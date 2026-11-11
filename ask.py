"""Ask Rova: a small floating helper on every page. Visitors pick a question from a list or type their own.
Every answer is a project fact written in advance; typed questions are matched to the closest one by a small
offline search (scikit-learn). Nothing is sent outside the app and nothing is invented."""
import base64
import html

import streamlit as st

# Rova, an original cartoon Mars rover drawn for this app
ROVA_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
<line x1="60" y1="30" x2="60" y2="12" stroke="#e9c46a" stroke-width="4" stroke-linecap="round"/>
<circle cx="60" cy="10" r="6" fill="#7fb7be"/>
<rect x="22" y="28" width="76" height="48" rx="22" fill="#f4ece1"/>
<rect x="30" y="36" width="60" height="32" rx="16" fill="#15110e"/>
<circle cx="47" cy="52" r="8" fill="#7fb7be"/><circle cx="73" cy="52" r="8" fill="#7fb7be"/>
<circle cx="49" cy="50" r="3" fill="#f4ece1"/><circle cx="75" cy="50" r="3" fill="#f4ece1"/>
<path d="M52 62 Q60 67 68 62" stroke="#e9c46a" stroke-width="3" fill="none" stroke-linecap="round"/>
<rect x="8" y="44" width="14" height="22" rx="4" fill="#e9c46a"/><rect x="98" y="44" width="14" height="22" rx="4" fill="#e9c46a"/>
<rect x="26" y="78" width="68" height="16" rx="8" fill="#d9734e"/>
<circle cx="36" cy="100" r="11" fill="#3a2e25"/><circle cx="60" cy="100" r="11" fill="#3a2e25"/><circle cx="84" cy="100" r="11" fill="#3a2e25"/>
<circle cx="36" cy="100" r="4" fill="#b9aa9a"/><circle cx="60" cy="100" r="4" fill="#b9aa9a"/><circle cx="84" cy="100" r="4" fill="#b9aa9a"/>
</svg>"""
ROVA_URI = 'data:image/svg+xml;base64,' + base64.b64encode(ROVA_SVG.encode()).decode()

GREETING = ("Hi, I’m Rova, a little Mars rover. I know everything about CanyonScope. Pick a question or type your "
            "own, and I’ll answer from the project’s own results.")

QUESTIONS = {
    'What is CanyonScope?': 'An AI that finds the side canyons of the Grand Canyon in free Sentinel-2 satellite images, and then uses them as a reference to compare with the side canyons of Valles Marineris on Mars.',
    'What problem does it solve?': 'There is no consistent map of the Grand Canyon’s side canyons. Drawing them by hand is slow and two people draw them differently. Side canyons matter for drainage, erosion and the debris flows that build the river’s rapids.',
    'Who can use it?': 'Geomorphologists, park and hazard planners, teachers and planetary scientists. It answers: where are the side canyons in my area, how big are they, and what rock are they cut into?',
    'What is a side canyon?': 'A tributary (side) canyon joins the main canyon, and its water flows into the main river. Here it needs at least 250 m of relief and 1 km² of area.',
    'Canyon or valley: what is the difference?': 'Every canyon is a valley, but not every valley is a canyon. A canyon is deep and steep compared with its width; a valley is often wide with gentle slopes. See the Learn page.',
    'Which data does it use?': 'All free and open: Sentinel-2 images (10 m), USGS 3DEP elevation (10 m), the USGS geology map, USGS official names (for checking only), and the USGS HRSC–MOLA elevation model of Mars (200 m).',
    'How does the AI find a canyon?': 'A YOLO model marks canyon ground on overlapping image tiles. Pixels found at least twice are kept. Then elevation data splits that ground into separate canyons along the ridges between them.',
    'How was the AI trained?': '71 canyons were drawn from elevation and checked by hand in QGIS. The area was split by place, so the test area is ground the model never saw. Training: yolo26s-seg, 100 epochs, free Colab GPU.',
    'How accurate is it?': 'In the test area: precision 0.91 and overlap (IoU) 0.68. In an unseen western area, Lava Falls, overlap improved from 0.36 to 0.52 after adding western training areas.',
    'How many canyons were found?': '325 side canyons covering 2,397 km², across the whole Grand Canyon. A live run of 123 km² takes about 39 seconds.',
    'Was it checked against official names?': 'Yes. Of 186 official named canyons, it found 83% in the central canyon, 54% in the west and 25% in narrow Marble Canyon: 70% overall. 108 canyons now show their official name.',
    'Why compare with Mars?': 'Valles Marineris is the largest canyon system we know, about 4,000 km long, and nobody can go there. The Grand Canyon’s side canyons were carved by water, so they are a good reference.',
    'How can you compare such different sizes?': 'Everything is divided by D, the depth of the main canyon: 1,229 m on Earth and 9,237 m on Mars. Rules were set on Earth, frozen, and used on Mars unchanged.',
    'What did you find on Mars?': 'Seen from above, Mars’s side canyons have the same shape as the Grand Canyon’s (within 1–7%). But they are cut about 40% less deeply relative to the main canyon (0.61 times).',
    'Does this prove water on Mars?': 'No. The shape is consistent with water erosion, and the main trough probably deepened by rifting faster than the side canyons. It is a hypothesis, not proof.',
    'What are the limits?': 'Small test sets, trained on Grand Canyon rocks only, weakest in narrow Marble Canyon, and Mars compared at 200 m with one Earth reference.',
    'Where is the code?': 'Open on GitHub: github.com/gisshaimaa-ai/canyonscope (AGPL-3.0 licence).',
}

# Extra search words (English and Arabic) so typed questions find the right answer
KEYWORDS = {
    'What is CanyonScope?': 'about project app idea purpose goal ما هو المشروع فكرة التطبيق هدف',
    'What problem does it solve?': 'problem solve why important matter المشكلة مشكلة تحل أهمية لماذا مهم',
    'Who can use it?': 'users who audience use benefit المستخدمين من يستخدم المستفيد',
    'What is a side canyon?': 'tributary side canyon definition meaning رافد أخدود جانبي تعريف معنى',
    'Canyon or valley: what is the difference?': 'canyon valley gorge difference valles وادي أخدود فرق الفرق',
    'Which data does it use?': 'data sources satellite sentinel images elevation dem البيانات مصادر صور قمر صناعي ارتفاعات',
    'How does the AI find a canyon?': 'how works method pipeline yolo steps elevation watershed كيف يعمل طريقة خطوات الذكاء الاصطناعي',
    'How was the AI trained?': 'train training labels qgis model epochs gpu تدريب التدريب عينات النموذج',
    'How accurate is it?': 'accuracy accurate precision recall iou results good الدقة دقة النتائج',
    'How many canyons were found?': 'how many number count catalogue found canyons كم عدد الأخاديد الكتالوج',
    'Was it checked against official names?': 'gnis official names validation check verify الأسماء الرسمية تحقق التحقق',
    'Why compare with Mars?': 'why mars valles marineris analog reason لماذا المريخ نظير',
    'How can you compare such different sizes?': 'compare size scale depth d divide fair مقارنة الحجم القياس العمق',
    'What did you find on Mars?': 'mars result finding found shape depth similar different نتيجة المريخ وجدت',
    'Does this prove water on Mars?': 'water proof prove hypothesis rifting إثبات الماء ماء مياه يوجد فرضية',
    'What are the limits?': 'limits limitations weakness problems القيود حدود ضعف',
    'Where is the code?': 'code github licence open source الكود جيت هب المصدر',
}


@st.cache_resource(show_spinner=False)
def search_index():
    from sklearn.feature_extraction.text import TfidfVectorizer
    keys = list(QUESTIONS)
    curated = [f'{q} {KEYWORDS.get(q, "")}' for q in keys]
    full = [f'{q} {KEYWORDS.get(q, "")} {QUESTIONS[q]}' for q in keys]
    words = TfidfVectorizer(stop_words='english', token_pattern=r'(?u)\b\w+\b', sublinear_tf=True)
    chars = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True)
    return keys, words, words.fit_transform(curated), chars, chars.fit_transform(full)


def closest_question(text):
    """The listed question closest to a typed one, or None when nothing is close enough."""
    from sklearn.metrics.pairwise import cosine_similarity
    keys, words, word_matrix, chars, char_matrix = search_index()
    scores = (0.75 * cosine_similarity(words.transform([text]), word_matrix)[0]
              + 0.25 * cosine_similarity(chars.transform([text]), char_matrix)[0])
    best = int(scores.argmax())
    return keys[best] if scores[best] >= 0.12 else None


CSS = f"""<style>
.st-key-rova_widget{{position:fixed;right:24px;bottom:24px;z-index:1000;width:auto}}
.st-key-rova_widget button{{border-radius:999px;border:1px solid var(--line);background:var(--panel);
  padding:10px 18px 10px 62px;min-height:56px;font-weight:600;color:var(--text);box-shadow:0 10px 30px rgba(0,0,0,.45);
  background-image:url('{ROVA_URI}');background-repeat:no-repeat;background-size:44px 44px;background-position:10px center}}
.st-key-rova_widget button:hover{{border-color:var(--clay)}}
.rova{{display:flex;gap:12px;align-items:flex-start}}
.rova img{{width:64px;height:64px;flex:none}}
.bubble{{background:#2a201a;border:1px solid var(--line);border-radius:4px 16px 16px 16px;padding:12px 14px;font-size:.92rem;line-height:1.5;color:var(--text)}}
.bubble b{{color:var(--sand)}}
</style>"""


def clear_typed():
    st.session_state.rova_text = ''


def clear_choice():
    st.session_state.rova_question = None


def show_rova():
    st.markdown(CSS, unsafe_allow_html=True)
    with st.container(key='rova_widget'):
        with st.popover('Ask Rova'):
            question = st.selectbox('Choose a question', list(QUESTIONS), index=None, placeholder='Choose a question…',
                                    key='rova_question', on_change=clear_typed)
            typed = st.text_input('…or type your own (English or Arabic)', key='rova_text', on_change=clear_choice,
                                  placeholder='e.g. How many canyons did you find?').strip()
            if typed:
                match = closest_question(typed)
                if match:
                    text = (f'<b>{html.escape(match)}</b><br>{html.escape(QUESTIONS[match])}'
                            '<br><i style="color:var(--muted)">Closest answer I have to your question.</i>')
                else:
                    text = ('I don’t have an answer to that one. I only know about CanyonScope: the data, the AI, '
                            'the results and Mars. Try one of the listed questions.')
            elif question:
                text = f'<b>{html.escape(question)}</b><br>{html.escape(QUESTIONS[question])}'
            else:
                text = html.escape(GREETING)
            st.markdown(f'<div class="rova"><img src="{ROVA_URI}" alt="Rova, a cartoon Mars rover">'
                        f'<div class="bubble">{text}</div></div>', unsafe_allow_html=True)
