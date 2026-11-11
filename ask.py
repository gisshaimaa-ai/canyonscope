"""Ask page: a chatbot that answers only from the project's own facts.

Without a key it finds the closest fact (TF-IDF search, no internet). If the app owner adds GEMINI_API_KEY in the
Streamlit secrets, Google Gemini writes the answer, but it is given only these facts and told not to add others.
"""
import json
import urllib.request

import streamlit as st

# (topic, answer, extra search words incl. Arabic)
FACTS = [
    ('About CanyonScope', 'CanyonScope is a GeoAI project and web app. It finds the tributary (side) canyons of the Grand Canyon in free Sentinel-2 satellite images with a YOLO model, separates them with elevation data, and uses the result as a reference to compare with the side canyons of Valles Marineris on Mars.', 'project about purpose goal مشروع فكرة هدف ما هو'),
    ('Problem', 'There is no consistent, repeatable map of the side canyons of the Grand Canyon. Drawing them by hand is slow and subjective, because canyons branch and shadows and rock colours hide their edges. Side canyons matter because they control drainage, erosion and the debris flows that build the rapids.', 'problem why matters solve مشكلة المشكلة تحل لماذا أهمية'),
    ('Users', 'Users are geomorphologists, park and hazard planners, educators and planetary scientists. The app answers: where are the side canyons in my area, how big are they, and what rock are they cut into?', 'users who audience مستخدم من'),
    ('Research questions', 'RQ1: how accurately does AI map canyon ground in unseen areas? RQ2: does elevation data split neighbouring canyons? RQ3: does the model work across the whole Grand Canyon? RQ4: do the side canyons of Valles Marineris share the shape of water-carved Grand Canyon tributaries?', 'research questions objective أسئلة البحث هدف'),
    ('Definition of a side canyon', 'A tributary (side) canyon is a valley that joins the Colorado River canyon, with at least 250 m of relief and 1 km² of area, above the main canyon floor.', 'tributary definition side canyon رافد تعريف أخدود جانبي'),
    ('Canyon versus valley', 'Every canyon is a valley, but not every valley is a canyon. A canyon is deep and steep-walled compared with its width; a valley is often wide with gentle slopes. A gorge is a very narrow canyon. "Valles" is Latin for valleys; Valles Marineris means "Mariner valleys".', 'canyon valley gorge difference valles وادي أخدود فرق'),
    ('Satellite images', 'The images are Copernicus Sentinel-2 Level-2A from the European Space Agency, read through Microsoft Planetary Computer: red, green and blue bands at 10 m, summer 2026, under 10% cloud. The 1000 offset of processing baseline 4 is removed, and the same fixed 8-bit stretch is used in training and in the app.', 'sentinel imagery images data source sources come from satellite صور قمر صناعي بيانات البيانات مصدر'),
    ('Elevation data', 'Earth elevation is the USGS 3DEP DEM at 10 m. Mars elevation is the USGS HRSC–MOLA blended DEM v2 at 200 m (Fergason et al., 2018). A DEM (digital elevation model) gives the height of every pixel.', 'dem elevation 3dep mola hrsc ارتفاعات'),
    ('Geology', 'Rock units come from the USGS State Geologic Map Compilation (SGMC), at about 1:1,000,000. It is a regional map, not a canyon-scale rock map.', 'geology rock sgmc جيولوجيا صخر'),
    ('Training labels', 'There was no ready-made label set. Candidate outlines were drawn from elevation, then checked and corrected by hand in QGIS: 71 reference canyons covering 457 km².', 'labels annotation reference training data qgis عينات تدريب'),
    ('Spatial split', 'The pilot area was split into strips from west to east: zone 1 test, zones 2 and 3 training, zone 4 validation. The test area is ground the model never saw; random tiles would overlap and inflate the scores.', 'split test train validation zones تقسيم اختبار تدريب'),
    ('Model', 'The model is Ultralytics yolo26s-seg (YOLO = You Only Look Once; s = small; seg = segmentation). Training: 100 epochs, patience 30, image size 640, batch 8, seed 42, on a free Google Colab T4 GPU.', 'yolo model training epochs gpu نموذج تدريب'),
    ('Why YOLO', 'YOLO segmentation is fast, open source, runs on a free GPU and on a CPU web server, and draws outlines rather than boxes.', 'why yolo choice لماذا يولو'),
    ('Detection steps', 'Detection: 640-pixel tiles with a 320-pixel step (50% overlap), confidence 0.05, and only pixels found at least twice are kept. Then a watershed on the elevation splits canyon ground into separate canyons along the ridges, from valleys 50, 90 and 130 m below their 1 km surroundings. Canyons of 1–25 km² are kept.', 'pipeline steps how works watershed votes طريقة كيف يعمل'),
    ('Why elevation is needed', 'YOLO alone merged neighbouring canyons into blobs of up to 233 km². Elevation splits them along the ridges: AI finds the ground, physics separates the canyons.', 'elevation why merge 233 دمج ارتفاعات لماذا'),
    ('Accuracy of the model', 'Model v2 in test zone 1: precision 0.907, recall 0.726, IoU 0.676, shape recall 0.75. At Lava Falls, an unseen western area, IoU rose from 0.36 (v1) to 0.52 (v2), with precision 0.79 and recall 0.60.', 'accuracy accurate accurately how good performance score results precision recall دقة الدقة النتائج نتائج'),
    ('IoU', 'IoU means Intersection over Union: the area where the model and the reference outlines overlap, divided by the area they cover together. It goes from 0 (no overlap) to 1 (perfect).', 'iou intersection union meaning معنى'),
    ('Model v2', 'Model v1 was strong in the pilot area but weak in the west. Model v2 added reference areas in Marble Canyon and the western canyon and kept Lava Falls as an unseen test. It generalises much better.', 'v2 version improvement تحسين نسخة'),
    ('Catalogue', 'The v2 model ran over the whole Grand Canyon in 157 resumable blocks and found 325 side canyons covering 2,397 km². Each has size, confidence, coordinates and dominant rock unit. A 123 km² live run takes about 39 s. The catalogue is experimental, not a complete inventory.', 'catalogue how many canyons number count find found total كتالوج الكتالوج عدد كم الأخاديد'),
    ('Official names check (GNIS)', 'As an independent check, the official USGS GNIS names list has 186 named canyons that open into the Grand Canyon, never used in training. CanyonScope found 82.9% in the central canyon, 53.5% in the west and 25.0% in narrow Marble Canyon: 69.9% overall. 108 catalogue canyons received their official name.', 'gnis names validation official أسماء رسمية تحقق'),
    ('Why some show “Unnamed”', 'Most small side canyons have no official name. A canyon gets a name only when an official canyon lies within 500 m, so the app never guesses a wrong name.', 'unnamed name بدون اسم'),
    ('Why Mars', 'Valles Marineris is the largest known canyon system, about 4,000 km long. Nobody can visit it, so the Grand Canyon, whose side canyons were carved by water, is used as a terrestrial analog.', 'valles marineris analog reason why choose لماذا نظير'),
    ('Scale-free comparison', 'D is the main-canyon depth: 1,229 m on Earth and 9,237 m on Mars (7.5 times deeper). Every measurement is divided by D, and Mars is analysed at 1,503 m pixels and Earth at 200 m so that D spans 6.1 pixels on both.', 'D depth scale compare units قياس مقارنة'),
    ('Tributary on Mars', 'A tributary is defined by water flow: all canyon ground whose water enters the main canyon floor at one point (Priority-Flood filling, D8 flow directions, main floor as sinks). The same frozen rules are used on both planets.', 'tributary flow priority flood d8 rules'),
    ('Frozen rules', 'All rules were calibrated on Earth only, then frozen in a file before the Mars run: trunk depth 0.5 D, floor depth 0.95 D, floor half-width 0.5 D, window 4 D, rim depth 0.05 D, minimum incision 0.15 D, minimum area 1 D². On Earth they match the YOLO catalogue with recall 71%.', 'frozen rules calibration تجميد قواعد'),
    ('Mars result', 'With the same rules, 273 tributaries were found on Earth and 188 on Mars. From above, their shapes are similar (Mars ÷ Earth 1.01–1.07, no significant difference). In depth they differ: incision relative to D is 0.32 on Mars vs 0.53 on Earth, 0.61 times (Cliff\'s delta 0.60, p < 0.001).', 'mars result found find findings shape depth similar different discover نتيجة النتيجة المريخ وجدت'),
    ('Robustness', 'The result held in five checks: changing the floor rule, removing small canyons, shape-only vs depth-only classifiers (AUC 0.61 vs 0.76), depth against the nearby trough (still 0.74 times), and west, centre and east of Mars separately.', 'robustness checks auc متانة'),
    ('Interpretation', 'The side canyons of Valles Marineris have the shape of water-carved valleys, but the main trough deepened mainly through crustal rifting, and the side canyons did not keep pace. This is consistent with water erosion, not proof of it.', 'interpretation water rifting meaning proof تفسير ماء الماء إثبات'),
    ('Limitations', 'Small test sets; trained on Grand Canyon rocks only; weakest in narrow Marble Canyon; catalogue is experimental; confidence is not a probability; Mars compared at 200 m with one Earth reference.', 'limitations weaknesses قيود القيود ضعف'),
    ('App and code', 'The app runs at canyonscope.streamlit.app on Streamlit Community Cloud. The code is open at github.com/gisshaimaa-ai/canyonscope under AGPL-3.0, because Ultralytics YOLO uses that licence.', 'app github code licence agpl تطبيق كود'),
    ('Future work', 'Next steps: sharper Mars terrain (CTX, HiRISE), more Earth analogs including rifted canyons, and side-canyon maps for flash-flood and debris-flow studies.', 'future next vision مستقبل رؤية'),
]


@st.cache_resource(show_spinner=False)
def search_index():
    from sklearn.feature_extraction.text import TfidfVectorizer
    keywords = [f'{topic} {extra}' for topic, answer, extra in FACTS]            # curated words weigh most
    documents = [f'{topic} {extra} {answer}' for topic, answer, extra in FACTS]
    words = TfidfVectorizer(stop_words='english', token_pattern=r'(?u)\b\w+\b', sublinear_tf=True)
    chars = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True)
    return words, words.fit_transform(keywords), chars, chars.fit_transform(documents)


def find_facts(question, top=3):
    from sklearn.metrics.pairwise import cosine_similarity
    words, word_matrix, chars, char_matrix = search_index()
    scores = (0.75 * cosine_similarity(words.transform([question]), word_matrix)[0]
              + 0.25 * cosine_similarity(chars.transform([question]), char_matrix)[0])
    order = scores.argsort()[::-1][:top]
    return [(FACTS[i], float(scores[i])) for i in order]


def secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def ask_gemini(question, key, model):
    facts = '\n'.join(f'- {topic}: {answer}' for topic, answer, _ in FACTS)
    instruction = ('You are the CanyonScope project assistant. Answer ONLY from the facts below. If the facts do not '
                   'contain the answer, say you do not know and suggest the Method & Accuracy page. Answer in the same '
                   'language as the question, in at most 120 words, in simple words.\n\nFacts:\n' + facts)
    body = {'system_instruction': {'parts': [{'text': instruction}]},
            'contents': [{'role': 'user', 'parts': [{'text': question}]}],
            'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 400}}
    request = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
    with urllib.request.urlopen(request, timeout=30) as response:
        reply = json.load(response)
    return reply['candidates'][0]['content']['parts'][0]['text'].strip()


def answer(question):
    key = secret('GEMINI_API_KEY')
    if key:
        try:
            return ask_gemini(question, key, secret('GEMINI_MODEL', 'gemini-2.5-flash')), 'AI (Google Gemini), using only the project facts'
        except Exception:
            pass   # fall back to the search below
    matches = find_facts(question)
    best, score = matches[0]
    if score < 0.08:
        return ("I could not find that in the project facts. Try asking about the data, the model, the accuracy, "
                "the official names check or the Mars comparison."), 'project facts search'
    text = f'**{best[0]}.** {best[1]}'
    related = [topic for (topic, _, _), s in matches[1:] if s > 0.08]
    if related:
        text += '\n\nRelated: ' + ', '.join(related)
    return text, 'project facts search'


def show_ask():
    ai_on = bool(secret('GEMINI_API_KEY'))
    st.markdown('<div class="page-title">Ask about the project</div>'
                '<div class="page-sub">Questions are answered only from CanyonScope’s own facts and results.</div>',
                unsafe_allow_html=True)
    if ai_on:
        st.caption('AI mode: answers are written by Google Gemini from the project facts. Your question is sent to Google; '
                   'do not type personal information.')
    else:
        st.caption('Search mode: the closest project fact is shown. Nothing is sent outside the app.')
    examples = ['What problem does it solve?', 'How accurate is the model?', 'What did you find on Mars?', 'What is IoU?']
    columns = st.columns(len(examples))
    clicked = None
    for column, example in zip(columns, examples):
        if column.button(example, key=f'ask_example_{example}', width='stretch'):
            clicked = example
    if 'chat' not in st.session_state:
        st.session_state.chat = []
    question = st.chat_input('Type a question, in English or Arabic') or clicked
    if question:
        reply, source = answer(question)
        st.session_state.chat.append(('user', question, ''))
        st.session_state.chat.append(('assistant', reply, source))
    for role, text, source in st.session_state.chat:
        with st.chat_message(role):
            st.markdown(text)
            if source:
                st.caption(f'Source: {source}')
