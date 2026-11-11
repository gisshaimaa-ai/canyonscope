import base64
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import altair as alt
import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st
from folium.plugins import Draw
from PIL import Image, ImageDraw
from shapely.geometry import box
from streamlit_folium import st_folium

# All paths are relative to the repository, so the app runs the same locally and on Streamlit Community Cloud
APP_DIR = Path(__file__).resolve().parent
RESULTS_DIR = APP_DIR / 'results/grand_canyon'
GEOLOGY_FILE = APP_DIR / 'results/geology/grand_canyon_geology_light.geojson'
METRICS_FILE = APP_DIR / 'results/model_v2_results.csv'
MARS_DIR = APP_DIR / 'results/mars_analog'
HERO_FILE = APP_DIR / 'assets/hero.jpg'
MEDIA_FILE = APP_DIR / 'assets/media.json'
GNIS_DIR = APP_DIR / 'results/gnis_validation'
IMAGERY = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
GEOLOGY_COLORS = ['#e9c46a', '#f4a261', '#e76f51', '#c98b6b', '#a7c4a0', '#7fb7be', '#b392ac', '#d4a5a5', '#90a955', '#bc6c25']
DATE_OPTIONS = {
    'Summer 2026': '2026-05-15/2026-08-31',
    'Summer 2025': '2025-05-15/2025-08-31',
    'Summer 2024': '2024-05-15/2024-08-31',
}
PAGES = ['Home', 'Explorer', 'Earth vs Mars', 'Results', 'Learn']
HEADERS = {'User-Agent': 'GrandCanyonTributaryExplorer/1.0 (student research project)'}
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;500;600&display=swap');
:root{--bg:#15110e;--panel:#211a15;--line:#3a2e25;--sand:#e9c46a;--clay:#d9734e;--text:#f4ece1;--muted:#b9aa9a}
html,body,[class*="css"]{font-family:'Inter',sans-serif}
[data-testid="stSidebar"],#MainMenu,footer{display:none}
header[data-testid="stHeader"]{background:transparent}
.block-container{max-width:1420px;padding-top:1rem;padding-bottom:3rem}
.brand{font-family:'Fraunces',serif;font-size:1.25rem;font-weight:700;color:var(--text);padding-top:6px}
.brand span{color:var(--clay)}
.st-key-nav div[role="radiogroup"]{gap:6px;justify-content:flex-end}
.st-key-nav div[role="radiogroup"] label{background:transparent;border:1px solid var(--line);border-radius:999px;padding:10px 22px;margin:0;cursor:pointer;min-height:44px;align-items:center}
.st-key-nav div[role="radiogroup"] label p{font-size:1rem;font-weight:600}
.st-key-nav div[role="radiogroup"] label>div:not(:has(p)){display:none}
.st-key-nav div[role="radiogroup"] label:hover{border-color:var(--clay)}
.st-key-nav div[role="radiogroup"] label:has(input:checked){background:var(--clay)}
.st-key-nav div[role="radiogroup"] label:has(input:checked) p{color:#fff}
.hero{min-height:560px;border-radius:20px;padding:56px;display:flex;flex-direction:column;justify-content:flex-end;background-size:cover;background-position:center;border:1px solid var(--line)}
.eyebrow{font-size:.78rem;letter-spacing:.2em;text-transform:uppercase;color:var(--sand);font-weight:600}
.hero h1{font-family:'Fraunces',serif;font-size:4rem;line-height:1.05;margin:.5rem 0;color:#fff;padding:0;max-width:900px}
.hero p{font-size:1.15rem;color:#eadfd2;max-width:720px;margin:0}
.page-title{font-family:'Fraunces',serif;font-size:2.3rem;margin:.6rem 0 .2rem;color:var(--text)}
.page-sub{color:var(--muted);margin-bottom:1rem}
.section{font-family:'Fraunces',serif;font-size:2rem;margin:2.6rem 0 .3rem;color:var(--text)}
.section-sub{color:var(--muted);max-width:760px;margin-bottom:1rem}
.grid{display:grid;gap:14px}
.g3{grid-template-columns:repeat(3,1fr)}
.g4{grid-template-columns:repeat(4,1fr)}
.g5{grid-template-columns:repeat(5,1fr)}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
.tile b{display:block;font-size:1rem;margin-bottom:6px}
.tile span{font-size:.88rem;color:var(--muted);line-height:1.5}
.stat strong{display:block;font-family:'Fraunces',serif;font-size:2.2rem;color:var(--sand)}
.step{border-top:3px solid var(--clay)}
.timeline{border-left:2px solid var(--clay);margin-left:8px;padding-left:24px}
.event{position:relative;padding-bottom:18px}
.event:before{content:"";position:absolute;left:-31px;top:6px;width:12px;height:12px;border-radius:50%;background:var(--sand)}
.event b{display:block;color:var(--sand)}
.event span{color:var(--text);font-size:.92rem}
.photo{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.photo img{width:100%;height:230px;object-fit:cover;display:block}
.photo video{width:100%;display:block}
.photo div{padding:9px 12px;font-size:.74rem;color:var(--muted)}
.photo a{color:var(--sand);text-decoration:none}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:12px}
.card h3{font-family:'Fraunces',serif;font-size:1.2rem;margin:0 0 8px;padding:0;color:var(--text)}
.row{display:flex;justify-content:space-between;gap:16px;padding:6px 0;border-bottom:1px solid var(--line);font-size:.88rem}
.row:last-child{border:0}
.row span{color:var(--muted)}
.row b{text-align:right;font-weight:600}
.unit{margin:10px 0}
.unit-head{display:flex;justify-content:space-between;gap:10px;font-size:.84rem;font-weight:600}
.unit-sub{font-size:.76rem;color:var(--muted)}
.track{height:7px;background:#33291f;border-radius:6px;overflow:hidden;margin-top:4px}
.fill{height:100%;border-radius:6px}
.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:.8rem;color:var(--muted);margin-top:8px}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
.sources{font-size:.8rem;color:var(--muted);border-top:1px solid var(--line);margin-top:2.5rem;padding-top:1rem}
.sources a{color:var(--sand)}
@media(max-width:900px){.hero{padding:26px;min-height:420px}.hero h1{font-size:2.3rem}.g3,.g4,.g5{grid-template-columns:1fr}}
</style>
"""

st.set_page_config(page_title='Grand Canyon Tributary Canyons', layout='wide')
st.markdown(CSS, unsafe_allow_html=True)


def region_name(longitude):
    if longitude < -113.0:
        return 'West'
    if longitude < -112.45:
        return 'Central West'
    if longitude <= -111.85:
        return 'Pilot Area'
    return 'East'


def short_age(value):
    parts = [part.split(' - ')[-1].strip() for part in str(value).split(' to ')]
    return parts[0] if len(set(parts)) == 1 else f'{parts[0]} to {parts[-1]}'


@st.cache_data(show_spinner=False)
def load_results():
    named = RESULTS_DIR / 'grand_canyon_detections_named.geojson'  # adds official USGS GNIS names
    table = gpd.read_file(named if named.exists() else RESULTS_DIR / 'grand_canyon_detections_geology.geojson')
    table['name'] = table['gnis_name'].fillna('') if 'gnis_name' in table else ''
    table['scene_date'] = table['scene_date'].astype(str)
    table['region'] = table['center_lon'].map(region_name)
    table['geology_age'] = table['geology_age'].map(short_age)
    columns = ['detection_id', 'name', 'region', 'area_km2', 'est_length_km', 'mean_width_km', 'max_confidence',
               'mean_confidence', 'center_lon', 'center_lat', 'scene_date', 'geology_unit',
               'geology_lithology', 'geology_age', 'geometry']
    return table[columns]


@st.cache_data(show_spinner=False)
def load_geology():
    return gpd.read_file(GEOLOGY_FILE)


@st.cache_data(show_spinner=False)
def geology_in_area(bbox):
    clipped = gpd.clip(load_geology(), box(*bbox))
    clipped = clipped[clipped.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])].copy()
    clipped['area_km2'] = clipped.to_crs('EPSG:32612').geometry.area / 1_000_000
    return clipped


@st.cache_data(show_spinner=False)
def load_media():
    return json.loads(MEDIA_FILE.read_text()) if MEDIA_FILE.exists() else {'photos': [], 'videos': []}


@st.cache_data(show_spinner=False)
def hero_data():
    return base64.b64encode(HERO_FILE.read_bytes()).decode()


def license_allowed(name):
    name = str(name).upper()
    return 'NC' not in name and 'ND' not in name and name.startswith(('CC BY', 'CC-BY', 'CC0', 'PUBLIC DOMAIN', 'PD'))


BLOCKED_MEDIA = re.compile(r'\b(raven|bird|squirrel|condor|elk|deer|sheep|lizard|snake|insect|butterfly|flower|plant|cactus|tree|fauna|flora|animal|wildlife|map|sign|logo|diagram|chart|poster|helicopter|aircraft|airplane|plane|vehicle|car|bus|truck|train|railway|locomotive|rescue|borstar|police|ranger|people|portrait|selfie|wedding|ceremony|event|festival|day|museum|exhibit|artifact|pottery|archaeology|archeology|hotel|lodge|studio|building|interior|restaurant|parking|construction|mule|horse|dog|visitor|tourist|skywalk|sculpture|statue|meeting|conference|press|award|celebration|volunteer|staff|employee)s?\b', re.IGNORECASE)


def media_ok(title, meta):
    text = (title + ' ' + meta.get('Categories', {}).get('value', '')).replace('_', ' ')
    return not BLOCKED_MEDIA.search(text)


def photo_series(title):
    """Key shared by near-identical photos: same astronaut series (ISS, STS) or same name with only numbers changed."""
    name = re.sub(r'\.[a-z]+$', '', title.lower().removeprefix('file:')).replace('_', ' ')
    if re.match(r'(iss|sts)[\s-]?\d', name) or 'from the iss' in name or 'from space' in name:
        return 'astronaut photo'
    return re.sub(r'[\d\W]+', ' ', name).strip()


def clean_text(value):
    return re.sub(r'<[^>]+>', '', str(value or 'Unknown')).strip()[:70]


@st.cache_data(show_spinner=False, ttl=86400)
def area_photos(bbox):
    west, south, east, north = bbox
    params = urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'generator': 'geosearch', 'ggsnamespace': 6,
        'ggsbbox': f'{north}|{west}|{south}|{east}', 'ggslimit': 60, 'prop': 'imageinfo',
        'iiprop': 'url|mime|extmetadata', 'iiurlwidth': 700,
    })
    request = urllib.request.Request(f'https://commons.wikimedia.org/w/api.php?{params}', headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            pages = json.load(response).get('query', {}).get('pages', {})
    except Exception:
        return []

    photos, seen = [], set()
    for page in sorted(pages.values(), key=lambda item: item.get('index', 0)):
        info = (page.get('imageinfo') or [{}])[0]
        meta = info.get('extmetadata', {})
        license_name = meta.get('LicenseShortName', {}).get('value', '')
        series = photo_series(page.get('title', ''))
        author = clean_text(meta.get('Artist', {}).get('value'))
        if series in seen or author in seen:
            continue   # one photo per series and per photographer: avoids near-identical shots
        if info.get('mime') == 'image/jpeg' and license_allowed(license_name) and media_ok(page.get('title', ''), meta):
            seen.update({series, author})
            photos.append({
                'thumb': info.get('thumburl'),
                'page': info.get('descriptionurl'),
                'author': author,
                'license': clean_text(license_name),
            })
    return photos[:6]


def confidence_color(value):
    return '#22c55e' if value >= 0.6 else '#facc15' if value >= 0.3 else '#f97316'


def detection_style(feature):
    return {'color': confidence_color(feature['properties']['mean_confidence']), 'weight': 2.5, 'fillOpacity': 0.14}


def geology_color(name):
    return GEOLOGY_COLORS[sum(ord(letter) for letter in str(name)) % len(GEOLOGY_COLORS)]


def geology_style(feature):
    color = geology_color(feature['properties']['UNIT_NAME'])
    return {'color': color, 'weight': 1, 'fillColor': color, 'fillOpacity': 0.2}


def rows(items):
    return ''.join(
        f'<div class="row"><span>{html.escape(str(label))}</span><b>{html.escape(str(value))}</b></div>'
        for label, value in items
    )


def card(title, content):
    st.markdown(f'<div class="card"><h3>{html.escape(title)}</h3>{content}</div>', unsafe_allow_html=True)


def section(title, subtitle=''):
    st.markdown(f'<div class="section">{title}</div><div class="section-sub">{subtitle}</div>', unsafe_allow_html=True)


def tiles(items, columns, css=''):
    content = ''.join(f'<div class="tile {css}"><b>{html.escape(a)}</b><span>{html.escape(b)}</span></div>' for a, b in items)
    st.markdown(f'<div class="grid g{columns}">{content}</div>', unsafe_allow_html=True)


def photo_grid(photos):
    content = ''.join(
        f'<div class="photo"><a href="{html.escape(item["page"])}" target="_blank"><img src="{html.escape(item["thumb"])}" loading="lazy" alt="Grand Canyon photograph"></a>'
        f'<div>{html.escape(item["author"])} · {html.escape(item["license"])}</div></div>'
        for item in photos
    )
    st.markdown(f'<div class="grid g3">{content}</div>', unsafe_allow_html=True)


def open_explorer():
    st.session_state.page = 'Explorer'


def show_home(results):
    background = f'linear-gradient(180deg,rgba(21,17,14,.1),rgba(21,17,14,.9)),url(data:image/jpeg;base64,{hero_data()})'
    st.markdown(
        f'<section class="hero" style="background-image:{background}"><div class="eyebrow">Geospatial AI · Sentinel-2 · YOLO</div>'
        '<h1>Reading the Grand Canyon from Space</h1>'
        '<p>An AI workflow that finds tributary-canyon terrain, separates it using elevation data, and turns it into an interactive map.</p></section>',
        unsafe_allow_html=True,
    )
    st.write('')
    st.button('Open the Explorer', type='primary', on_click=open_explorer)

    section('Why this matters', 'Tributary canyons shape the Grand Canyon, but mapping them by hand is slow and difficult to repeat.')
    tiles([
        ('The challenge', 'Canyons branch and connect, and shadows and rock colors hide their boundaries in satellite images.'),
        ('Our approach', 'YOLO finds canyon terrain in Sentinel-2 imagery. Elevation data separates neighboring canyons along ridges.'),
        ('The result', 'Users draw any area, run detection, and receive polygons, dimensions, confidence scores and regional geology.'),
    ], 3)

    section('The canyon in numbers')
    content = ''.join(f'<div class="tile stat"><strong>{value}</strong><span>{label}</span></div>' for value, label in [
        ('447 km', 'length through the national park'),
        ('1.6 km', 'average depth'),
        ('2 billion', 'years of geologic history in its rock layers'),
        (f'{len(results)}', 'experimental detections mapped by this project'),
    ])
    st.markdown(f'<div class="grid g4">{content}</div>', unsafe_allow_html=True)

    section('A long story in stone', 'Key moments in the geological and human history of the Grand Canyon.')
    events = [
        ('About 2 billion years', 'Rock layers begin recording a history that spans four major geologic eras.'),
        ('About 6 million years', 'Uplift and erosion by the Colorado River shape the canyon.'),
        ('9,000 to 13,000 years ago', 'Paleo-Indians are the first people known to migrate through the canyon.'),
        ('800 to 1,300 years ago', 'Ancestral Puebloans live in stone houses and farm corn, beans and squash.'),
        ('1540', 'Europeans first explore the canyon.'),
        ('1901', 'The railroad reaches the South Rim.'),
        ('1919', 'Grand Canyon National Park is established on February 26.'),
    ]
    content = ''.join(f'<div class="event"><b>{html.escape(a)}</b><span>{html.escape(b)}</span></div>' for a, b in events)
    st.markdown(f'<div class="timeline">{content}</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub" style="margin-top:12px">The Havasupai, Navajo, Southern Paiute and Hualapai live in or beside the canyon, and the Hopi, Zuni and Apache live nearby. Many consider it a sacred place.</div>', unsafe_allow_html=True)

    section('How it works')
    tiles([
        ('1. Data', 'Sentinel-2 imagery and 3DEP elevation at 10 m'),
        ('2. Reference', 'Reviewed canyon polygons in separate areas'),
        ('3. YOLO', 'Instance segmentation finds canyon terrain'),
        ('4. Elevation', 'Ridges separate neighboring canyons'),
        ('5. Mapping', 'Coordinates, size and geology are attached'),
    ], 5, 'step')

    section('Beyond Earth', 'The Grand Canyon catalogue becomes a reference for reading canyons on Mars, where no one can go.')
    tiles([
        ('Valles Marineris', 'The largest canyon system known in the Solar System, about 7.5 times deeper than the Grand Canyon in our measurements.'),
        ('Same rules, both planets', 'Tributary canyons are found from elevation alone, with rules calibrated on Earth and written in units of canyon depth.'),
        ('The finding', 'Martian side canyons match Grand Canyon tributaries in plan-view shape, but are cut 25–35% less deeply.'),
    ], 3)
    st.write('')
    st.button('Compare Earth and Mars', on_click=open_mars)

    media = load_media()
    if media['photos']:
        section('Views of the canyon', 'Openly licensed photographs from Wikimedia Commons. Select a photo to see its source.')
        photo_grid(media['photos'])
    if media['videos']:
        section('Watch', 'Openly licensed videos from Wikimedia Commons.')
        content = ''.join(
            f'<div class="photo"><video controls preload="metadata" src="{html.escape(item["url"])}"></video>'
            f'<div><a href="{html.escape(item["page"])}" target="_blank">{html.escape(item["title"])}</a><br>{html.escape(item["author"])} · {html.escape(item["license"])}</div></div>'
            for item in media['videos']
        )
        st.markdown(f'<div class="grid g3">{content}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="sources">Sources: <a href="https://www.nps.gov/grca/learn/management/statistics.htm" target="_blank">NPS park statistics</a> · '
        '<a href="https://www.nps.gov/grca/learn/education/human-history.htm" target="_blank">NPS human history</a> · '
        '<a href="https://www.nps.gov/grca/learn/historyculture/thenandnow.htm" target="_blank">NPS Then and Now</a> · '
        '<a href="https://whc.unesco.org/en/list/75/" target="_blank">UNESCO World Heritage</a></div>',
        unsafe_allow_html=True,
    )


def build_map(bbox, clipped, detections):
    canyon_map = folium.Map(location=[36.15, -112.8], zoom_start=8, tiles=None)
    folium.TileLayer(IMAGERY, attr='Tiles © Esri', name='Imagery').add_to(canyon_map)

    if clipped is not None and len(clipped) > 0:
        fields = ['UNIT_NAME', 'GENERALIZED_LITH']
        folium.GeoJson(
            clipped[fields + ['geometry']].to_json(),
            name='Geology',
            style_function=geology_style,
            tooltip=folium.GeoJsonTooltip(fields=fields, aliases=['Map unit', 'Lithology']),
        ).add_to(canyon_map)

    if detections is not None and len(detections) > 0:
        fields = ['detection_id', 'name', 'area_km2', 'mean_confidence']
        shown = detections.copy()
        if 'name' not in shown:
            shown['name'] = ''
        shown['name'] = shown['name'].replace('', 'Unnamed')
        folium.GeoJson(
            shown[fields + ['geometry']].to_crs(4326).to_json(),
            name='Detections',
            style_function=detection_style,
            tooltip=folium.GeoJsonTooltip(fields=fields, aliases=['ID', 'Official name (USGS GNIS)', 'Area (km²)', 'Mean confidence']),
        ).add_to(canyon_map)

    Draw(
        export=False,
        draw_options={'polyline': False, 'polygon': False, 'circle': False, 'marker': False,
                      'circlemarker': False, 'rectangle': {'shapeOptions': {'color': '#ffffff', 'weight': 2}}},
        edit_options={'edit': False, 'remove': False},
    ).add_to(canyon_map)

    if bbox:
        west, south, east, north = bbox
        folium.Rectangle([[south, west], [north, east]], color='#ffffff', weight=2, fill=False).add_to(canyon_map)
        canyon_map.fit_bounds([[south, west], [north, east]])
    return canyon_map


def add_geology(table, clipped):
    if len(table) == 0:
        return table
    if len(clipped) == 0:
        table['geology_unit'] = table['geology_lithology'] = table['geology_age'] = 'Not available'
        return table
    geology = clipped.to_crs('EPSG:32612')
    units, rocks, ages = [], [], []
    for geometry in table.geometry:
        shared = geology.geometry.intersection(geometry).area
        item = geology.iloc[int(shared.to_numpy().argmax())]
        units.append(str(item.UNIT_NAME))
        rocks.append(str(item.GENERALIZED_LITH))
        ages.append(short_age(f'{item.AGE_MAX} to {item.AGE_MIN}'))
    table['geology_unit'] = units
    table['geology_lithology'] = rocks
    table['geology_age'] = ages
    return table


@st.cache_data(show_spinner=False)
def load_gnis():
    path = GNIS_DIR / 'gnis_named_tributaries_check.csv'
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def add_names(table):
    """Name each detection after the official USGS GNIS canyon whose mouth is within 500 m (nearest wins)."""
    names = load_gnis()
    if len(table) == 0:
        return table
    table['name'] = ''
    if len(names) == 0:
        return table
    mouths = gpd.GeoDataFrame(names[['name']], geometry=gpd.points_from_xy(names.mouth_lon, names.mouth_lat), crs=4326).to_crs(table.crs)
    for index, geometry in table.geometry.items():
        distance = mouths.distance(geometry)
        if distance.min() <= 500:
            table.loc[index, 'name'] = mouths.loc[distance.idxmin(), 'name']
    columns = ['detection_id', 'name'] + [c for c in table.columns if c not in ('detection_id', 'name')]
    return table[columns]


def run_detection(status):
    sys.path.insert(0, str(APP_DIR))
    import detector
    st.session_state.error = None
    try:
        result = detector.detect_area(
            *st.session_state.bbox,
            date_range=DATE_OPTIONS[st.session_state.period],
            progress=status.info,
        )
        status.info('Adding geology')
        result['detections'] = add_geology(result['detections'], geology_in_area(st.session_state.bbox))
        result['detections'] = add_names(result['detections'])
        st.session_state.result = result
    except Exception as error:
        st.session_state.result = None
        st.session_state.error = str(error)
    st.session_state.pending = False
    st.rerun()


def handle_map_click(state):
    drawing = state.get('last_active_drawing') if state else None
    if not drawing:
        return
    drawing_key = json.dumps(drawing, sort_keys=True)
    if drawing_key == st.session_state.last_drawing:
        return
    st.session_state.last_drawing = drawing_key
    properties = drawing.get('properties') or {}
    if 'detection_id' in properties:
        st.session_state.selected = properties
    elif not properties and drawing.get('geometry', {}).get('type') == 'Polygon':
        points = drawing['geometry']['coordinates'][0]
        longitudes = [point[0] for point in points]
        latitudes = [point[1] for point in points]
        st.session_state.bbox = (min(longitudes), min(latitudes), max(longitudes), max(latitudes))
        st.session_state.result = None
        st.session_state.selected = None
        st.session_state.error = None
        st.session_state.pending = True
        st.rerun()


def show_selected_detection():
    item = st.session_state.selected
    if not item:
        return
    card(f"Canyon {item['detection_id']}", rows([
        ('Location', f"{item.get('center_lat')}, {item.get('center_lon')}"),
        ('Area', f"{item.get('area_km2')} km²"),
        ('Estimated length', f"{item.get('est_length_km')} km"),
        ('Estimated mean width', f"{item.get('mean_width_km')} km"),
        ('Mean confidence', item.get('mean_confidence')),
        ('Maximum confidence', item.get('max_confidence')),
        ('Map unit', item.get('geology_unit')),
        ('Rock type', item.get('geology_lithology')),
        ('Age', item.get('geology_age')),
    ]))


def show_geology_summary(clipped):
    if len(clipped) == 0:
        return
    total_area = clipped.area_km2.sum()
    summary = clipped.groupby('UNIT_NAME', as_index=False).agg(
        area_km2=('area_km2', 'sum'),
        lithology=('GENERALIZED_LITH', 'first'),
        age_max=('AGE_MAX', 'first'),
        age_min=('AGE_MIN', 'first'),
    ).sort_values('area_km2', ascending=False)

    blocks = []
    for item in summary.head(6).itertuples():
        share = item.area_km2 / total_area * 100
        age = short_age(f'{item.age_max} to {item.age_min}')
        color = geology_color(item.UNIT_NAME)
        blocks.append(
            f'<div class="unit"><div class="unit-head"><span>{html.escape(str(item.UNIT_NAME))}</span><span>{share:.0f}%</span></div>'
            f'<div class="unit-sub">{html.escape(str(item.lithology))} · {html.escape(age)}</div>'
            f'<div class="track"><div class="fill" style="width:{share:.1f}%;background:{color}"></div></div></div>'
        )
    note = '<div class="unit-sub">USGS SGMC, approximately 1:1,000,000. Regional geology, not a canyon-scale rock map.</div>'
    card('Geology in this area', ''.join(blocks) + note)


def overlay_image(result):
    image = Image.fromarray(np.moveaxis(result['rgb'], 0, -1)).convert('RGB')
    draw = ImageDraw.Draw(image)
    transform = result['transform']
    for geometry in result['detections'].geometry:
        points = [((x - transform.c) / transform.a, (y - transform.f) / transform.e) for x, y in geometry.exterior.coords]
        draw.line(points, fill=(34, 211, 238), width=4)
    return image


def show_results():
    result = st.session_state.result
    detections = result['detections']
    if not result.get('inside_tested_area', False):
        st.warning('This area is outside the original pilot zone. Results are unverified.')

    st.markdown('<div class="section">Results for this area</div>', unsafe_allow_html=True)
    canyon_area = detections.area_km2.sum() if len(detections) else 0
    mean_score = f'{detections.mean_confidence.mean():.3f}' if len(detections) else 'None'
    content = ''.join(f'<div class="tile stat"><strong>{value}</strong><span>{label}</span></div>' for value, label in [
        (len(detections), 'detections'),
        (f'{canyon_area:.1f} km²', 'canyon area'),
        (mean_score, 'mean confidence'),
        (result['scene_date'], 'image date'),
    ])
    st.markdown(f'<div class="grid g4">{content}</div>', unsafe_allow_html=True)

    if len(detections) == 0:
        message = 'YOLO found candidates, but none passed canyon separation.' if len(result['raw']) else 'YOLO found no candidates in this area.'
        st.warning(message)
        return

    st.write('')
    left, right = st.columns(2)
    left.image(np.moveaxis(result['rgb'], 0, -1), caption='Sentinel-2 image', width='stretch')
    right.image(overlay_image(result), caption='YOLO detections', width='stretch')

    table = detections.drop(columns='geometry')
    st.dataframe(table, width='stretch', hide_index=True)
    first, second = st.columns(2)
    first.download_button('Download GeoJSON', detections.to_crs(4326).to_json(), 'area_detections.geojson',
                          'application/geo+json', width='stretch')
    second.download_button('Download CSV', table.to_csv(index=False), 'area_detections.csv', 'text/csv', width='stretch')


def show_explorer():
    st.markdown('<div class="page-title">Explorer</div><div class="page-sub">Use the square tool on the map to draw an area. Detection starts automatically.</div>', unsafe_allow_html=True)
    bbox = st.session_state.bbox
    result = st.session_state.result
    clipped = geology_in_area(bbox) if bbox else None
    detections = result['detections'] if result else None
    left, right = st.columns([2.45, 1])

    with left:
        canyon_map = build_map(bbox, clipped, detections)
        state = st_folium(canyon_map, height=640, use_container_width=True, returned_objects=['last_active_drawing'])
        st.markdown(
            '<div class="legend"><span><i class="dot" style="background:#22c55e"></i>Confidence 0.6+</span>'
            '<span><i class="dot" style="background:#facc15"></i>0.3 to 0.6</span>'
            '<span><i class="dot" style="background:#f97316"></i>Below 0.3</span></div>',
            unsafe_allow_html=True,
        )

    handle_map_click(state)

    with right:
        st.selectbox('Image period', list(DATE_OPTIONS), key='period')
        status = st.empty()
        if st.session_state.error:
            status.error(st.session_state.error)
        if st.session_state.pending:
            run_detection(status)
        if bbox and st.button('Run again', width='stretch'):
            st.session_state.pending = True
            st.rerun()
        show_selected_detection()
        if bbox:
            show_geology_summary(clipped)
        elif not st.session_state.selected:
            card('Start here', '<div class="unit-sub">Maps stay clear until you choose an area. Draw up to 400 km² inside the Grand Canyon region.</div>')

    if result:
        show_results()
    if bbox:
        photos = area_photos(bbox)
        if photos:
            section('Photos near this area', 'Geotagged, openly licensed photographs from Wikimedia Commons.')
            photo_grid(photos)


def bar_chart(data, category, value, color='#d9734e', sort='-x'):
    chart = alt.Chart(data).mark_bar(cornerRadiusEnd=4, color=color).encode(
        x=alt.X(f'{value}:Q', title=None),
        y=alt.Y(f'{category}:N', sort=sort, title=None, axis=alt.Axis(labelLimit=280)),
        tooltip=[category, value],
    ).properties(height=max(180, len(data) * 36)).configure_view(strokeWidth=0).configure(
        background='transparent'
    ).configure_axis(labelColor='#d8cbbb', gridColor='#33291f', domainColor='#3a2e25', tickColor='#3a2e25')
    st.altair_chart(chart, width='stretch')


def show_analytics(results):
    st.markdown('<div class="page-title">Analytics</div><div class="page-sub">Statistics for the saved Grand Canyon catalogue. Counts are experimental, not a complete inventory.</div>', unsafe_allow_html=True)
    content = ''.join(f'<div class="tile stat"><strong>{value}</strong><span>{label}</span></div>' for value, label in [
        (len(results), 'detections'),
        (f'{results.area_km2.sum():,.0f} km²', 'mapped canyon area'),
        (f'{results.area_km2.mean():.2f} km²', 'mean area'),
        (f'{results.mean_confidence.mean():.3f}', 'mean confidence'),
    ])
    st.markdown(f'<div class="grid g4">{content}</div>', unsafe_allow_html=True)
    st.write('')
    left, right = st.columns(2)
    with left:
        st.subheader('Detections by region')
        counts = results.region.value_counts().rename_axis('Region').reset_index(name='Detections')
        bar_chart(counts, 'Region', 'Detections')
    with right:
        st.subheader('Mean confidence')
        labels = ['0.0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0']
        groups = pd.cut(results.mean_confidence, [0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=labels, include_lowest=True)
        counts = groups.value_counts().reindex(labels).rename_axis('Range').reset_index(name='Detections')
        bar_chart(counts, 'Range', 'Detections', '#e9c46a', None)

    st.subheader('Canyon area by geologic unit')
    units = results.groupby('geology_unit', as_index=False).area_km2.sum().nlargest(8, 'area_km2')
    units.columns = ['Map unit', 'Canyon area km2']
    bar_chart(units, 'Map unit', 'Canyon area km2', '#7fb7be')


def show_method():
    st.markdown('<div class="page-title">Method &amp; Accuracy</div><div class="page-sub">How the system works, and what its tests show.</div>', unsafe_allow_html=True)
    tiles([
        ('1. Data', 'Sentinel-2 imagery and 3DEP elevation at 10 m'),
        ('2. Reference', 'Reviewed canyon polygons in separate areas'),
        ('3. YOLO', 'Instance segmentation finds canyon terrain'),
        ('4. Elevation', 'Ridges separate neighboring canyons'),
        ('5. Mapping', 'Coordinates, size and geology are attached'),
    ], 5, 'step')
    st.subheader('Model v2 test results')
    metrics = pd.read_csv(METRICS_FILE)
    tests = metrics[(metrics.model == 'v2') & metrics.split.isin(['test', 'test_lava'])].copy()
    tests['split'] = tests.split.map({'test': 'Zone 1', 'test_lava': 'Lava Falls'})
    tests = tests[['split', 'pixel_precision', 'pixel_recall', 'pixel_iou', 'shape_recall']]
    tests.columns = ['Area', 'Pixel precision', 'Pixel recall', 'Pixel IoU', 'Shape recall']
    st.dataframe(tests, width='stretch', hide_index=True)
    st.warning('The test samples are small, and metrics measure canyon terrain better than separation of each canyon. Detection counts are not a complete canyon inventory.')

    names = load_gnis()
    if len(names):
        st.subheader('Independent check: official USGS GNIS canyon names')
        st.caption('Named tributaries of the Grand Canyon from the U.S. Geological Survey Geographic Names Information System, '
                   'never used in training. A canyon counts as found when a detection lies within 500 m of its mouth-to-head line.')
        canyons = names[names.kind == 'Canyon / Gorge'] if 'kind' in names else names
        content = ''.join(f'<div class="tile stat"><strong>{value}</strong><span>{label}</span></div>' for value, label in [
            (f"{names.found.sum()} / {len(names)}", 'official named tributaries found'),
            (f"{names.found.mean() * 100:.0f}%", 'recall, all named tributaries'),
            (f"{canyons.found.mean() * 100:.0f}%", 'recall, names with Canyon or Gorge'),
            (f"{(names.distance_m <= 2000).mean() * 100:.0f}%", 'recall if 2 km is allowed'),
        ])
        st.markdown(f'<div class="grid g4">{content}</div>', unsafe_allow_html=True)
        if 'reach' in names:
            by_reach = names.groupby('reach').agg(Named=('found', 'size'), Found=('found', 'sum')).reset_index()
            by_reach['Recall %'] = (by_reach.Found / by_reach.Named * 100).round(1)
            by_reach['reach'] = by_reach['reach'].str[2:]
            by_reach = by_reach.rename(columns={'reach': 'Reach of the river'})
            st.dataframe(by_reach, width='stretch', hide_index=True)
            st.info('Recall is highest in the central canyon where the model was trained (83% of true canyons) and lower in '
                    'narrow Marble Canyon and the western canyon, the same pattern as the Lava Falls test.')


def show_data(results):
    st.markdown('<div class="page-title">Data</div><div class="page-sub">Download the saved Grand Canyon catalogue.</div>', unsafe_allow_html=True)
    card('Catalogue', rows([
        ('Detections', len(results)),
        ('Coordinate system', 'WGS 84 (GeoJSON), UTM 12N (GeoPackage)'),
        ('Imagery', 'Copernicus Sentinel-2'),
        ('Elevation', 'USGS 3DEP'),
        ('Geology', 'USGS SGMC'),
        ('Canyon names', 'USGS GNIS (official names, used only for checking and labels)'),
        ('Photos and videos', 'Wikimedia Commons, credited on each item'),
    ]))
    first, second, third = st.columns(3)
    catalogue_file = RESULTS_DIR / 'grand_canyon_detections_named.geojson'
    if not catalogue_file.exists():
        catalogue_file = RESULTS_DIR / 'grand_canyon_detections_geology.geojson'
    first.download_button('Download GeoJSON', catalogue_file.read_bytes(),
                          'grand_canyon_detections.geojson', 'application/geo+json', width='stretch')
    second.download_button('Download CSV', results.drop(columns='geometry').to_csv(index=False),
                           'grand_canyon_detections.csv', 'text/csv', width='stretch')
    third.download_button('Download GeoPackage', (RESULTS_DIR / 'grand_canyon_detections.gpkg').read_bytes(),
                          'grand_canyon_detections.gpkg', 'application/geopackage+sqlite3', width='stretch')



# ---------------- Earth vs Mars (terrestrial analog study) ----------------
EARTH_COLOR, MARS_COLOR = '#7fb7be', '#d9734e'
D_EARTH, D_MARS = 1229, 9237
MARS_PIXEL_M = 200 * D_MARS / D_EARTH
MARS_RADIUS_M = 3396190
VARIABLE_NAMES = {
    'area_D2': 'Area / D²', 'length_D': 'Length / D', 'width_D': 'Width / D', 'elongation': 'Length / width',
    'solidity': 'Solidity (branching)', 'incision_D': 'Incision / D', 'relief_ratio': 'Relief / length',
}
# Classifier results from Step B6 (5-fold cross-validation, random forest)
CLASSIFIER_AUC = [('Plan-view shape only', '0.61 ± 0.06'), ('Vertical only (incision, gradient)', '0.76 ± 0.05'),
                  ('All seven variables', '0.81 ± 0.04')]


def open_mars():
    st.session_state.page = 'Earth vs Mars'


@st.cache_data(show_spinner=False)
def load_analog():
    return pd.read_csv(MARS_DIR / 'b6_robustness_data.csv')


def cliffs_delta(a, b):
    from scipy.stats import mannwhitneyu
    u, p = mannwhitneyu(a, b)
    return 2 * u / (len(a) * len(b)) - 1, p


@st.cache_data(show_spinner=False)
def comparison_table(min_area):
    data = load_analog()
    data = data[data.area_D2 >= min_area]
    earth, mars = data[data.planet == 'Earth'], data[data.planet == 'Mars']
    rows_out = []
    for column, name in VARIABLE_NAMES.items():
        delta, p = cliffs_delta(earth[column], mars[column])
        rows_out.append({'Variable': name, 'Earth median': round(earth[column].median(), 2),
                         'Mars median': round(mars[column].median(), 2),
                         'Mars / Earth': round(mars[column].median() / earth[column].median(), 2),
                         "Cliff's delta": round(delta, 2), 'p value': '< 0.001' if p < 0.001 else f'{p:.3f}',
                         'Different?': 'Yes' if (p < 0.05 and abs(delta) >= 0.15) else 'No'})
    return pd.DataFrame(rows_out), len(earth), len(mars)


@st.cache_data(show_spinner=False)
def planet_map(name):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import rasterio
    from io import BytesIO

    if name == 'Earth':
        depth_file, tributary_file, D = MARS_DIR / 'grand_canyon_incision_depth.tif', MARS_DIR / 'earth_tributaries_frozen.gpkg', D_EARTH
        with rasterio.open(depth_file) as src:
            depth = src.read(1)
            left, top, pixel = src.transform.c, src.transform.f, src.transform.a
            shape_ = depth.shape
    else:
        # Light copy already on the 1,503 m analysis grid (see scripts/prepare_app_data.py)
        tributary_file, D = MARS_DIR / 'mars_tributaries_frozen.gpkg', D_MARS
        with rasterio.open(MARS_DIR / 'valles_marineris_incision_depth_light.tif') as src:
            depth = src.read(1)
            left, top, pixel = src.transform.c, src.transform.f, src.transform.a
            shape_ = depth.shape
    tributaries = gpd.read_file(tributary_file)
    extent = (left, left + shape_[1] * pixel, top - shape_[0] * pixel, top)
    figure, axis = plt.subplots(figsize=(9, 9 * shape_[0] / shape_[1] + 0.4), facecolor='#15110e')
    axis.imshow(np.clip(depth / D, 0, 1), cmap='gray', extent=extent)
    palette = ['#d9734e', '#e9c46a', '#7fb7be', '#f4a261', '#b392ac', '#90a955', '#e76f51', '#a7c4a0']
    tributaries.plot(ax=axis, color=[palette[i % len(palette)] for i in range(len(tributaries))], alpha=0.8, linewidth=0)
    kilometres = (extent[1] - extent[0]) / 1000
    bar = 10 ** np.floor(np.log10(kilometres / 4))
    axis.plot([extent[0] + 0.04 * (extent[1] - extent[0]), extent[0] + 0.04 * (extent[1] - extent[0]) + bar * 1000],
              [extent[2] + 0.06 * (extent[3] - extent[2])] * 2, color='white', linewidth=3)
    axis.text(extent[0] + 0.04 * (extent[1] - extent[0]), extent[2] + 0.09 * (extent[3] - extent[2]),
              f'{bar:,.0f} km', color='white', fontsize=10)
    axis.set_axis_off()
    figure.tight_layout(pad=0)
    buffer = BytesIO()
    figure.savefig(buffer, format='png', dpi=110, facecolor='#15110e')
    plt.close(figure)
    return buffer.getvalue(), len(tributaries)


def ratio_chart(table):
    data = table[['Variable', 'Mars / Earth', 'Different?']].copy()
    data['Result'] = data['Different?'].map({'Yes': 'Different', 'No': 'Similar'})
    bars = alt.Chart(data).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X('Mars / Earth:Q', scale=alt.Scale(domain=[0, 1.4]), title='Mars median ÷ Earth median (1 = identical)'),
        y=alt.Y('Variable:N', sort=None, title=None, axis=alt.Axis(labelLimit=260)),
        color=alt.Color('Result:N', scale=alt.Scale(domain=['Similar', 'Different'], range=[EARTH_COLOR, MARS_COLOR]),
                        legend=alt.Legend(orient='top', title=None)),
        tooltip=['Variable', 'Mars / Earth', 'Result'],
    )
    rule = alt.Chart(pd.DataFrame({'x': [1]})).mark_rule(color='#f4ece1', strokeDash=[4, 4]).encode(x='x:Q')
    chart = (bars + rule).properties(height=300).configure_view(strokeWidth=0).configure(background='transparent') \
        .configure_axis(labelColor='#d8cbbb', titleColor='#b9aa9a', gridColor='#33291f', domainColor='#3a2e25') \
        .configure_legend(labelColor='#d8cbbb')
    st.altair_chart(chart, width='stretch')


def distribution_chart(column, title, log=False):
    data = load_analog()[['planet', column]].rename(columns={column: 'value'})
    if log:
        data['value'] = np.log10(data['value'])
    chart = alt.Chart(data).transform_density('value', groupby=['planet'], as_=['value', 'density']).mark_area(
        opacity=0.55, interpolate='monotone').encode(
        x=alt.X('value:Q', title=title), y=alt.Y('density:Q', title=None, axis=None),
        color=alt.Color('planet:N', scale=alt.Scale(domain=['Earth', 'Mars'], range=[EARTH_COLOR, MARS_COLOR]),
                        legend=alt.Legend(orient='top', title=None)),
    ).properties(height=230).configure_view(strokeWidth=0).configure(background='transparent') \
        .configure_axis(labelColor='#d8cbbb', titleColor='#b9aa9a', gridColor='#33291f', domainColor='#3a2e25') \
        .configure_legend(labelColor='#d8cbbb')
    st.altair_chart(chart, width='stretch')


def show_mars():
    st.markdown('<div class="page-title">Earth vs Mars</div><div class="page-sub">The Grand Canyon as a terrestrial analog '
                'for the side canyons of Valles Marineris, the largest canyon system known in the Solar System.</div>',
                unsafe_allow_html=True)
    for required in ['b6_robustness_data.csv', 'earth_tributaries_frozen.gpkg', 'mars_tributaries_frozen.gpkg',
                     'grand_canyon_incision_depth.tif', 'valles_marineris_incision_depth_light.tif']:
        if not (MARS_DIR / required).exists():
            st.error(f'Missing analysis file: results/mars_analog/{required}. See README, section "Reproduce the analysis".')
            return

    tiles([
        ('Question', 'Do the side canyons of Valles Marineris have the shape of the water-carved tributary canyons of the Grand Canyon?'),
        ('Approach', 'The same elevation-only rules on both planets, written in units of main-canyon depth D and calibrated on Earth first.'),
        ('Answer', 'Same plan-view shape, but Martian side canyons are cut 25–35% less deeply relative to their main canyon.'),
    ], 3)
    table, n_earth, n_mars = comparison_table(0)
    content = ''.join(f'<div class="tile stat"><strong>{value}</strong><span>{label}</span></div>' for value, label in [
        ('1,229 m', 'main-canyon depth D, Grand Canyon'),
        ('9,237 m', 'main-canyon depth D, Valles Marineris'),
        (f'{n_earth} / {n_mars}', 'tributary canyons, Earth / Mars'),
        ('7.5 ×', 'deeper on Mars, so all results use units of D'),
    ])
    st.write('')
    st.markdown(f'<div class="grid g4">{content}</div>', unsafe_allow_html=True)

    section('Tributary canyons on both planets', 'Each colour is one tributary canyon found by the same frozen rules. '
            'Grey shows depth below the plateau (white = deepest). Mars is analysed at 1.5 km pixels so that D spans 6.1 pixels on both planets.')
    left, right = st.columns([1, 1.6])
    with left:
        with st.spinner('Drawing Earth map...'):
            image, count = planet_map('Earth')
        st.image(image, caption=f'Grand Canyon, Earth · {count} tributaries · USGS 3DEP', width='stretch')
    with right:
        with st.spinner('Drawing Mars map...'):
            image, count = planet_map('Mars')
        st.image(image, caption=f'Valles Marineris 92°W–52°W, Mars · {count} tributaries · USGS HRSC–MOLA', width='stretch')

    section('Same shape from above, different depth', 'Medians of seven scale-free variables. A bar near 1 means Mars and Earth match.')
    small = st.toggle('Remove small tributaries (under 2 D²) — robustness check', value=True)
    table, n_earth, n_mars = comparison_table(2 if small else 0)
    ratio_chart(table)
    st.dataframe(table, width='stretch', hide_index=True)
    st.caption(f"Earth n = {n_earth}, Mars n = {n_mars}. Cliff's delta: 0 = no difference, positive = larger on Earth; "
               "'Different' requires p < 0.05 and |delta| ≥ 0.15.")

    first, second = st.columns(2)
    with first:
        st.subheader('Incision / D')
        distribution_chart('incision_D', 'Maximum incision divided by main-canyon depth')
    with second:
        st.subheader('Area / D²')
        distribution_chart('area_D2', 'log10 of area divided by D²', log=True)

    section('Is the difference real?', 'Five robustness checks. The finding holds in all of them.')
    data = load_analog()
    earth, mars = data[data.planet == 'Earth'], data[data.planet == 'Mars']
    delta_local, _ = cliffs_delta(earth.incision_local, mars.incision_local)
    edges = np.quantile(mars.x_km, [0, 1 / 3, 2 / 3, 1])
    parts = [mars[(mars.x_km >= a) & (mars.x_km < b)] for a, b in zip(edges[:-1], list(edges[1:-1]) + [edges[-1] + 1])]
    deltas = [cliffs_delta(earth.incision_D, part.incision_D)[0] for part in parts]
    left, right = st.columns(2)
    with left:
        card('Which variables separate the planets?', rows([(name, f'AUC {value}') for name, value in CLASSIFIER_AUC]) +
             '<div class="unit-sub" style="margin-top:8px">0.5 = indistinguishable, 1.0 = completely different</div>')
        floor = MARS_DIR / 'b4b_floor_sensitivity.csv'
        if floor.exists():
            sensitivity = pd.read_csv(floor)
            card('Floor rule varied', rows([(f"floor {r.floor_depth_D:.2f} D", f"Mars / Earth area {r.mars_median_D2 / r.earth_median_D2:.2f}")
                                            for r in sensitivity.itertuples()]))
    with right:
        card('Incision against the nearby main-canyon depth', rows([
            ('Earth median', f'{earth.incision_local.median():.2f}'), ('Mars median', f'{mars.incision_local.median():.2f}'),
            ("Cliff's delta", f'{delta_local:.2f}')]))
        card('Along the whole canyon (Mars split in three)', rows([
            (name, f"delta {d:.2f}") for name, d in zip(['West (Ius side)', 'Centre (Melas/Candor)', 'East (Coprates side)'], deltas)]))

    section('What it means')
    tiles([
        ('Interpretation', 'The Grand Canyon\'s river cut the main canyon and its tributaries together. Valles Marineris is thought to have deepened mainly by crustal rifting. If water shaped the side canyons, they did not keep pace.'),
        ('What we do not claim', 'Similar shapes can come from different processes (equifinality). The result is consistent with water erosion, not proof of it, and it does not reconstruct the history of Mars.'),
        ('Limitations', '200 m elevation data; one Earth reference canyon; an incomplete calibration catalogue; up to 4% east–west scale error on the Mars grid; gravity differences not modelled.'),
    ], 3)

    section('Download the analysis')
    first, second, third = st.columns(3)
    first.download_button('Earth tributaries (GeoPackage)', (MARS_DIR / 'earth_tributaries_frozen.gpkg').read_bytes(),
                          'earth_tributaries.gpkg', 'application/geopackage+sqlite3', width='stretch')
    second.download_button('Mars tributaries (GeoPackage)', (MARS_DIR / 'mars_tributaries_frozen.gpkg').read_bytes(),
                           'mars_tributaries.gpkg', 'application/geopackage+sqlite3', width='stretch')
    third.download_button('Shape measurements (CSV)', (MARS_DIR / 'b6_robustness_data.csv').read_bytes(),
                          'tributary_shapes_earth_mars.csv', 'text/csv', width='stretch')
    st.markdown(
        '<div class="sources">Sources: <a href="https://astrogeology.usgs.gov/search/map/mars_mgs_mola_mex_hrsc_blended_dem_global_200m" target="_blank">'
        'USGS HRSC–MOLA Blended DEM v2 (Fergason et al., 2018)</a> · USGS 3DEP · '
        '<a href="https://science.nasa.gov/resource/mars-canyon-with-los-angeles-for-scale/" target="_blank">NASA</a> · '
        'Priority-Flood algorithm (Barnes et al., 2014). Mars coordinates use a Mars equirectangular grid, not an Earth coordinate system.</div>',
        unsafe_allow_html=True,
    )


defaults = {'bbox': None, 'result': None, 'selected': None, 'last_drawing': None, 'pending': False,
            'error': None, 'page': 'Home', 'period': 'Summer 2026'}
for name, value in defaults.items():
    if name not in st.session_state:
        st.session_state[name] = value

results = load_results()
brand, navigation = st.columns([1, 3])
brand.markdown('<div class="brand">Canyon<span>Scope</span></div>', unsafe_allow_html=True)
with navigation.container(key='nav'):
    page = st.radio('Navigation', PAGES, key='page', horizontal=True, label_visibility='collapsed')

from ask import show_rova
show_rova()   # floating helper on every page

if page == 'Home':
    show_home(results)
elif page == 'Explorer':
    show_explorer()
elif page == 'Earth vs Mars':
    show_mars()
elif page == 'Results':
    analytics_tab, method_tab, data_tab = st.tabs(['Analytics', 'Method & Accuracy', 'Data'])
    with analytics_tab:
        show_analytics(results)
    with method_tab:
        show_method()
    with data_tab:
        show_data(results)
else:
    from learn import show_learn
    from view3d import show_3d
    basics_tab, view_tab = st.tabs(['Canyon basics', '3D Earth and Mars'])
    with basics_tab:
        show_learn()
    with view_tab:
        show_3d()
