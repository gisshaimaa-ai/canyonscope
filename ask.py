"""Ask Rova: a small floating helper on every page, in English and Arabic.
Questions about the project are answered from facts written in advance (offline search with scikit-learn).
Other questions about space, geology, geography or AI are answered from Wikipedia in the question's language,
with the article linked (CC BY-SA 4.0). Questions on other topics get a polite "I can't help with that". The owner can unlock a presenter mode
(password in the Streamlit secrets) in which Rova answers with Google Gemini; visitors never reach Gemini."""
import base64
import html
import json
import re
import urllib.parse
import urllib.request

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

GREETING = {
    'en': 'Hi, I’m Rova, a little Mars rover. Ask me about this project, or anything about space, geology, geography or AI.',
    'ar': 'مرحباً، أنا روفا، مركبة صغيرة من المريخ. اسألني عن المشروع، أو عن أي شيء في الفضاء والجيولوجيا والجغرافيا والذكاء الاصطناعي.',
}
NOT_FOUND = {
    'en': 'Sorry, I can only help with this project, space, geology, geography and AI. Try asking it another way, or pick a question from the list.',
    'ar': 'عذراً، أستطيع المساعدة فقط في المشروع والفضاء والجيولوجيا والجغرافيا والذكاء الاصطناعي. جرّب صياغة السؤال بطريقة أخرى، أو اختر سؤالاً من القائمة.',
}

# Each entry: English question, Arabic question, English answer, Arabic answer, extra search words
ENTRIES = [
    ('What is CanyonScope?', 'ما هو مشروع CanyonScope؟',
     'An AI that finds the side canyons of the Grand Canyon in free Sentinel-2 satellite images, and then uses them as a reference to compare with the side canyons of Valles Marineris on Mars.',
     'ذكاء اصطناعي يكتشف الأخاديد الجانبية في Grand Canyon من صور القمر الصناعي Sentinel-2 المجانية، ثم يستخدمها كمرجع للمقارنة مع الأخاديد الجانبية في Valles Marineris على المريخ.',
     'about project app idea فكره المشروع التطبيق عن'),
    ('What problem does it solve?', 'ما المشكلة التي يحلها المشروع؟',
     'There is no consistent map of the Grand Canyon’s side canyons. Drawing them by hand is slow, and two people draw them differently. Side canyons matter for drainage, erosion and the debris flows that build the river’s rapids.',
     'لا توجد خريطة منتظمة للأخاديد الجانبية في Grand Canyon. رسمها باليد بطيء، وكل شخص يرسمها بشكل مختلف. وهذه الأخاديد مهمة لأنها تتحكم في تصريف المياه والتعرية والسيول التي تصنع المنحدرات في النهر.',
     'problem solve why important matter مشكله تحل اهميه لماذا مهم'),
    ('Who can use it?', 'من يستفيد من المشروع؟',
     'Geomorphologists, park and hazard planners, teachers and planetary scientists. It answers: where are the side canyons in my area, how big are they, and what rock are they cut into?',
     'علماء التضاريس، ومخططو المتنزه والمخاطر، والمعلمون، وعلماء الكواكب. يجيب عن سؤال: أين الأخاديد الجانبية في منطقتي، وما حجمها، وفي أي صخر حُفرت؟',
     'users who audience benefit مستخدمين يستخدم يستفيد مستفيد فائده'),
    ('What are the project goals?', 'ما أهداف المشروع؟',
     'Build and test an AI workflow that outlines each side canyon, and apply it to Mars. Four questions: how accurate is it on new ground, does elevation separate canyons, does it work across the whole Grand Canyon, and do Mars’s side canyons look water-carved?',
     'بناء واختبار ذكاء اصطناعي يرسم حدود كل أخدود جانبي، ثم تطبيقه على المريخ. وفيه أربعة أسئلة بحثية: ما دقته في مناطق جديدة؟ هل تفصل الارتفاعات بين الأخاديد؟ هل يعمل في Grand Canyon كله؟ وهل أخاديد المريخ تشبه أخاديد نحتها الماء؟',
     'goals objective aims research questions هدف اهداف اسئله بحث غايه'),
    ('What is a side canyon?', 'ما هو الأخدود الجانبي (الرافد)؟',
     'A tributary (side) canyon joins the main canyon, and its water flows into the main river. In this project it needs at least 250 m of relief and 1 km² of area.',
     'الأخدود الجانبي (الرافد) هو أخدود يتصل بالأخدود الرئيسي، وتجري مياهه إلى النهر الرئيسي. في هذا المشروع يجب أن يكون فرق ارتفاعه 250 متراً على الأقل ومساحته 1 كم² على الأقل.',
     'tributary side canyon definition meaning رافد روافد جانبي تعريف معنى'),
    ('What is a canyon?', 'ما هو الأخدود؟',
     'A canyon is a deep valley with steep, often rocky walls, usually cut by a river over a very long time. It is deep compared with its width. The Grand Canyon is about 1.2 km deep; Valles Marineris on Mars is about 9 km deep. See the Learn page.',
     'الأخدود وادٍ عميق جدرانه شديدة الانحدار وغالباً صخرية، يحفره نهر في الغالب على مدى زمن طويل جداً، ويكون عميقاً مقارنة بعرضه. عمق Grand Canyon حوالي 1.2 كم، وعمق Valles Marineris على المريخ حوالي 9 كم. شاهد صفحة Learn.',
     'canyon gorge definition meaning اخدود اخاديد تعريف معنى'),
    ('Canyon or valley: what is the difference?', 'ما الفرق بين الوادي والأخدود؟',
     'Every canyon is a valley, but not every valley is a canyon. A canyon is deep and steep compared with its width; a valley is often wide with gentle slopes. See the Learn page.',
     'كل أخدود هو وادٍ، لكن ليس كل وادٍ أخدوداً. الأخدود عميق وجدرانه شديدة الانحدار مقارنة بعرضه، أما الوادي فغالباً عريض ومنحدراته خفيفة. شاهد صفحة Learn.',
     'canyon valley gorge difference valles وادي اوديه اخدود فرق'),
    ('Which data does it use?', 'ما البيانات المستخدمة؟',
     'All free and open: Sentinel-2 images (10 m), USGS 3DEP elevation (10 m), the USGS geology map, USGS official names (for checking only), and the USGS HRSC–MOLA elevation model of Mars (200 m).',
     'كلها مجانية ومفتوحة: صور Sentinel-2 بدقة 10 م، وارتفاعات USGS 3DEP بدقة 10 م، والخريطة الجيولوجية من USGS، والأسماء الرسمية من USGS (للتحقق فقط)، ونموذج ارتفاعات المريخ HRSC–MOLA بدقة 200 م.',
     'data sources satellite sentinel images elevation dem بيانات مصادر مصدر اين جات صور قمر صناعي ارتفاعات'),
    ('How does the AI find a canyon?', 'كيف يكتشف الذكاء الاصطناعي الأخدود؟',
     'A YOLO model marks canyon ground on overlapping image tiles. Pixels found at least twice are kept. Then elevation data splits that ground into separate canyons along the ridges between them.',
     'نموذج YOLO يحدد أرض الأخاديد على مربعات متداخلة من الصورة، ونحتفظ فقط بالأجزاء التي وجدها مرتين على الأقل. بعدها تفصل بيانات الارتفاع هذه الأرض إلى أخاديد مستقلة عند الحواف المرتفعة بينها.',
     'how works method pipeline steps watershed كيف يعمل طريقه خطوات يكتشف يجد ذكاء اصطناعي'),
    ('How was the AI trained?', 'كيف تم تدريب النموذج؟',
     '71 canyons were drawn from elevation and checked by hand in QGIS. The area was split by place, so the test area is ground the model never saw. Training: yolo26s-seg, 100 epochs, on a free Colab GPU.',
     'رسمنا 71 أخدوداً من بيانات الارتفاع وراجعناها يدوياً في QGIS. وقسّمنا المنطقة حسب المكان، فمنطقة الاختبار لم يرها النموذج أبداً. التدريب: yolo26s-seg لمدة 100 دورة على GPU مجاني في Colab.',
     'train training labels qgis epochs gpu تدريب درب عينات نموذج'),
    ('Why YOLO?', 'لماذا اخترتِ YOLO؟',
     'YOLO is fast and open source. It runs on a free GPU for training and on a normal CPU in the web app, and its segmentation version draws outlines, not just boxes.',
     'لأن YOLO سريع ومفتوح المصدر، ويعمل على GPU مجاني في التدريب وعلى معالج عادي في التطبيق، ونسخة segmentation منه ترسم حدود الشيء وليس مربعاً حوله فقط.',
     'why yolo choose model لماذا يولو اختيار اخترت'),
    ('How accurate is it?', 'ما دقة النموذج؟',
     'In the test area: precision 0.91 and overlap (IoU) 0.68. In an unseen western area, Lava Falls, overlap improved from 0.36 to 0.52 after adding western training areas.',
     'في منطقة الاختبار: الدقة (precision) 0.91 والتطابق (IoU) 0.68. وفي منطقة غربية لم يرها النموذج (Lava Falls) تحسّن التطابق من 0.36 إلى 0.52 بعد إضافة مناطق تدريب من الغرب.',
     'accuracy accurate precision recall results good دقه نتائج نتيجه جيد'),
    ('What is IoU?', 'ما معنى IoU؟',
     'IoU means Intersection over Union: the area where the AI outline and the hand-drawn outline overlap, divided by the area they cover together. 0 means no overlap, 1 means perfect.',
     'IoU تعني Intersection over Union: مساحة التطابق بين ما رسمه الذكاء الاصطناعي وما رسمناه باليد، مقسومة على المساحة التي يغطيانها معاً. الصفر يعني لا تطابق، والواحد يعني تطابقاً كاملاً.',
     'iou intersection union overlap معنى تطابق تقاطع'),
    ('How many canyons were found?', 'كم عدد الأخاديد المكتشفة؟',
     '325 side canyons covering 2,397 km², across the whole Grand Canyon. A live run of 123 km² takes about 39 seconds.',
     '325 أخدوداً جانبياً تغطي 2,397 كم² في Grand Canyon كله. والكشف المباشر لمساحة 123 كم² يأخذ حوالي 39 ثانية.',
     'how many number count catalogue found canyons كم عدد اخاديد كتالوج مكتشفه وجدت'),
    ('Was it checked against official names?', 'هل تم التحقق باستخدام الأسماء الرسمية؟',
     'Yes. Of 186 official named canyons, it found 83% in the central canyon, 54% in the west and 25% in narrow Marble Canyon: 70% overall. 108 canyons now show their official name.',
     'نعم. من 186 أخدوداً لها أسماء رسمية، وجد النموذج 83% في الوسط، و54% في الغرب، و25% في Marble Canyon الضيق، أي 70% إجمالاً. وأصبح 108 أخاديد تظهر بأسمائها الرسمية.',
     'gnis official names validation check verify اسماء رسميه تحقق تاكد'),
    ('What were the main challenges?', 'ما أهم التحديات في المشروع؟',
     '1) YOLO alone merged neighbouring canyons into blobs of up to 233 km²; elevation now splits them. 2) The first model was weak in the west (IoU 0.36); new training areas raised it to 0.52. 3) Newer satellite images needed a 1000 offset removed. 4) On Mars, one untested rule cut recall from 76% to 52%, so I recalibrated on Earth and froze the rules. 5) Big Mars files crashed Colab, so I used reduced copies.',
     '1) YOLO وحده دمج الأخاديد المتجاورة في كتل تصل إلى 233 كم²، فأصبحت الارتفاعات تفصلها. 2) النموذج الأول كان ضعيفاً في الغرب (IoU 0.36)، فأضفنا مناطق تدريب جديدة فارتفع إلى 0.52. 3) الصور الحديثة احتاجت حذف إزاحة 1000 من قيمها. 4) على المريخ، قاعدة لم تُختبر خفّضت النتيجة من 76% إلى 52%، فأعدنا المعايرة على الأرض وثبّتنا القواعد. 5) ملفات المريخ الكبيرة أوقفت Colab، فاستخدمنا نسخاً مصغّرة.',
     'challenges difficulties problems faced issues hard تحديات تحدي صعوبات صعوبه مشاكل مشكلات واجهت'),
    ('Why compare with Mars?', 'لماذا المقارنة مع المريخ؟',
     'Valles Marineris is the largest canyon system we know, about 4,000 km long, and nobody can go there. The Grand Canyon’s side canyons were carved by water, so they are a good reference.',
     'لأن Valles Marineris أكبر نظام أخاديد معروف، طوله حوالي 4,000 كم، ولا أحد يستطيع الذهاب إليه. وأخاديد Grand Canyon الجانبية نحتها الماء، فهي مرجع جيد للمقارنة.',
     'why mars valles marineris analog reason لماذا مريخ نظير سبب'),
    ('How can you compare such different sizes?', 'كيف تقارنين بين أحجام مختلفة جداً؟',
     'Everything is divided by D, the depth of the main canyon: 1,229 m on Earth and 9,237 m on Mars. The rules were set on Earth, frozen, and used on Mars unchanged.',
     'نقسم كل شيء على D، وهو عمق الأخدود الرئيسي: 1,229 م على الأرض و9,237 م على المريخ. وضبطنا القواعد على الأرض، ثم ثبّتناها، واستخدمناها على المريخ دون تغيير.',
     'compare size scale depth d divide fair مقارنه حجم احجام قياس عمق'),
    ('What did you find on Mars?', 'ماذا وجدتِ على المريخ؟',
     'Seen from above, Mars’s side canyons have the same shape as the Grand Canyon’s (within 1–7%). But they are cut about 40% less deeply relative to the main canyon (0.61 times).',
     'من الأعلى، شكل الأخاديد الجانبية على المريخ مثل شكلها في Grand Canyon (الفرق 1–7% فقط). لكنها أقل عمقاً بحوالي 40% مقارنة بالأخدود الرئيسي (0.61 مرة).',
     'mars result finding found shape depth similar different نتيجه مريخ وجدت شكل عمق'),
    ('Does this prove water on Mars?', 'هل هذا يثبت وجود ماء على المريخ؟',
     'No. The shape is consistent with water erosion, and the main trough probably deepened by rifting faster than the side canyons. It is a hypothesis, not proof.',
     'لا. الشكل متوافق مع النحت بالماء، والأخدود الرئيسي غالباً تعمّق بسبب تشقق القشرة أسرع من الأخاديد الجانبية. هذه فرضية وليست إثباتاً.',
     'water proof prove hypothesis rifting اثبات يثبت ماء مياه يوجد فرضيه'),
    ('What are the limits?', 'ما حدود المشروع وقيوده؟',
     'Small test sets, trained on Grand Canyon rocks only, weakest in narrow Marble Canyon, and Mars compared at 200 m with one Earth reference.',
     'عينات الاختبار قليلة، والنموذج تدرّب على صخور Grand Canyon فقط، وأضعف أداء في Marble Canyon الضيق، والمقارنة مع المريخ بدقة 200 م ومرجع أرضي واحد.',
     'limits limitations weakness قيود حدود ضعف نقاط'),
    ('What comes next?', 'ما الخطوات القادمة؟',
     'Sharper Mars data (CTX, HiRISE), more Earth analogs including rifted canyons, and side-canyon maps for flash-flood studies. The catalogue will also be shared as a gIQ story.',
     'بيانات أدق للمريخ (CTX وHiRISE)، ونظائر أرضية أكثر منها أخاديد تشكّلت بتشقق القشرة، وخرائط للأخاديد لدراسة السيول. وسيُنشر الكتالوج أيضاً كقصة على gIQ.',
     'next future plans vision مستقبل قادم خطوات رؤيه خطط'),
    ('Where is the code?', 'أين الكود؟',
     'Open on GitHub: github.com/gisshaimaa-ai/canyonscope (AGPL-3.0 licence).',
     'مفتوح على GitHub: github.com/gisshaimaa-ai/canyonscope (ترخيص AGPL-3.0).',
     'code github licence open source كود جيت هب مصدر رابط'),
]

SMALL_TALK = [
    (re.compile(r'^\s*(yes|yeah|ok|okay|sure|نعم|اي|ايوه|أيوه|تمام|طيب|اوكي|أوكي|حسنا|حسناً)\s*[.!؟?]*\s*$', re.I),
     {'en': 'Great! Ask me about this project, or anything about space, geology, geography or AI. For example: “What is a volcano?”',
      'ar': 'رائع! اسألني عن المشروع، أو عن أي شيء في الفضاء والجيولوجيا والجغرافيا والذكاء الاصطناعي. مثلاً: «ما هو البركان؟»'}),
    (re.compile(r'(thank|thanks|شكر|مشكور|يعطيك)', re.I),
     {'en': 'You’re welcome! Ask me anything else about CanyonScope.', 'ar': 'العفو! اسألني أي شيء آخر عن المشروع.'}),
    (re.compile(r'(\bhi\b|hello|hey|how are you|مرحب|السلام|اهلا|أهلا|هلا|حالك|شلونك|كيفك)', re.I),
     {'en': 'Hello! I’m doing great, rolling around Mars. What would you like to know about CanyonScope?',
      'ar': 'أهلاً! أنا بخير وأتجوّل على المريخ. ماذا تريد أن تعرف عن مشروع CanyonScope؟'}),
]

ARABIC = re.compile(r'[\u0600-\u06FF]')
PREFIXES = ('وال', 'بال', 'فال', 'كال', 'لل', 'ال')   # single letters (و ب ل ف) are often part of the word
ARABIC_STOP = {'من', 'في', 'على', 'ما', 'ماذا', 'هل', 'هو', 'هي', 'عن', 'الى', 'لي', 'لنا', 'ان', 'هذا', 'هذه', 'يمكنك',
               'ممكن', 'تقوم', 'شرح', 'اشرح', 'لو', 'سمحت', 'عندك', 'انت', 'مع'}


def normalise(text):
    """Lower case; for Arabic, remove diacritics, unify letter forms and strip common prefixes."""
    text = re.sub(r'[ً-ْـ]', '', text.lower())
    text = text.translate(str.maketrans('أإآىة', 'ااايه'))
    words = []
    for word in re.findall(r'\w+', text):
        if ARABIC.search(word):
            for prefix in PREFIXES:
                if word.startswith(prefix) and len(word) - len(prefix) >= 3:
                    word = word[len(prefix):]
                    break
        if word not in ARABIC_STOP:
            words.append(word)
    return ' '.join(words)


# Changes whenever the questions change, so a cached search index is never reused for a different list
ENTRIES_SIGNATURE = str(hash(tuple(entry[0] for entry in ENTRIES)))


@st.cache_resource(show_spinner=False)
def search_index(signature=None):
    from sklearn.feature_extraction.text import TfidfVectorizer
    curated = [f'{q_en} {q_ar} {extra}' for q_en, q_ar, _, _, extra in ENTRIES]
    full = [f'{q_en} {q_ar} {extra} {a_en} {a_ar}' for q_en, q_ar, a_en, a_ar, extra in ENTRIES]
    words = TfidfVectorizer(preprocessor=normalise, stop_words='english', token_pattern=r'(?u)\b\w+\b', sublinear_tf=True)
    chars = TfidfVectorizer(preprocessor=normalise, analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True)
    return words, words.fit_transform(curated), chars, chars.fit_transform(full)


def closest_entry(text):
    """Index of the entry closest to a typed question, or None when nothing is close enough."""
    from sklearn.metrics.pairwise import cosine_similarity
    words, word_matrix, chars, char_matrix = search_index(ENTRIES_SIGNATURE)
    scores = (0.75 * cosine_similarity(words.transform([text]), word_matrix)[0]
              + 0.25 * cosine_similarity(chars.transform([text]), char_matrix)[0])
    best = int(scores.argmax())
    return best if scores[best] >= 0.12 else None


def project_match(text):
    """(index, score) of the closest project question."""
    from sklearn.metrics.pairwise import cosine_similarity
    words, word_matrix, chars, char_matrix = search_index(ENTRIES_SIGNATURE)
    scores = (0.75 * cosine_similarity(words.transform([text]), word_matrix)[0]
              + 0.25 * cosine_similarity(chars.transform([text]), char_matrix)[0])
    best = int(scores.argmax())
    return best, float(scores[best])


# Words that show a question is about this project rather than general knowledge
PROJECT_MARKERS = ('canyonscope', 'project', 'your', 'you ', 'app', 'rova', 'train', 'accura', 'iou', 'yolo',
                   'challenge', 'limit', 'goal', 'code', 'github', 'data', 'how many', 'next', 'found',
                   'find', 'catalog', 'compare', 'user', 'problem', 'model',
                   'مشروع', 'تطبيق', 'نموذج', 'درب', 'دقه', 'تحدي', 'قيود', 'حدود', 'اهداف', 'هدف', 'كود', 'بيانات',
                   'عدد', 'قادم', 'وجدت', 'كتالوج', 'مقارن', 'مستفيد', 'مشكل', 'يولو', 'روفا')

# Wikipedia answers are kept only when the article is about one of these subjects
TOPIC_WORDS = ('space', 'planet', 'mars', 'martian', 'moon', 'sun', 'solar', 'star', 'galaxy', 'galaxies', 'astronomy',
               'astronomer', 'astronomical', 'orbit', 'satellite', 'nasa', 'spacecraft', 'rocket', 'comet', 'asteroid',
               'universe', 'cosmic', 'cosmology', 'crater', 'telescope', 'black hole', 'geology', 'geological',
               'geologist', 'rock', 'mineral', 'erosion', 'tectonic', 'volcano', 'volcanic', 'earthquake', 'sediment',
               'sedimentary', 'fossil', 'canyon', 'valley', 'river', 'mountain', 'desert', 'glacier', 'climate',
               'geography', 'geographic', 'continent', 'ocean', 'sea', 'lake', 'island', 'country', 'city', 'capital',
               'region', 'map', 'remote sensing', 'elevation', 'latitude', 'artificial intelligence', 'machine learning',
               'neural', 'deep learning', 'algorithm', 'computer vision', 'software', 'programming', 'robot',
               'language model',
               'فضاء', 'كوكب', 'كواكب', 'مريخ', 'قمر', 'اقمار', 'شمس', 'شمسي', 'نجم', 'نجوم', 'مجره', 'مجرات', 'فلك',
               'فلكي', 'مدار', 'صناعي', 'صاروخ', 'مذنب', 'كويكب', 'كون', 'فوهه', 'تلسكوب', 'مركبه', 'ثقب', 'جيولوجيا',
               'جيولوجي', 'جيولوجيه', 'صخر', 'صخور', 'صخري', 'معدن', 'معادن', 'تعريه', 'تكتونيه', 'تكتونيات', 'صفائح',
               'بركان', 'براكين', 'بركاني', 'زلزال', 'زلازل', 'رسوبي', 'رسوبيه', 'احفوره', 'احافير', 'اخدود', 'اخاديد',
               'وادي', 'اوديه', 'نهر', 'انهار', 'جبل', 'جبال', 'صحراء', 'جليد', 'جليدي', 'مناخ', 'جغرافيا', 'جغرافي',
               'جغرافيه', 'قاره', 'قارات', 'محيط', 'بحر', 'بحار', 'بحيره', 'جزيره', 'دوله', 'مدينه', 'عاصمه', 'منطقه',
               'خريطه', 'خرائط', 'استشعار', 'ارتفاع', 'ذكاء اصطناعي', 'تعلم الي', 'تعلم عميق', 'عصبيه', 'خوارزميه',
               'خوارزميات', 'حاسوب', 'برمجه', 'روبوت')

QUESTION_WORDS = re.compile(r'^\s*((what|who|where|when|why|how)( is| are| was| were| do| does| did| can)?( a| an| the)?'
                            r'|tell me about|explain|ما هو|ما هي|ماهو|ماهي|ما هى|ماذا|من هو|من هي|كيف|لماذا|اين|أين|هل|كم|'
                            r'عرف|اشرح|اشرح لي)\s+', re.I)


# Place words name the subject only when they define it ("Paris is the capital…"), not when an article just mentions a place
PLACE_WORDS = {'country', 'city', 'capital', 'region', 'island', 'sea', 'lake', 'ocean', 'continent', 'river', 'mountain',
               'desert', 'valley', 'map', 'دوله', 'مدينه', 'عاصمه', 'منطقه', 'جزيره', 'بحر', 'بحار', 'بحيره', 'محيط',
               'قاره', 'قارات', 'نهر', 'انهار', 'جبل', 'جبال', 'صحراء', 'وادي', 'اوديه', 'خريطه', 'خرائط'}


def on_topic(text, places=True):
    """True when the text is about space, geology, geography or AI (whole words, not parts of other words).
    With places=False, place words (city, river…) do not count."""
    plain = normalise(text)
    tokens = plain.split()
    for keyword in TOPIC_WORDS:
        if not places and keyword in PLACE_WORDS:
            continue
        if ' ' in keyword:
            if keyword in plain:
                return True
            continue
        for token in tokens:
            if token == keyword or token in (keyword + 's', keyword + 'es', keyword + 'ات') or \
                    (len(keyword) >= 5 and token.startswith(keyword)):
                return True
    return False


WIKI_HEADERS = {'User-Agent': 'CanyonScope/1.0 (https://github.com/gisshaimaa-ai/canyonscope; student research project)',
                'Accept': 'application/json'}


def first_sentence(text):
    match = re.search(r'[.!?؟]\s', text)
    return text[:match.start() + 1] if match and match.start() < 300 else text[:300]


def before_location(text):
    """The part of a definition before a location phrase: 'Pizza is an Italian dish originating in Naples' -> 'Pizza is
    an Italian dish originating'. A place mentioned only as a location does not make the article about geography."""
    return re.split(r'\s(?:in|on|at|near|from|located|originating|في|قرب|بالقرب)\s', f' {text} ', maxsplit=1)[0]


def wikipedia_get(base, params):
    """One call to the Wikipedia API, with a descriptive User-Agent (Wikimedia policy) and one retry."""
    import time
    url = f'{base}/w/api.php?' + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers=WIKI_HEADERS)
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=12) as reply:
                return json.load(reply)
        except Exception as error:
            print(f'Wikipedia request failed ({type(error).__name__}: {error}) for {url[:160]}', flush=True)
            if attempt == 0:
                time.sleep(1.5)
    raise ConnectionError('Wikipedia not reachable')


# Articles about films, books, songs, stories or religious texts are never used, even when their title matches
NOT_SCIENCE = re.compile(r'\b(film|movie|novel|book|song|album|band|video game|television|tv series|episode|character|'
                         r'comic|manga|anime|opera|musical|play by|story)\b|فيلم|روايه|كتاب|اغنيه|البوم|مسلسل|شخصيه|قصه|'
                         r'سوره|قران|حديث نبوي|مسرحيه|لعبه فيديو', re.I)
QUERY_STOP = {'what', 'is', 'are', 'the', 'a', 'an', 'of', 'on', 'in', 'how', 'why', 'does', 'do', 'and', 'between',
              'different', 'difference', 'about', 'tell', 'me', 'explain', 'define', 'meaning', 'mean', 'from',
              'far', 'much', 'many', 'did', 'was', 'were', 'which', 'with', 'for', 'its', 'their', 'this', 'that'}


SINGULAR = {'براكين': 'بركان', 'كواكب': 'كوكب', 'نجوم': 'نجم', 'جبال': 'جبل', 'انهار': 'نهر', 'صخور': 'صخر',
            'زلازل': 'زلزال', 'مجرات': 'مجره', 'اقمار': 'قمر', 'اخاديد': 'اخدود', 'اوديه': 'وادي', 'بحار': 'بحر',
            'قارات': 'قاره', 'ثقوب': 'ثقب', 'سوداء': 'اسود', 'شبكات': 'شبكه', 'نيازك': 'نيزك', 'مذنبات': 'مذنب',
            'volcanoes': 'volcano', 'planets': 'planet', 'canyons': 'canyon', 'galaxies': 'galaxy', 'stars': 'star',
            'satellites': 'satellite', 'earthquakes': 'earthquake', 'rivers': 'river', 'mountains': 'mountain'}


def query_words(query):
    words = [w for w in normalise(query).split() if len(w) >= 3 and w not in QUERY_STOP]
    return [SINGULAR.get(w, w) for w in words]


def title_matches(title, words):
    """At least one meaningful word of the question appears in the article title."""
    title_words = normalise(title).split()
    return any(t.startswith(w[:5]) or w.startswith(t[:5]) for w in words for t in title_words if len(t) >= 3)


def clean_extract(text):
    """Remove wiki markup that sometimes stays in the text ([[File:…]], {{…}}, [[link|text]]), even when nested."""
    files = r'(?:ملف|File|Image|صورة)'
    for _ in range(3):   # inner links first: [[صخر|الصخور]] -> الصخور
        text = re.sub(r'\[\[(?!' + files + r':)(?:[^\[\]|]*\|)?([^\[\]|]*)\]\]', r'\1', text)
    text = re.sub(r'\[\[' + files + r':[^\[\]]*\]\]', ' ', text)
    text = re.sub(r'\{\{[^{}]*\}\}', ' ', text)
    text = re.sub(r'\[\[|\]\]|\{\{|\}\}', ' ', text)
    text = re.sub(r'\(\s*[;,،]?\s*\)', '', text)
    text = re.sub(r'\(\s*[;,،]\s*', '(', text)
    text = re.sub(r'\(\s*[^()]{0,15}:\s*\)', '', text)   # empty labels such as (رمزها: )
    return re.sub(r'\s+', ' ', text).strip()


def acceptable(page, question, words, question_on_topic):
    title = page.get('title', '')
    description = page.get('description', '') or ''
    extract = clean_extract(page.get('extract') or '')
    if page.get('missing') or len(extract) < 40 or 'may refer to' in extract[:200] or 'قد يشير' in extract[:200]:
        return None
    sentence = first_sentence(extract)
    if NOT_SCIENCE.search(normalise(f'{description} {sentence}')) or NOT_SCIENCE.search(f'{description} {sentence}'):
        return None
    if words and not title_matches(title, words):
        return None
    definition = f"{before_location(description)} {before_location(' '.join(sentence.split()[:15]))}"
    if on_topic(f'{description} {sentence}', places=False) or on_topic(definition) or \
            (question_on_topic and on_topic(extract[:600], places=False)):
        return extract
    return None


def title_score(title, words):
    """How well the title names the subject: (question words found in it, share of the title they cover)."""
    title_words = [t for t in normalise(title).split() if len(t) >= 3]
    if not title_words:
        return (0, 0.0)
    hits = sum(1 for w in words if any(t.startswith(w[:5]) or w.startswith(t[:5]) for t in title_words))
    covered = sum(1 for t in title_words if any(t.startswith(w[:5]) or w.startswith(t[:5]) for w in words))
    return (hits, covered / len(title_words))


def wikipedia_answer(question, language, max_chars=600):
    """Return a short Wikipedia summary that answers the question, or None.
    Candidates: the article titled exactly like the subject, articles titled like each main word ("Mars", "بركان"),
    and the top search results. Only science articles about space, geology, geography or AI are kept (films, books
    and stories are skipped); the one whose title best names the subject wins."""
    query = QUESTION_WORDS.sub('', question).strip(' ?؟!.') or question
    base = f'https://{language}.wikipedia.org'
    common = {'action': 'query', 'format': 'json', 'formatversion': 2, 'prop': 'extracts|description|info',
              'exintro': 1, 'explaintext': 1, 'inprop': 'url', 'redirects': 1}
    words = query_words(query)
    question_on_topic = on_topic(question)
    titles = [query]
    if question_on_topic:   # single words only when the question itself is about science ("Mars", not "Rome")
        titles += [w for w in words[:3] if w != normalise(query)]
    exact = wikipedia_get(base, {**common, 'titles': '|'.join(titles), 'exlimit': len(titles)})
    asked = [normalise(t) for t in titles]
    redirects = {normalise(r.get('to', '')): normalise(r.get('from', ''))
                 for r in exact.get('query', {}).get('redirects', []) + exact.get('query', {}).get('normalized', [])}

    def requested_order(page):   # keep the exact pages in the order they were asked for: subject first
        name = normalise(page.get('title', ''))
        name = redirects.get(name, name)
        return asked.index(name) if name in asked else len(asked)

    found = wikipedia_get(base, {**common, 'generator': 'search', 'gsrsearch': ' '.join(words) or query,
                                 'gsrlimit': 6, 'exlimit': 6})
    candidates = sorted(exact.get('query', {}).get('pages', []), key=requested_order) + \
        sorted(found.get('query', {}).get('pages', []), key=lambda page: page.get('index', 99))
    best, best_key, seen = None, None, set()
    for order, page in enumerate(candidates):
        title = page.get('title', '')
        if title in seen:
            continue
        seen.add(title)
        extract = acceptable(page, question, words, question_on_topic)
        if not extract:
            continue
        key = (*title_score(title, words), -order)
        if best_key is None or key > best_key:
            best, best_key = (page, extract), key
    if best is None:
        return None
    page, extract = best
    if len(extract) > max_chars:
        cut = max(extract.rfind('. ', 0, max_chars), extract.rfind('.', 0, max_chars))
        extract = extract[:cut + 1] if cut > max_chars // 3 else extract[:max_chars] + '…'
    title = page.get('title', '')
    return {'title': title, 'extract': extract,
            'url': page.get('fullurl', f"{base}/wiki/{urllib.parse.quote(title.replace(' ', '_'))}")}


COMPARE = re.compile(r'(?:difference|differences|different|differ|compare)\b.*?\bbetween\s+(.+?)\s+and\s+(.+?)[?.!]*$'
                     r'|^(.+?)\s+(?:vs\.?|versus)\s+(.+?)[?.!]*$'
                     r'|(?:الفرق|فرق|الاختلاف)\s+بين\s+(.+?)\s+و\s*(.+?)[؟?.!]*$', re.I)


def compared_things(text):
    match = COMPARE.search(text.strip())
    if not match:
        return None
    parts = [p for p in match.groups() if p]
    return [p.strip() for p in parts[:2]] if len(parts) >= 2 else None


WIKI_RULES = 'rules-2026-11-11c'   # change when the answer rules change, so old saved answers are not reused


@st.cache_data(show_spinner=False, ttl=86400)
def cached_wikipedia_answer(question, language, max_chars=600, rules=WIKI_RULES):
    return wikipedia_answer(question, language, max_chars)


def route(text):
    """Decide how Rova answers a typed question."""
    talk = next((n for n, (pattern, _) in enumerate(SMALL_TALK) if pattern.search(text)), None)
    if talk is not None and len(text.split()) <= 4:
        return ('talk', talk)
    index, score = project_match(text)
    plain = normalise(text) + ' ' + text.lower()
    if re.search(r'canyon|اخدود|اخاديد', plain) and re.search(r'valley|وادي|اوديه', plain):
        return [e[0] for e in ENTRIES].index('Canyon or valley: what is the difference?')
    if query_words(QUESTION_WORDS.sub('', text).strip(' ?؟!.')) in (['canyon'], ['canyons'], ['اخدود'], ['اخاديد']):
        return [e[0] for e in ENTRIES].index('What is a canyon?')
    if score >= 0.45 or (score >= 0.2 and any(marker in plain for marker in PROJECT_MARKERS)):
        return index
    things = compared_things(text)
    if things:
        try:
            articles = [cached_wikipedia_answer(thing, language_of(text), 300, WIKI_RULES) for thing in things]
        except Exception:
            return ('offline', None)
        if all(articles):
            return ('compare', articles)
        return None
    try:
        article = cached_wikipedia_answer(text, language_of(text), 600, WIKI_RULES)
    except Exception:
        article = 'offline'
    if article == 'offline':
        return index if score >= 0.25 else ('offline', None)
    if article:
        return ('wiki', article)
    return index if score >= 0.25 else None


# ---------- Presenter mode: Rova answers with Google Gemini (owner only, unlocked with a password) ----------
# Needs two Streamlit secrets: GEMINI_API_KEY and ROVA_PRESENTER_PASSWORD (optional: GEMINI_MODEL).
# Visitors never reach Gemini; they get the project facts and Wikipedia answers above.

def secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def presenter_ready():
    return bool(secret('GEMINI_API_KEY')) and bool(secret('ROVA_PRESENTER_PASSWORD'))


def check_password():
    import hmac
    typed = st.session_state.get('rova_pw', '')
    expected = str(secret('ROVA_PRESENTER_PASSWORD', ''))
    st.session_state.rova_presenter = bool(expected) and hmac.compare_digest(typed.encode(), expected.encode())
    st.session_state.rova_pw_wrong = bool(typed) and not st.session_state.rova_presenter
    st.session_state.rova_pw = ''


def presenter_off():
    st.session_state.rova_presenter = False


@st.cache_data(show_spinner=False, ttl=86400)
def gemini_model(key):
    """The model to use: GEMINI_MODEL if set, else the newest available 'flash' model that can write text."""
    chosen = secret('GEMINI_MODEL')
    if chosen:
        return chosen
    request = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200',
                                     headers={'x-goog-api-key': key})
    with urllib.request.urlopen(request, timeout=20) as reply:
        models = json.load(reply).get('models', [])
    names = [m['name'].removeprefix('models/') for m in models
             if 'generateContent' in m.get('supportedGenerationMethods', [])]
    flash = [n for n in names if 'flash' in n and 'lite' not in n and 'image' not in n and 'tts' not in n
             and 'preview' not in n and 'exp' not in n]
    return sorted(flash)[-1] if flash else (names[0] if names else 'gemini-2.5-flash')


def ask_gemini(question, earlier):
    key = secret('GEMINI_API_KEY')
    facts = '\n'.join(f'- {q_en} {a_en}' for q_en, _, a_en, _, _ in ENTRIES)
    instruction = (
        'You are Rova, a friendly cartoon Mars rover and the helper of CanyonScope, a GeoAI student project. '
        'Answer questions about the project, space, planetary science, geology, geography and AI tools. '
        'Politely decline other topics in one sentence. Reply in the language of the question (Arabic or English), '
        'in plain, simple words, at most 120 words, without markdown. '
        'For anything about the project, use ONLY these facts and never invent numbers; if the facts do not cover it, '
        'say you do not know:\n' + facts)
    contents = []
    for asked, said in earlier[-4:]:
        contents.append({'role': 'user', 'parts': [{'text': asked}]})
        contents.append({'role': 'model', 'parts': [{'text': said}]})
    contents.append({'role': 'user', 'parts': [{'text': question}]})
    body = {'system_instruction': {'parts': [{'text': instruction}]}, 'contents': contents,
            'generationConfig': {'temperature': 0.3, 'maxOutputTokens': 600}}
    request = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{gemini_model(key)}:generateContent',
        data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
    with urllib.request.urlopen(request, timeout=40) as reply:
        result = json.load(reply)
    parts = result.get('candidates', [{}])[0].get('content', {}).get('parts', [])
    text = ''.join(part.get('text', '') for part in parts).strip()
    if not text:
        raise ValueError(f'empty Gemini reply: {str(result)[:200]}')
    return text


def language_of(text):
    return 'ar' if ARABIC.search(text) else 'en'


def remember(question, index, language, typed):
    st.session_state.rova_history.append((question, index, language, typed))
    st.session_state.rova_history = st.session_state.rova_history[-12:]


def on_choice():
    choice = st.session_state.rova_question
    if choice:
        language = 'ar' if st.session_state.rova_lang == 'العربية' else 'en'
        labels = [entry[1] if language == 'ar' else entry[0] for entry in ENTRIES]
        remember(choice, labels.index(choice), language, False)
    st.session_state.rova_question = None


def on_typed():
    text = st.session_state.rova_text.strip()
    if text:
        if st.session_state.get('rova_presenter'):
            earlier = [(q, i[1]) for q, i, _, _ in st.session_state.rova_history
                       if isinstance(i, tuple) and i[0] == 'gemini']
            try:
                remember(text, ('gemini', ask_gemini(text, earlier)), language_of(text), True)
            except Exception as error:
                print(f'Gemini failed ({type(error).__name__}: {error})', flush=True)
                remember(text, route(text), language_of(text), True)
        else:
            remember(text, route(text), language_of(text), True)
    st.session_state.rova_text = ''


def clear_history():
    st.session_state.rova_history = []


CSS = f"""<style>
@keyframes rova-hover{{0%,100%{{background-position:10px 60%}}50%{{background-position:10px 35%}}}}
@keyframes rova-float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-6px)}}}}
@keyframes rova-fly{{0%{{opacity:0;transform:translate(60px,-28px) rotate(-8deg) scale(.85)}}
  60%{{opacity:1;transform:translate(-6px,4px) rotate(2deg) scale(1.02)}}100%{{transform:translate(0,0) rotate(0) scale(1)}}}}
@keyframes rova-glide{{0%,100%{{transform:translateY(0) rotate(0)}}50%{{transform:translateY(-4px) rotate(-.6deg)}}}}
.st-key-rova_widget{{position:fixed;right:24px;bottom:24px;z-index:1000;width:auto}}
.st-key-rova_widget button{{border-radius:999px;border:1px solid var(--line);background:var(--panel);
  padding:10px 18px 10px 62px;min-height:56px;font-weight:600;color:var(--text);box-shadow:0 10px 30px rgba(0,0,0,.45);
  background-image:url('{ROVA_URI}');background-repeat:no-repeat;background-size:44px 44px;background-position:10px center;
  animation:rova-hover 2.6s ease-in-out infinite}}
.st-key-rova_widget button:hover{{border-color:var(--clay)}}
.rova{{display:flex;gap:10px;align-items:flex-start;margin:6px 0}}
.rova img{{width:52px;height:52px;flex:none;animation:rova-float 2.6s ease-in-out infinite}}
.bubble{{background:#2a201a;border:1px solid var(--line);border-radius:4px 16px 16px 16px;padding:10px 13px;font-size:.9rem;
  line-height:1.55;color:var(--text);box-shadow:0 6px 18px rgba(0,0,0,.35)}}
.bubble.new{{animation:rova-fly .9s cubic-bezier(.2,.8,.2,1) both, rova-glide 4s ease-in-out .9s infinite}}
.bubble b{{color:var(--sand)}}
.bubble i{{color:var(--muted)}}
.asked{{display:flex;justify-content:flex-end;margin:10px 0 2px}}
.asked span{{background:var(--clay);color:#fff;border-radius:16px 4px 16px 16px;padding:7px 12px;font-size:.88rem;max-width:85%}}
.st-key-rova_clear button{{background-image:none;padding:4px 14px;min-height:0;animation:none;box-shadow:none}}
@media (prefers-reduced-motion:reduce){{.st-key-rova_widget button,.rova img,.bubble.new{{animation:none}}}}
</style>"""


def rova_says(text, language, new=False):
    direction = ' dir="rtl" style="text-align:right"' if language == 'ar' else ''
    css = 'bubble new' if new else 'bubble'
    return (f'<div class="rova"><img src="{ROVA_URI}" alt="Rova, a cartoon Mars rover">'
            f'<div class="{css}"{direction}>{text}</div></div>')


def show_rova():
    st.markdown(CSS, unsafe_allow_html=True)
    if 'rova_history' not in st.session_state:
        st.session_state.rova_history = []
    with st.container(key='rova_widget'):
        with st.popover('Ask Rova'):
            language_choice = st.radio('Language', ['English', 'العربية'], key='rova_lang', horizontal=True,
                                       label_visibility='collapsed')
            arabic = language_choice == 'العربية'
            labels = [entry[1] if arabic else entry[0] for entry in ENTRIES]
            st.selectbox('اختر سؤالاً' if arabic else 'Choose a question', labels, index=None,
                         placeholder='اختر سؤالاً' if arabic else 'Choose a question…',
                         key='rova_question', on_change=on_choice)
            st.text_input('أو اكتب سؤالك واضغط Enter' if arabic else '…or type your own and press Enter (English or Arabic)',
                          key='rova_text', on_change=on_typed,
                          placeholder='مثلاً: ما هي الصفائح التكتونية؟' if arabic else 'e.g. How did the Grand Canyon form?')
            history = st.session_state.rova_history
            with st.container(height=330, border=False):
                if not history:
                    language = 'ar' if arabic else 'en'
                    st.markdown(rova_says(html.escape(GREETING[language]), language, new=True), unsafe_allow_html=True)
                for number, (question, index, language, typed) in enumerate(history):
                    newest = number == len(history) - 1
                    direction = ' dir="rtl"' if language_of(question) == 'ar' else ''
                    parts = [f'<div class="asked"><span{direction}>{html.escape(question)}</span></div>']
                    if index is None:
                        answer = html.escape(NOT_FOUND[language])
                    elif isinstance(index, tuple) and index[0] == 'talk':
                        answer = html.escape(SMALL_TALK[index[1]][1][language])
                    elif isinstance(index, tuple) and index[0] == 'gemini':
                        answer = (html.escape(index[1]).replace('\n', '<br>') +
                                  '<br><i>' + ('أُجيب بمساعدة Gemini' if language == 'ar' else 'Answered with Gemini') + '</i>')
                    elif isinstance(index, tuple) and index[0] == 'offline':
                        answer = html.escape('لم أستطع الوصول إلى ويكيبيديا الآن. حاول بعد قليل.' if language == 'ar'
                                             else 'I couldn’t reach Wikipedia right now. Please try again in a moment.')
                    elif isinstance(index, tuple) and index[0] == 'compare':
                        source = ('المصدر: ويكيبيديا (CC BY-SA 4.0) — ليست من نتائج المشروع' if language == 'ar'
                                  else 'Source: Wikipedia (CC BY-SA 4.0), not part of the project results')
                        intro = 'إليك كل واحد منهما:' if language == 'ar' else 'Here is each one, so you can compare:'
                        answer = html.escape(intro) + ''.join(
                            f'<br><b>{html.escape(a["title"])}</b><br>{html.escape(a["extract"])}' for a in index[1])
                        answer += ''.join(f'<br><i><a href="{html.escape(a["url"])}" target="_blank" style="color:var(--sand)">'
                                          f'{source} · {html.escape(a["title"])}</a></i>' for a in index[1])
                    elif isinstance(index, tuple) and index[0] == 'wiki':
                        article = index[1]
                        source = ('المصدر: ويكيبيديا (CC BY-SA 4.0) — ليست من نتائج المشروع' if language == 'ar'
                                  else 'Source: Wikipedia (CC BY-SA 4.0), not part of the project results')
                        answer = (f'<b>{html.escape(article["title"])}</b><br>{html.escape(article["extract"])}'
                                  f'<br><i><a href="{html.escape(article["url"])}" target="_blank" '
                                  f'style="color:var(--sand)">{source}</a></i>')
                    else:
                        q_en, q_ar, a_en, a_ar, _ = ENTRIES[index]
                        title, body = (q_ar, a_ar) if language == 'ar' else (q_en, a_en)
                        answer = f'<b>{html.escape(title)}</b><br>{html.escape(body)}'
                        if typed:
                            answer += '<br><i>' + ('أقرب جواب عندي لسؤالك.' if language == 'ar' else 'The closest answer I have to your question.') + '</i>'
                    parts.append(rova_says(answer, language, new=newest))
                    st.markdown(''.join(parts), unsafe_allow_html=True)
            if history:
                st.button('مسح المحادثة' if arabic else 'Clear chat', key='rova_clear', on_click=clear_history)
            if presenter_ready():
                with st.expander('Presenter', expanded=False):
                    if st.session_state.get('rova_presenter'):
                        st.caption('Presenter mode is on: Rova answers with Gemini.')
                        st.button('Turn off', key='rova_presenter_off', on_click=presenter_off)
                    else:
                        st.text_input('Password', type='password', key='rova_pw', on_change=check_password)
                        if st.session_state.get('rova_pw_wrong'):
                            st.caption('Wrong password.')
