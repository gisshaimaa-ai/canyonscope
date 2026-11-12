"""Ask Rova: a small floating helper on every page, in English and Arabic.
Visitors pick a topic and a question, or type their own. Rova answers only from a bank of about 100 answers written
and checked in advance (rova_bank.py): the project, canyons and Earth, Mars and space, satellites and maps, and AI.
Typed questions are matched to the closest answer by a small offline search with scikit-learn; anything else gets a
polite "sorry". Nothing is sent outside the app and nothing is invented."""
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
    'en': 'Hi, I’m Rova, a little Mars rover. I have about 100 checked answers about CanyonScope, canyons, Mars and space, satellites and AI. Pick a topic and a question, or type your own.',
    'ar': 'مرحباً، أنا روفا، مركبة صغيرة من المريخ. عندي حوالي 100 جواب مراجَع عن مشروع CanyonScope، والأخاديد، والمريخ والفضاء، والأقمار الصناعية، والذكاء الاصطناعي. اختر موضوعاً وسؤالاً، أو اكتب سؤالك.',
}
NOT_FOUND = {
    'en': 'Sorry, I don’t have a checked answer for that. I can answer about CanyonScope, canyons and Earth, Mars and space, satellites and maps, and AI. Try another wording, or pick a question from the list.',
    'ar': 'عذراً، ليس عندي جواب مراجَع عن هذا. أستطيع الإجابة عن مشروع CanyonScope، والأخاديد والأرض، والمريخ والفضاء، والأقمار الصناعية والخرائط، والذكاء الاصطناعي. جرّب صياغة أخرى، أو اختر سؤالاً من القائمة.',
}

from rova_bank import TOPICS

ENTRIES = [entry for _, _, entries in TOPICS for entry in entries]
TOPIC_OF = [number for number, (_, _, entries) in enumerate(TOPICS) for _ in entries]

SMALL_TALK = [
    (re.compile(r'(who are you|what are you|your name|من انت|من أنت|مين انت|مين أنت|شو اسمك|ما اسمك)', re.I),
     {'en': 'I’m Rova, a little cartoon Mars rover and the helper of CanyonScope. I answer from about 100 checked answers. Ask me about the project, canyons, Mars and space, satellites or AI.',
      'ar': 'أنا روفا، مركبة مريخية كرتونية صغيرة ومساعِدة مشروع CanyonScope. أجيب من حوالي 100 جواب مراجَع. اسألني عن المشروع أو الأخاديد أو المريخ والفضاء أو الأقمار الصناعية أو الذكاء الاصطناعي.'}),
    (re.compile(r'^\s*(yes|yeah|ok|okay|sure|نعم|اي|ايوه|أيوه|تمام|طيب|اوكي|أوكي|حسنا|حسناً)\s*[.!؟?]*\s*$', re.I),
     {'en': 'Great! Ask me about CanyonScope, canyons, Mars or AI. For example: “What did you find on Mars?”',
      'ar': 'رائع! اسألني عن مشروع CanyonScope أو الأخاديد أو المريخ أو الذكاء الاصطناعي. مثلاً: «ماذا وجدتِ على المريخ؟»'}),
    (re.compile(r'(thank|thanks|شكر|مشكور|يعطيك)', re.I),
     {'en': 'You’re welcome! Ask me anything else.', 'ar': 'العفو! اسألني أي شيء آخر.'}),
    (re.compile(r'(\bhi\b|hello|hey|how are you|مرحب|السلام|اهلا|أهلا|هلا|حالك|شلونك|كيفك)', re.I),
     {'en': 'Hello! I’m doing great, rolling around Mars. What would you like to know?',
      'ar': 'أهلاً! أنا بخير وأتجوّل على المريخ. ماذا تريد أن تعرف؟'}),
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
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    stop = sorted(ENGLISH_STOP_WORDS - {'made', 'far', 'many', 'side'})   # these words help find the right answer
    words = TfidfVectorizer(preprocessor=normalise, stop_words=stop, token_pattern=r'(?u)\b\w+\b', sublinear_tf=True)
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


# Words that show a question is about one of Rova's topics (used when the match is only fair)
TOPIC_MARKERS = ('canyonscope', 'project', 'your', 'you ', 'app', 'rova', 'train', 'accura', 'iou', 'yolo',
                 'challenge', 'limit', 'goal', 'code', 'github', 'data', 'how many', 'next', 'found',
                 'find', 'catalog', 'compare', 'user', 'use it', 'who can', 'problem', 'model',
                 'canyon', 'valley', 'river', 'rock', 'erosion', 'geolog', 'mars', 'martian', 'planet', 'space',
                 'moon', 'satellite', 'sentinel', 'map', 'elevation', ' ai', 'artificial', 'learning',
                 'neural', 'gpu',
                 'مشروع', 'تطبيق', 'نموذج', 'درب', 'دقه', 'تحدي', 'قيود', 'حدود', 'اهداف', 'هدف', 'كود', 'بيانات',
                 'عدد', 'قادم', 'وجدت', 'كتالوج', 'مقارن', 'مستفيد', 'مشكل', 'يولو', 'روفا',
                 'اخدود', 'اخاديد', 'وادي', 'نهر', 'صخر', 'تعري', 'جيولوج', 'مريخ', 'كوكب', 'فضاء', 'قمر', 'شمس',
                 'نجم', 'صناعي', 'خريط', 'ارتفاع', 'ذكاء', 'تعلم', 'شبك')


COMPARE_WORDS = {'what', 'is', 'are', 'the', 'a', 'an', 'difference', 'different', 'differences', 'between', 'and',
                 'vs', 'versus', 'compare', 'compared', 'with', 'of', 'how', 'فرق', 'اختلاف', 'بين', 'و', 'كيف',
                 'يختلف', 'تختلف', 'مقارنه'}


def route(text):
    """Decide how Rova answers a typed question: a friendly reply, a checked answer from the bank, or a polite sorry."""
    talk = next((n for n, (pattern, _) in enumerate(SMALL_TALK) if pattern.search(text)), None)
    if talk is not None and len(text.split()) <= 4:
        return ('talk', talk)
    index, score = project_match(text)
    plain = normalise(text) + ' ' + text.lower()
    if re.search(r'canyon|اخدود|اخاديد', plain) and re.search(r'valley|وادي|اوديه', plain):
        return [e[0] for e in ENTRIES].index('Canyon or valley: what is the difference?')
    if re.search(r'between .+ and |\bvs\b|versus|فرق بين|اختلاف بين', plain):
        # A comparison is answered only when the answer covers every thing being compared
        q_en, q_ar, _, _, extra = ENTRIES[index]
        covered = set(normalise(f'{q_en} {q_ar} {extra}').split())
        compared = set(normalise(text).split()) - COMPARE_WORDS
        if score < 0.3 or not compared <= covered:
            return None
    if score >= 0.3 or (score >= 0.15 and any(marker in plain for marker in TOPIC_MARKERS)):
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
            topic = st.selectbox('الموضوع' if arabic else 'Topic', range(len(TOPICS)), key='rova_topic',
                                 format_func=lambda n: TOPICS[n][1] if arabic else TOPICS[n][0])
            labels = [entry[1] if arabic else entry[0] for entry in TOPICS[topic][2]]
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
