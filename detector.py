"""Live tributary-canyon detection for any area in the Grand Canyon region.

Pipeline: Sentinel-2 L2A RGB (Microsoft Planetary Computer) -> YOLO instance segmentation on 640 px tiles ->
vote raster -> USGS 3DEP 10 m DEM watershed separation into individual canyons -> table of polygons.
"""
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import planetary_computer
import rasterio
from pystac_client import Client
from rasterio.enums import MergeAlg, Resampling
from rasterio.features import rasterize, shapes
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from scipy.ndimage import gaussian_filter, uniform_filter
from shapely.geometry import Polygon, box, shape
from shapely.strtree import STRtree
from skimage.measure import label
from skimage.morphology import remove_small_objects
from skimage.segmentation import watershed

PROJECT_DIR = Path(__file__).resolve().parent
MODEL_FILE = PROJECT_DIR / 'models/seg_rgb_v2/best.pt'
SETTINGS_FILE = PROJECT_DIR / 'data/processed/stretch_settings.json'
ALLOWED_BOUNDS = (-114.25, 35.45, -111.25, 37.05)
MAX_AREA_KM2 = 400
TARGET_CRS = 'EPSG:32612'
PIXEL_M = 10
TILE_SIZE = 640
STEP = 320
CONFIDENCE = 0.05
MIN_VOTES = 2
STOP_ELEVATION_M = 1000
PILOT_BOUNDS = (-112.45, 35.95, -111.85, 36.35)
THRESHOLDS = [-50, -90, -130]
MIN_VALLEY_PIXELS = 5000
MIN_AREA_KM2 = 1
MAX_SHAPE_KM2 = 25
PIXEL_AREA_KM2 = 0.0001

_model = None


def stop_elevation(longitude):
    """Lowest elevation kept as tributary ground; the Colorado River floor drops from east to west."""
    return float(np.interp(longitude, [-113.5, -112.45, -111.85, -111.75], [700, 1000, 1000, 1250]))


def get_model():
    global _model
    if _model is None:
        from ultralytics import YOLO
        _model = YOLO(MODEL_FILE)
    return _model


def largest_polygon(geometry):
    geometry = geometry.buffer(0)
    if geometry.is_empty:
        return None
    if geometry.geom_type == 'Polygon':
        return geometry
    parts = [part for part in getattr(geometry, 'geoms', []) if part.geom_type == 'Polygon']
    return max(parts, key=lambda part: part.area) if parts else None


def prepare_grid(west, south, east, north):
    allowed = box(*ALLOWED_BOUNDS)
    if not allowed.contains(box(west, south, east, north)):
        raise ValueError('Select an area inside the Grand Canyon region.')

    left, bottom, right, top = transform_bounds('EPSG:4326', TARGET_CRS, west, south, east, north, densify_pts=21)
    minimum = TILE_SIZE * PIXEL_M
    if right - left < minimum:
        center = (left + right) / 2
        left, right = center - minimum / 2, center + minimum / 2
    if top - bottom < minimum:
        center = (top + bottom) / 2
        bottom, top = center - minimum / 2, center + minimum / 2

    left = np.floor(left / PIXEL_M) * PIXEL_M
    top = np.ceil(top / PIXEL_M) * PIXEL_M
    width = int(np.ceil((right - left) / PIXEL_M))
    height = int(np.ceil((top - bottom) / PIXEL_M))
    area_km2 = width * height * PIXEL_AREA_KM2

    if area_km2 > MAX_AREA_KM2:
        raise ValueError(f'Selected area is {area_km2:.0f} km2. The limit is {MAX_AREA_KM2} km2.')

    return from_origin(left, top, PIXEL_M, PIXEL_M), width, height, area_km2


def warped_read(href, transform, width, height, resampling):
    with rasterio.open(href) as src:
        with WarpedVRT(src, crs=TARGET_CRS, transform=transform, width=width, height=height, resampling=resampling) as vrt:
            return vrt.read(1).astype('float32')


def open_catalog():
    return Client.open('https://planetarycomputer.microsoft.com/api/stac/v1', modifier=planetary_computer.sign_inplace)


def choose_scenes(catalog, bbox, date_range):
    items = list(catalog.search(
        collections=['sentinel-2-l2a'],
        bbox=bbox,
        datetime=date_range,
        query={'eo:cloud_cover': {'lt': 10}},
    ).items())
    if not items:
        raise ValueError('No clear Sentinel-2 scenes were found for this area and date range.')

    groups = {}
    for item in items:
        groups.setdefault(item.datetime.date(), []).append(item)

    area = box(*bbox)

    def score(group):
        covered = area.intersection(gpd.GeoSeries([shape(i.geometry) for i in group]).union_all()).area / area.area
        cloud = max(i.properties.get('eo:cloud_cover', 100) for i in group)
        return (-round(covered, 3), cloud)

    selected_date = min(groups, key=lambda value: score(groups[value]))
    return selected_date, groups[selected_date]


def load_rgb(items, transform, width, height):
    settings = json.loads(SETTINGS_FILE.read_text())['rgb_reflectance_limits']
    rgb = np.zeros((3, height, width), dtype='uint8')

    for index, (asset, name) in enumerate([('B04', 'red'), ('B03', 'green'), ('B02', 'blue')]):
        band = np.zeros((height, width), dtype='float32')
        for item in items:
            baseline = float(item.properties.get('s2:processing_baseline', '0'))
            offset = 1000 if baseline >= 4 else 0  # processing baseline 04.00+ adds a +1000 offset
            data = warped_read(item.assets[asset].href, transform, width, height, Resampling.nearest)
            valid = data > 0
            data[valid] = (data[valid] - offset) / 10000
            fill = (band == 0) & valid
            band[fill] = data[fill]
        low = settings[name]['low']
        high = settings[name]['high']
        scaled = np.clip((band - low) / (high - low), 0, 1)
        layer = np.rint(scaled * 254 + 1).astype('uint8')
        layer[band == 0] = 0
        rgb[index] = layer

    return rgb


def load_dem(catalog, bbox, transform, width, height):
    items = [
        item for item in catalog.search(collections=['3dep-seamless'], bbox=bbox).items()
        if item.properties.get('gsd') == 10
    ]
    if not items:
        raise ValueError('No 10 m DEM was found for this area.')

    dem = np.full((height, width), np.nan, dtype='float32')
    for item in items:
        tile = warped_read(item.assets['data'].href, transform, width, height, Resampling.bilinear)
        tile[tile <= 0] = np.nan
        dem = np.where(np.isnan(dem), tile, dem)

    if np.isnan(dem).mean() > 0.01:
        raise ValueError('The DEM does not fully cover this area.')
    return np.where(np.isnan(dem), np.nanmedian(dem), dem)


def tile_starts(size):
    starts = list(range(0, size - TILE_SIZE + 1, STEP))
    if starts[-1] != size - TILE_SIZE:
        starts.append(size - TILE_SIZE)
    return starts


def run_yolo(rgb, transform):
    model = get_model()
    records = []
    _, height, width = rgb.shape

    for row in tile_starts(height):
        for col in tile_starts(width):
            tile = rgb[:, row:row + TILE_SIZE, col:col + TILE_SIZE]
            if not tile.any():
                continue
            bgr = np.moveaxis(tile, 0, -1)[:, :, ::-1].copy()
            result = model.predict(bgr, conf=CONFIDENCE, imgsz=TILE_SIZE, verbose=False)[0]
            if result.masks is None:
                continue
            for points, score in zip(result.masks.xy, result.boxes.conf.cpu().numpy()):
                if len(points) < 3:
                    continue
                polygon = largest_polygon(Polygon([
                    (transform.c + (col + x) * transform.a, transform.f + (row + y) * transform.e)
                    for x, y in points
                ]))
                if polygon is not None:
                    records.append({'confidence': float(score), 'geometry': polygon})

    if not records:
        return gpd.GeoDataFrame({'confidence': [], 'geometry': []}, geometry='geometry', crs=TARGET_CRS)
    return gpd.GeoDataFrame(records, geometry='geometry', crs=TARGET_CRS)


def separate_canyons(raw, dem, transform, stop_m=STOP_ELEVATION_M):
    votes = rasterize(
        [(geometry, 1) for geometry in raw.geometry],
        out_shape=dem.shape,
        transform=transform,
        fill=0,
        dtype='uint16',
        merge_alg=MergeAlg.add,
    )
    land = (votes >= MIN_VOTES) & (dem >= stop_m)
    smooth = gaussian_filter(dem, sigma=8)
    position = smooth - uniform_filter(smooth, size=101, mode='nearest')

    remaining = land.copy()
    regions_out = np.zeros(dem.shape, dtype='int32')
    next_id = 1

    for threshold in THRESHOLDS:
        valleys = remove_small_objects((position <= threshold) & remaining, min_size=MIN_VALLEY_PIXELS)
        markers = label(valleys, connectivity=2)
        if markers.max() == 0:
            continue
        regions = watershed(smooth, markers=markers, mask=remaining)
        area = np.bincount(regions.ravel()) * PIXEL_AREA_KM2
        keep = (area >= MIN_AREA_KM2) & (area <= MAX_SHAPE_KM2)
        keep[0] = False
        for region_id in np.flatnonzero(keep):
            selected = regions == region_id
            regions_out[selected] = next_id
            remaining[selected] = False
            next_id += 1

    valleys = remove_small_objects((position <= THRESHOLDS[-1]) & remaining, min_size=MIN_VALLEY_PIXELS)
    markers = label(valleys, connectivity=2)
    if markers.max() > 0:
        regions = watershed(smooth, markers=markers, mask=remaining)
        area = np.bincount(regions.ravel()) * PIXEL_AREA_KM2
        for region_id in np.flatnonzero(area >= MIN_AREA_KM2):
            if region_id:
                regions_out[regions == region_id] = next_id
                next_id += 1

    polygons = []
    for geometry, value in shapes(regions_out, mask=regions_out > 0, transform=transform):
        polygon = largest_polygon(shape(geometry).buffer(-30).buffer(30))
        polygon = largest_polygon(polygon.simplify(20)) if polygon is not None else None
        if polygon is not None and polygon.area / 1_000_000 >= MIN_AREA_KM2:
            polygons.append(polygon)
    return polygons


def build_table(polygons, raw):
    clean = []
    used = None
    for polygon in polygons:
        current = polygon if used is None else largest_polygon(polygon.difference(used))
        if current is not None and current.area / 1_000_000 >= MIN_AREA_KM2:
            clean.append(current)
            used = current if used is None else used.union(current)

    if not clean:
        return gpd.GeoDataFrame(columns=['detection_id', 'geometry'], geometry='geometry', crs=TARGET_CRS)

    table = gpd.GeoDataFrame(geometry=clean, crs=TARGET_CRS)
    tree = STRtree(list(raw.geometry))
    scores = raw['confidence'].to_numpy()
    max_values = []
    mean_values = []
    lengths = []

    for geometry in table.geometry:
        matches = tree.query(geometry, predicate='intersects')
        max_values.append(round(float(scores[matches].max()), 3) if len(matches) else 0)
        mean_values.append(round(float(scores[matches].mean()), 3) if len(matches) else 0)
        x, y = geometry.minimum_rotated_rectangle.exterior.coords.xy
        lengths.append(max(np.hypot(x[1] - x[0], y[1] - y[0]), np.hypot(x[2] - x[1], y[2] - y[1])) / 1000)

    table['area_km2'] = (table.geometry.area / 1_000_000).round(2)
    table['est_length_km'] = np.round(lengths, 2)
    table['mean_width_km'] = (table['area_km2'] / table['est_length_km']).round(2)
    table['max_confidence'] = max_values
    table['mean_confidence'] = mean_values
    table = table.sort_values('mean_confidence', ascending=False).reset_index(drop=True)
    table.insert(0, 'detection_id', [f'A{i + 1:04d}' for i in range(len(table))])
    centers = gpd.GeoSeries(table.geometry.representative_point(), crs=TARGET_CRS).to_crs(4326)
    table['center_lon'] = centers.x.round(6)
    table['center_lat'] = centers.y.round(6)
    return table


def detect_area(west, south, east, north, date_range='2026-05-15/2026-08-31', progress=print):
    transform, width, height, area_km2 = prepare_grid(west, south, east, north)
    bbox = [west, south, east, north]
    catalog = open_catalog()

    progress('Searching Sentinel-2 scenes')
    scene_date, items = choose_scenes(catalog, bbox, date_range)

    progress('Reading image')
    rgb = load_rgb(items, transform, width, height)

    progress('Reading elevation data')
    dem = load_dem(catalog, bbox, transform, width, height)

    progress('Running YOLO')
    raw = run_yolo(rgb, transform)
    if raw.empty:
        table = gpd.GeoDataFrame(columns=['detection_id', 'geometry'], geometry='geometry', crs=TARGET_CRS)
    else:
        progress('Separating canyons')
        stop_m = stop_elevation((west + east) / 2)
        table = build_table(separate_canyons(raw, dem, transform, stop_m), raw)

    return {
        'detections': table,
        'raw': raw,
        'rgb': rgb,
        'transform': transform,
        'scene_date': str(scene_date),
        'scene_ids': [item.id for item in items],
        'area_km2': round(area_km2, 2),
        'inside_tested_area': box(*PILOT_BOUNDS).contains(box(west, south, east, north)),
    }
