"""Ask Rova: a small floating helper on every page, in English and Arabic.
Visitors pick a question or type their own; Rova answers only from facts written in advance from the project's
results (typed questions are matched to the closest fact by a small offline search with scikit-learn). Other
topics get a polite "I can only help with this project". Nothing is sent outside the app and nothing is invented."""
import base64
import html
import re

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
    'en': 'Hi, I’m Rova, a little Mars rover. I know everything about CanyonScope. Pick a question or type your own.',
    'ar': 'مرحباً، أنا روفا، مركبة صغيرة من المريخ. أعرف كل شيء عن مشروع CanyonScope. اختر سؤالاً أو اكتب سؤالك.',
}
NOT_FOUND = {
    'en': 'Sorry, I can only answer questions about the CanyonScope project: its data, AI, results and the Mars comparison. Try another wording, or pick a question from the list.',
    'ar': 'عذراً، أستطيع الإجابة فقط عن مشروع CanyonScope: بياناته، والذكاء الاصطناعي، والنتائج، والمقارنة مع المريخ. جرّب صياغة أخرى، أو اختر سؤالاً من القائمة.',
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
     {'en': 'Great! Ask me anything about CanyonScope. For example: “What did you find on Mars?”',
      'ar': 'رائع! اسألني أي شيء عن مشروع CanyonScope. مثلاً: «ماذا وجدتِ على المريخ؟»'}),
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
                   'find', 'catalog', 'compare', 'user', 'use it', 'who can', 'problem', 'model',
                   'مشروع', 'تطبيق', 'نموذج', 'درب', 'دقه', 'تحدي', 'قيود', 'حدود', 'اهداف', 'هدف', 'كود', 'بيانات',
                   'عدد', 'قادم', 'وجدت', 'كتالوج', 'مقارن', 'مستفيد', 'مشكل', 'يولو', 'روفا')

def route(text):
    """Decide how Rova answers a typed question: a friendly reply, a project fact, or a polite "only this project"."""
    talk = next((n for n, (pattern, _) in enumerate(SMALL_TALK) if pattern.search(text)), None)
    if talk is not None and len(text.split()) <= 4:
        return ('talk', talk)
    index, score = project_match(text)
    plain = normalise(text) + ' ' + text.lower()
    if re.search(r'canyon|اخدود|اخاديد', plain) and re.search(r'valley|وادي|اوديه', plain):
        return [e[0] for e in ENTRIES].index('Canyon or valley: what is the difference?')
    if re.search(r'between .+ and |\bvs\b|versus|فرق بين|اختلاف بين', plain):
        return None   # comparisons of other things are not about the project
    if score >= 0.3 or (score >= 0.15 and any(marker in plain for marker in PROJECT_MARKERS)):
        return index
    return None


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
                          placeholder='مثلاً: ما أهم التحديات؟' if arabic else 'e.g. What were the main challenges?')
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
