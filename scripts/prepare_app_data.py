"""Make the light data files the deployed app reads (run once after the notebooks).

Usage:
    python scripts/prepare_app_data.py --geology outputs/geology/grand_canyon_geology.geojson \
        --mars-depth results/mars_analog/valles_marineris_incision_depth.tif

1. USGS SGMC geology (31 MB) -> simplified copy with only the columns the app uses (< 10 MB).
2. Valles Marineris incision depth at 200 m (349 MB) -> the 1,503 m analysis grid (about 4 MB).
   This is the same grid used for every Mars result (D / 6.1 per pixel), so no analysed value is lost.
"""
import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

REPO_DIR = Path(__file__).resolve().parents[1]
D_EARTH, D_MARS, MARS_RADIUS_M, STANDARD_LAT = 1229, 9237, 3396190, -8.0


def light_geology(source, target, tolerance_m=50):
    geology = gpd.read_file(source)[['UNIT_NAME', 'GENERALIZED_LITH', 'AGE_MAX', 'AGE_MIN', 'geometry']]
    metric = geology.to_crs('EPSG:32612')
    metric['geometry'] = metric.geometry.simplify(tolerance_m, preserve_topology=True)
    metric = metric[~metric.geometry.is_empty]
    target.parent.mkdir(parents=True, exist_ok=True)
    metric.to_crs(4326).to_file(target, driver='GeoJSON', COORDINATE_PRECISION=5)
    print(f'Geology: {len(metric)} units -> {target} ({target.stat().st_size / 1e6:.1f} MB)')


def light_mars(source, target):
    pixel = 200 * D_MARS / D_EARTH
    metres_per_degree = np.pi / 180 * MARS_RADIUS_M
    mars_x = lambda lon: lon * metres_per_degree * np.cos(np.radians(STANDARD_LAT))
    bounds = (mars_x(-92.0), -18.0 * metres_per_degree, mars_x(-52.0), 0.0)
    with rasterio.open(source) as src:
        window = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
        shape = (int(window.height / (pixel / 200)), int(window.width / (pixel / 200)))
        depth = src.read(1, window=window, out_shape=shape, resampling=Resampling.average).astype('float32')
        transform = src.window_transform(window) * Affine.scale(window.width / shape[1], window.height / shape[0])
    with rasterio.open(target, 'w', driver='GTiff', width=shape[1], height=shape[0], count=1, dtype='float32',
                       transform=transform, compress='deflate', tiled=True) as dst:
        dst.write(depth, 1)
    print(f'Mars depth: {shape[1]} x {shape[0]} px -> {target} ({target.stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--geology', type=Path, help='full SGMC GeoJSON made by notebooks/earth_pipeline.ipynb step 20')
    parser.add_argument('--mars-depth', type=Path, help='200 m incision-depth GeoTIFF made by notebooks/mars_analog.ipynb')
    args = parser.parse_args()
    if args.geology:
        light_geology(args.geology, REPO_DIR / 'results/geology/grand_canyon_geology_light.geojson')
    if args.mars_depth:
        light_mars(args.mars_depth, REPO_DIR / 'results/mars_analog/valles_marineris_incision_depth_light.tif')
