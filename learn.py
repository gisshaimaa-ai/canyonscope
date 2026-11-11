"""Learn page: canyon words explained with a drawn 3D landscape and a short quiz (no data needed)."""
import html

import numpy as np
import streamlit as st

TERMS = [
    ('Valley', 'Any long low area between hills, usually with a river. Often wide, with gentle slopes.'),
    ('Canyon', 'A deep valley with steep, often rocky walls. Deep compared with its width.'),
    ('Gorge', 'A very narrow canyon with near-vertical walls, for example Marble Canyon.'),
    ('Main canyon', 'The largest canyon, cut by the main river (the Colorado River in the Grand Canyon).'),
    ('Tributary canyon', 'A side canyon that joins the main canyon. Its water flows into the main river.'),
    ('Plateau and rim', 'The flat high land around the canyon, and its edge where the walls begin.'),
    ('Mouth and head', 'The mouth is where a side canyon meets the main canyon; the head is where it starts.'),
    ('Wash', 'A dry stream bed that carries water only after rain. Common in the western Grand Canyon.'),
]

COMPARE = [
    ('Shape across', 'U or V shape, gentle slopes', 'Steep walls, often in steps'),
    ('Depth vs width', 'Usually wide and shallow', 'Deep compared with its width'),
    ('Typical place', 'Humid or mountain areas', 'Dry regions with hard rock layers'),
    ('Example', 'A river valley in the mountains', 'The Grand Canyon, 1.2 km deep'),
]

FEATURES = ['Plateau', 'Rim', 'Main canyon', 'Tributary canyons', 'Mouths', 'A wide valley (for comparison)']

QUIZ = [
    ('Which one is deep and steep compared with its width?', ['Valley', 'Canyon', 'Plateau'], 'Canyon'),
    ('A side canyon that joins the main canyon is called a…', ['Tributary', 'Rim', 'Wash'], 'Tributary'),
    ('Where does a tributary’s water enter the main canyon?', ['At its head', 'At its mouth', 'On the plateau'], 'At its mouth'),
    ('“Valles” in Valles Marineris means…', ['Canyons', 'Valleys', 'Mountains'], 'Valleys'),
    ('On which planet are side canyons cut less deeply, relative to the main canyon?', ['Earth', 'Mars', 'Both the same'], 'Mars'),
]


@st.cache_data(show_spinner=False)
def landscape():
    """A drawn landscape (not real data): plateau, a winding main canyon, six side canyons and one wide valley."""
    x = np.linspace(0, 20, 260)
    y = np.linspace(0, 12, 160)
    X, Y = np.meshgrid(x, y)
    centre = 6 + 1.3 * np.sin(X / 3.1)
    main = np.exp(-((Y - centre) / 1.0) ** 6)                      # steep walls, flat floor
    tributaries = np.zeros_like(X)
    mouths = []
    for x0, side, angle in [(3.5, 1, 0.9), (8.5, 1, 1.1), (14.0, 1, 0.8), (6.0, -1, -1.0), (11.5, -1, -0.8), (16.5, -1, -1.2)]:
        y0 = 6 + 1.3 * np.sin(x0 / 3.1) + side * 0.95
        mouths.append((x0, y0))
        length = 3.6
        direction = np.array([np.cos(angle), np.sin(angle) * side * np.sign(angle)])
        direction /= np.linalg.norm(direction)
        t = np.clip(((X - x0) * direction[0] + (Y - y0) * direction[1]) / length, 0, 1)
        px, py = x0 + t * length * direction[0], y0 + t * length * direction[1]
        distance = np.hypot(X - px, Y - py)
        width = 0.45 * (1 - 0.6 * t)
        tributaries = np.maximum(tributaries, 0.55 * (1 - t) ** 0.7 * np.exp(-(distance / width) ** 4))
    valley = 0.18 * np.exp(-(((X - 17.5) / 3.5) ** 2 + ((Y - 11.2) / 1.6) ** 2))   # wide and gentle
    depth = np.maximum(main, tributaries)
    depth = np.maximum(depth, valley)
    height = -depth
    masks = {
        'Plateau': depth < 0.03,
        'Rim': (main > 0.03) & (main < 0.25),
        'Main canyon': main >= 0.25,
        'Tributary canyons': (tributaries > 0.08) & (main < 0.25),
        'A wide valley (for comparison)': valley > 0.03,
    }
    return X, Y, height, masks, mouths


def landscape_figure(feature):
    import plotly.graph_objects as go

    X, Y, Z, masks, mouths = landscape()
    colour = (Z - Z.min()) / (Z.max() - Z.min()) * 0.8          # 0 = floor, 0.8 = plateau
    if feature in masks:
        colour = np.where(masks[feature], 1.0, colour)
    scale = [[0.0, '#4a2a1a'], [0.35, '#a0583a'], [0.65, '#d9a27a'], [0.8, '#efd8b8'], [0.81, '#2fb3c0'], [1.0, '#2fb3c0']]
    figure = go.Figure(go.Surface(x=X, y=Y, z=Z, surfacecolor=colour, cmin=0, cmax=1, colorscale=scale,
                                  showscale=False, hoverinfo='skip',
                                  contours=dict(x=dict(highlight=False), y=dict(highlight=False), z=dict(highlight=False)),
                                  lighting=dict(ambient=0.55, diffuse=0.8, roughness=0.9, specular=0.1)))
    if feature == 'Mouths':
        mx, my = zip(*mouths)
        figure.add_trace(go.Scatter3d(x=mx, y=my, z=[-0.45] * len(mx), mode='markers+text', text=['mouth'] * len(mx),
                                      textfont=dict(color='#ffffff', size=13), marker=dict(size=7, color='#2fb3c0'),
                                      hoverinfo='skip'))
    figure.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='#15110e',
                         scene=dict(xaxis_visible=False, yaxis_visible=False, zaxis_visible=False,
                                    aspectmode='manual', aspectratio=dict(x=2, y=1.2, z=0.45),
                                    camera=dict(eye=dict(x=1.3, y=-1.5, z=0.9)), bgcolor='#15110e'))
    return figure


def show_learn():
    st.markdown('<div class="page-title">Learn: canyons in five minutes</div>'
                '<div class="page-sub">The words used in this project, a landscape you can turn, and a short quiz.</div>',
                unsafe_allow_html=True)

    st.markdown('<div class="section">The words</div>', unsafe_allow_html=True)
    content = ''.join(f'<div class="tile"><b>{html.escape(a)}</b><span>{html.escape(b)}</span></div>' for a, b in TERMS)
    st.markdown(f'<div class="grid g4">{content}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section">Valley or canyon?</div>'
                '<div class="section-sub">Every canyon is a valley, but not every valley is a canyon.</div>',
                unsafe_allow_html=True)
    rows_html = ''.join(f'<tr><td><b>{html.escape(a)}</b></td><td>{html.escape(b)}</td><td>{html.escape(c)}</td></tr>'
                        for a, b, c in COMPARE)
    st.markdown('<div class="card"><table style="width:100%;border-collapse:collapse;font-size:.95rem">'
                '<tr><th style="text-align:left;color:var(--sand)"></th><th style="text-align:left;color:var(--sand)">Valley</th>'
                f'<th style="text-align:left;color:var(--sand)">Canyon</th></tr>{rows_html}</table></div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><h3>And “Valles”?</h3><span style="color:var(--muted)">'
                '<b>Valles</b> is Latin for “valleys”. Valles Marineris means “Mariner valleys”, after the Mariner 9 '
                'spacecraft that mapped it in 1971–72. On Mars, a single steep-sided trough is called a <b>chasma</b>.'
                '</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="section">Explore a landscape</div>'
                '<div class="section-sub">A drawn example, not real data. Choose a feature to light it up in blue; '
                'drag to turn the landscape, scroll to zoom.</div>', unsafe_allow_html=True)
    feature = st.radio('Show', FEATURES, key='learn_feature', horizontal=True)
    st.plotly_chart(landscape_figure(feature), width='stretch', config={'displayModeBar': False})

    st.markdown('<div class="section">Quick quiz</div>', unsafe_allow_html=True)
    score = 0
    answered = 0
    for number, (question, options, answer) in enumerate(QUIZ, start=1):
        choice = st.radio(f'{number}. {question}', options, index=None, key=f'quiz_{number}')
        if choice is not None:
            answered += 1
            if choice == answer:
                score += 1
                st.success('Correct.')
            else:
                st.error(f'Not quite. The answer is: {answer}.')
    if answered == len(QUIZ):
        st.info(f'Your score: {score} of {len(QUIZ)}.')
