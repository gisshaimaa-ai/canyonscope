"""3D page: the Grand Canyon and Valles Marineris as depth below the plateau, side by side."""
from pathlib import Path

import numpy as np
import streamlit as st

TERRAIN_FILE = Path(__file__).resolve().parent / 'results/mars_analog/terrain_3d.npz'
EARTH_SCALE = [[0.0, '#123c40'], [0.35, '#2f7f86'], [0.7, '#b9a27a'], [1.0, '#efe3c8']]
MARS_SCALE = [[0.0, '#2a0f07'], [0.35, '#7e3219'], [0.7, '#c8714a'], [1.0, '#f2c9a0']]


@st.cache_data(show_spinner=False)
def load_terrain():
    data = np.load(TERRAIN_FILE)
    return {key: data[key] for key in data.files}


def planet_figure(name, mode, exaggeration):
    import plotly.graph_objects as go

    terrain = load_terrain()
    key = name.lower()
    depth = terrain[f'{key}_depth'].astype('float32')
    pixel, D = float(terrain[f'{key}_pixel_m']), float(terrain[f'{key}_D_m'])
    rows, cols = depth.shape
    x = np.arange(cols) * pixel
    y = (rows - 1 - np.arange(rows)) * pixel
    if mode == 'Relative (÷ D)':
        x, y, z, unit = x / D, y / D, -depth / D, 'D'
        z_label = 'Depth below plateau (D)'
    else:
        x, y, z, unit = x / 1000, y / 1000, -depth / 1000, 'km'
        z_label = 'Depth below plateau (km)'
    colour = 1 - np.clip(depth / D, 0, 1)
    figure = go.Figure(go.Surface(
        x=x, y=y, z=z, surfacecolor=colour, cmin=0, cmax=1, colorscale=EARTH_SCALE if name == 'Earth' else MARS_SCALE,
        showscale=False, hovertemplate=f'%{{z:.2f}} {unit}<extra></extra>',
        lighting=dict(ambient=0.5, diffuse=0.85, roughness=0.9, specular=0.05)))
    width, height = x.max(), y.max()
    vertical = (np.nanmax(-z) * exaggeration) / width
    figure.update_layout(
        height=470, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='#15110e',
        scene=dict(aspectmode='manual', aspectratio=dict(x=1.6, y=1.6 * height / width, z=max(1.6 * vertical, 0.05)),
                   xaxis=dict(title=f'East ({unit})', color='#b9aa9a', gridcolor='#3a2e25', backgroundcolor='#15110e'),
                   yaxis=dict(title=f'North ({unit})', color='#b9aa9a', gridcolor='#3a2e25', backgroundcolor='#15110e'),
                   zaxis=dict(title=z_label, color='#b9aa9a', gridcolor='#3a2e25', backgroundcolor='#15110e'),
                   camera=dict(eye=dict(x=0.9, y=-1.6, z=1.0)), bgcolor='#15110e'))
    return figure, rows * pixel / 1000, cols * pixel / 1000, D


def show_3d():
    st.markdown('<div class="page-title">3D view: Earth and Mars</div>'
                '<div class="page-sub">Depth below the surrounding plateau, from the same maps used in the Earth vs Mars '
                'analysis. Drag to turn, scroll to zoom.</div>', unsafe_allow_html=True)
    left, right = st.columns([2, 1])
    mode = left.radio('Scale', ['Relative (÷ D)', 'True size (km)'], key='view_mode', horizontal=True)
    exaggeration = right.slider('Vertical exaggeration', 1, 20, 5, key='view_exaggeration')

    earth_col, mars_col = st.columns(2)
    for column, name, place in [(earth_col, 'Earth', 'Grand Canyon, Arizona'), (mars_col, 'Mars', 'Valles Marineris, 92°W–52°W')]:
        figure, north_km, east_km, D = planet_figure(name, mode, exaggeration)
        with column:
            st.markdown(f'<div class="card"><h3>{name}: {place}</h3><span style="color:var(--muted)">'
                        f'{east_km:,.0f} × {north_km:,.0f} km · main-canyon depth D = {D:,.0f} m</span></div>',
                        unsafe_allow_html=True)
            st.plotly_chart(figure, width='stretch', config={'displayModeBar': False}, key=f'view_{name}')

    if mode == 'Relative (÷ D)':
        st.info('Divided by their own depth D, both regions are about 220–250 D wide: at this scale the two canyon systems '
                'are the same size, so their shapes can be compared fairly. This is the scale used in the analysis.')
    else:
        st.info('At true size, the Mars region shown is about 8.6 times wider than the Earth region (2,345 vs 273 km), '
                'and its main canyon is 7.5 times deeper. Each plot has its own axes; compare the numbers on them.')
    st.caption('Elevation: USGS 3DEP (Earth, 800 m cells here) and USGS HRSC–MOLA blended DEM v2 (Mars, 6 km cells here). '
               'Depth below the plateau is computed by grey closing, as in notebooks/mars_analog.ipynb.')
