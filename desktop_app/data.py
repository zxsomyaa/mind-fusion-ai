"""
Static data + small helper functions used across the whole app.
This is a Python port of the data.js file from the original web app,
trimmed down to what the desktop version actually needs.
"""

# ---------------------------------------------------------------------------
# Colors (matches the web app's design tokens so the desktop app looks the
# same). Qt stylesheets use these as plain hex strings.
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#FAF8F4",
    "surface": "#FFFFFF",
    "primary": "#8B5E3C",
    "primary_light": "#C8956C",
    "primary_pale": "#F5EDE5",
    "sage": "#7D9B76",
    "sage_pale": "#EFF5EE",
    "sage_light": "#B5CDB2",
    "text": "#3D2C1E",
    "text_muted": "#8A7168",
    "border": "#E8DDD5",
    "on_primary": "#FFFFFF",   # text colour used on top of the primary colour
}

LIGHT_COLORS = dict(COLORS)
DARK_COLORS = {
    "bg": "#1B1714",
    "surface": "#26211D",
    "primary": "#D4A373",
    "primary_light": "#E6BC8F",
    "primary_pale": "#3A2F27",
    "sage": "#9DBB96",
    "sage_pale": "#26332A",
    "sage_light": "#4E6B4A",
    "text": "#F1E9E2",
    "text_muted": "#A99B90",
    "border": "#3B332D",
    "on_primary": "#1B1714",
}


def apply_theme(name):
    """Switch the shared COLORS dict to the light or dark palette *in place*,
    so every module that did `from data import COLORS as C` sees the change
    the next time it builds a widget or stylesheet."""
    COLORS.update(DARK_COLORS if name == "dark" else LIGHT_COLORS)

# ---------------------------------------------------------------------------
# Mood system
# ---------------------------------------------------------------------------
MOODS = {
    "happy":    {"emoji": "😊", "label": "Happy",    "color": "#E97D3F", "bg": "#FEF3E6"},
    "calm":     {"emoji": "😌", "label": "Calm",     "color": "#74C69D", "bg": "#EAF7F0"},
    "sad":      {"emoji": "😢", "label": "Sad",      "color": "#748CAB", "bg": "#EBF0F5"},
    "anxious":  {"emoji": "😰", "label": "Anxious",  "color": "#B5838D", "bg": "#F5EAEC"},
    "stressed": {"emoji": "😤", "label": "Stressed", "color": "#E07A5F", "bg": "#FCEEE9"},
    "grateful": {"emoji": "🙏", "label": "Grateful", "color": "#D4A017", "bg": "#FDF6E3"},
    "tired":    {"emoji": "😴", "label": "Tired",    "color": "#A8DADC", "bg": "#EAF6F7"},
    "hopeful":  {"emoji": "🌱", "label": "Hopeful",  "color": "#52B788", "bg": "#EBF7F2"},
}

MOOD_WORDS = {
    "happy":    ["happy", "joyful", "excited", "great", "wonderful", "fantastic", "amazing", "love", "laugh", "smile", "cheerful", "delighted", "thrilled", "elated", "ecstatic", "awesome", "brilliant", "enjoy", "glad", "pleased"],
    "calm":     ["calm", "peaceful", "relaxed", "serene", "tranquil", "quiet", "centered", "balanced", "zen", "content", "ease", "fine", "alright", "steady", "grounded", "composed", "settled"],
    "sad":      ["sad", "unhappy", "down", "depressed", "miserable", "cry", "crying", "tears", "lonely", "empty", "hopeless", "gloomy", "heartbroken", "hurt", "grief", "lost", "alone", "terrible", "awful", "devastated"],
    "anxious":  ["anxious", "anxiety", "worry", "worried", "nervous", "scared", "fear", "afraid", "panic", "tense", "uneasy", "dread", "apprehensive", "restless", "overthinking", "on edge", "racing thoughts"],
    "stressed": ["stressed", "stress", "overwhelmed", "pressure", "burnout", "struggling", "overloaded", "frazzled", "swamped", "deadline", "behind", "chaotic", "chaos", "too much"],
    "grateful": ["grateful", "thankful", "appreciate", "blessed", "lucky", "fortunate", "gratitude", "thank you", "thanks", "appreciative", "abundance"],
    "tired":    ["tired", "exhausted", "fatigue", "sleepy", "drained", "worn out", "no energy", "weary", "sluggish", "lethargic", "depleted", "heavy", "low energy"],
    "hopeful":  ["hopeful", "hope", "optimistic", "looking forward", "positive", "better", "improve", "progress", "trying", "getting there", "working on", "can do"],
}

MOOD_FALLBACKS = {
    "happy":    "Something brightened your day - I can feel it in your words. What's been sparking that joy?",
    "calm":     "There's a quiet steadiness in what you've shared. That kind of peace is worth protecting.",
    "sad":      "Whatever you're carrying right now, you don't have to carry it alone. I'm right here with you.",
    "anxious":  "Your mind is working overtime and that's genuinely exhausting. Let's slow things down together.",
    "stressed": "You're carrying a heavy load right now. It makes complete sense to feel stretched thin.",
    "grateful": "Gratitude has such a warm energy to it. It sounds like something good found its way into your day.",
    "tired":    "Your body and mind are asking for rest - that's a real signal worth listening to.",
    "hopeful":  "There's something quietly brave about holding onto hope. That reaching-forward in you matters.",
}


CRISIS_PHRASES = [
    "kill myself", "suicide", "suicidal", "end my life", "want to die", "wanna die",
    "self harm", "self-harm", "hurt myself", "don't want to live", "dont want to live",
    "no reason to live", "better off dead", "take my own life",
    # Hindi / Hinglish
    "marna chahta", "marna chahti", "mar jana chahta", "mar jana chahti", "jeene ka mann nahi",
    "jeene ka man nahi", "khudkushi", "aatmahatya", "atmahatya", "khud ko khatam",
    "आत्महत्या", "मरना चाहता", "मरना चाहती", "जीने का मन नहीं", "खुद को खत्म",
]

CRISIS_FALLBACK = (
    "I'm really glad you told me. What you're feeling matters, and you don't have to hold it alone - "
    "please reach out to someone right now, like a crisis line or a person you trust. "
    "If you might act on these thoughts, call your local emergency number."
)


def detect_crisis(text):
    """True if the text contains language suggesting self-harm or suicide.
    Deliberately simple and over-cautious: a false alarm just shows a support
    banner, a miss could matter a lot more."""
    lower = text.lower()
    return any(phrase in lower for phrase in CRISIS_PHRASES)


# Hindi / Hinglish (Hindi typed in Roman letters) / Urdu-romanised keywords,
# added to the English lists above. Both Devanagari and Roman spellings are
# included because people commonly type either way, e.g. "mujhe dar lagta hai".
HINDI_MOOD_WORDS = {
    "anxious":  ["dar", "darr", "dara", "dari", "darta", "darti", "darna", "डर", "डरा", "डरी", "डरता", "डरती",
                 "ghabrahat", "ghabra", "ghabraya", "ghabrai", "घबराहट", "घबरा", "घबराया", "घबराई",
                 "chinta", "चिंता", "fikar", "fikr", "फिक्र", "फ़िक्र", "bechain", "bechaini", "बेचैन", "बेचैनी"],
    "stressed": ["tension", "tanav", "तनाव", "pareshan", "pareshani", "परेशान", "परेशानी", "bojh", "बोझ"],
    "sad":      ["udaas", "udas", "उदास", "dukhi", "दुखी", "dukh", "दुख", "rona", "रोना", "akela", "akeli",
                 "अकेला", "अकेली", "nirash", "निराश", "hataash", "हताश", "bura lag", "बुरा लग"],
    "tired":    ["thak", "thaka", "thaki", "थका", "थकी", "thakan", "thakaan", "थकान", "kamzor", "कमज़ोर", "कमजोर"],
    "happy":    ["khush", "khushi", "खुश", "खुशी", "masti", "maza", "मज़ा", "मजा", "prasann", "प्रसन्न"],
    "calm":     ["shant", "शांत", "sukoon", "सुकून", "aaram", "आराम", "theek", "ठीक"],
    "grateful": ["shukriya", "शुक्रिया", "dhanyavaad", "dhanyawad", "धन्यवाद", "aabhari", "आभारी", "shukr", "शुक्र"],
    "hopeful":  ["umeed", "ummid", "उम्मीद", "asha", "आशा", "bharosa", "भरोसा", "behtar", "बेहतर"],
}
for _mood, _words in HINDI_MOOD_WORDS.items():
    MOOD_WORDS[_mood] = MOOD_WORDS[_mood] + _words

_EDGE_PUNCTUATION = "\"'`.,!?;:()[]{}<>-_*~|/\\…।“”‘’—–"


def _normalise(text):
    """Lowercase text as a single space-padded string of whitespace-separated
    words with punctuation trimmed off each word, so a keyword can be matched
    as a whole word or phrase (" dar " matches "mujhe dar lagta hai" but not
    "dark" - plain substring matching would). Splitting on whitespace rather
    than a regex \\w keeps Devanagari words intact (their vowel signs are not
    counted as word characters by \\w)."""
    words = [w.strip(_EDGE_PUNCTUATION) for w in text.lower().split()]
    return " " + " ".join(w for w in words if w) + " "


def detect_mood(text):
    """Very simple keyword-based mood detector (no ML model needed).
    Returns a dict merged from MOODS plus 'mood' and 'confidence' keys.
    Understands English plus Hindi / Hinglish keywords."""
    padded = _normalise(text)
    scores = {}
    for mood, words in MOOD_WORDS.items():
        scores[mood] = sum(1 for w in words if f" {w} " in padded)

    total = sum(scores.values())
    if total == 0:
        return {"mood": "calm", "confidence": 0.3, **MOODS["calm"]}

    top_mood = max(scores, key=scores.get)
    confidence = min(scores[top_mood] / max(total, 3), 1.0)
    return {"mood": top_mood, "confidence": confidence, **MOODS[top_mood]}


# ---------------------------------------------------------------------------
# Onboarding data
# ---------------------------------------------------------------------------
COUNTRIES = [
    {"code": "US", "name": "United States",  "flag": "🇺🇸"},
    {"code": "GB", "name": "United Kingdom", "flag": "🇬🇧"},
    {"code": "CA", "name": "Canada",         "flag": "🇨🇦"},
    {"code": "AU", "name": "Australia",      "flag": "🇦🇺"},
    {"code": "IN", "name": "India",          "flag": "🇮🇳"},
    {"code": "DE", "name": "Germany",        "flag": "🇩🇪"},
    {"code": "FR", "name": "France",         "flag": "🇫🇷"},
    {"code": "ES", "name": "Spain",          "flag": "🇪🇸"},
    {"code": "IT", "name": "Italy",          "flag": "🇮🇹"},
    {"code": "JP", "name": "Japan",          "flag": "🇯🇵"},
    {"code": "BR", "name": "Brazil",         "flag": "🇧🇷"},
    {"code": "MX", "name": "Mexico",         "flag": "🇲🇽"},
    {"code": "NG", "name": "Nigeria",        "flag": "🇳🇬"},
    {"code": "ZA", "name": "South Africa",   "flag": "🇿🇦"},
    {"code": "NZ", "name": "New Zealand",    "flag": "🇳🇿"},
    {"code": "SG", "name": "Singapore",      "flag": "🇸🇬"},
    {"code": "AE", "name": "UAE",            "flag": "🇦🇪"},
    {"code": "PK", "name": "Pakistan",       "flag": "🇵🇰"},
    {"code": "PH", "name": "Philippines",    "flag": "🇵🇭"},
    {"code": "KE", "name": "Kenya",          "flag": "🇰🇪"},
]

LANGUAGES = [
    {"code": "en", "name": "English",   "locale": "en-US"},
    {"code": "es", "name": "Español",   "locale": "es-ES"},
    {"code": "fr", "name": "Français",  "locale": "fr-FR"},
    {"code": "de", "name": "Deutsch",   "locale": "de-DE"},
    {"code": "it", "name": "Italiano",  "locale": "it-IT"},
    {"code": "pt", "name": "Português", "locale": "pt-BR"},
    {"code": "hi", "name": "हिंदी",      "locale": "hi-IN"},
    {"code": "ja", "name": "日本語",      "locale": "ja-JP"},
    {"code": "ar", "name": "العربية",    "locale": "ar-SA"},
    {"code": "zh", "name": "中文",        "locale": "zh-CN"},
]

# Languages the companion can reply in - chosen from the Chat page, separately from
# the language picked at sign-up. "auto" follows whatever language you write in, and
# "hinglish" is Hindi typed in English letters (which many people text in).
LANGUAGE_ENGLISH_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
    "pt": "Portuguese", "hi": "Hindi", "ja": "Japanese", "ar": "Arabic", "zh": "Chinese",
}
CHAT_LANGUAGES = (
    [{"code": "auto", "name": "Match what I write"},
     {"code": "en", "name": "English"},
     {"code": "hi", "name": "हिंदी (Hindi)"},
     {"code": "hinglish", "name": "Hinglish (Hindi in English letters)"}]
    + [{"code": l["code"], "name": l["name"]} for l in LANGUAGES if l["code"] not in ("en", "hi")]
)
WHISPER_LANGUAGES = set(LANGUAGE_ENGLISH_NAMES)      # codes speech-to-text can be told about


def default_chat_language(profile_language):
    """What replies use until the user picks something: the language chosen at
    sign-up, or 'auto' for English (so it also follows people who write another language)."""
    return profile_language if profile_language in LANGUAGE_ENGLISH_NAMES and profile_language != "en" else "auto"


def language_instruction(code):
    """The line added to the model's instructions for a reply language ('' if unknown)."""
    if code == "auto":
        return ("Reply in the same language the person writes in. They may mix languages or write Hindi in "
                "English letters - if so, reply the same way.")
    if code == "hinglish":
        return ("IMPORTANT: Reply in Hinglish - Hindi written in English (Roman) letters, the way people text, "
                "e.g. \"Mujhe samajh aa raha hai ki tum kaisa feel kar rahe ho.\" Never use Devanagari script.")
    if code == "en":
        return "IMPORTANT: Reply in English, even if the person writes in another language."
    if code in LANGUAGE_ENGLISH_NAMES:
        name = LANGUAGE_ENGLISH_NAMES[code]
        # Small local models are prone to sliding back into whatever language the
        # conversation history is already in (or, for a language they're weak at
        # like Arabic, into English or a transliteration) unless told firmly and
        # concretely what "reply in X" excludes. Spelling that out - script,
        # no English, no transliteration, ignore prior turns - measurably
        # improves compliance with llama3.2 in testing; see build_system_prompt,
        # which also repeats this instruction as the first line, not just the last.
        return (f"IMPORTANT: Respond entirely in {name} - {name} script only, no English words and no "
                f"transliteration - even if the person writes in another language or the conversation "
                f"so far has been in a different language.")
    return ""


def language_reminder(code):
    """A short reminder inserted as its own message right before the final
    user turn (see chat_tab.py), not just in the system prompt - tested
    directly against Ollama, a small local model follows a language switch
    far more reliably when the instruction sits right next to the turn it
    generates from, rather than only at the start of the conversation. '' when
    no reminder is needed (auto - there is nothing to remind it to do)."""
    if code in (None, "", "auto"):
        return ""
    if code == "hinglish":
        return ("REMINDER: reply in Hinglish (Hindi written in English letters), not Devanagari, regardless "
                "of what language earlier messages in this conversation were in.")
    name = LANGUAGE_ENGLISH_NAMES.get(code, "English" if code == "en" else None)
    if name:
        return (f"REMINDER: reply in {name} script only - no English, no other language, no transliteration - "
                f"regardless of what language earlier messages in this conversation were in.")
    return ""


def whisper_language(code):
    """Language hint for speech-to-text, or None to let it detect (auto / Hinglish)."""
    return code if code in WHISPER_LANGUAGES else None


AGE_GROUPS = [
    {"id": "18-24", "label": "18 - 24"},
    {"id": "25-34", "label": "25 - 34"},
    {"id": "35-44", "label": "35 - 44"},
    {"id": "45-54", "label": "45 - 54"},
    {"id": "55-64", "label": "55 - 64"},
    {"id": "65+",   "label": "65 and over"},
]

HEALTH_CONDITIONS = [
    {"id": "hypertension",    "label": "Hypertension",     "emoji": "❤️"},
    {"id": "anxiety",         "label": "Anxiety",          "emoji": "🌀"},
    {"id": "depression",      "label": "Depression",       "emoji": "🌧️"},
    {"id": "pcos",            "label": "PCOS",             "emoji": "🌸"},
    {"id": "adhd",            "label": "ADHD",             "emoji": "⚡"},
    {"id": "chronic_pain",    "label": "Chronic Pain",     "emoji": "💙"},
    {"id": "diabetes",        "label": "Diabetes",         "emoji": "🩺"},
    {"id": "thyroid",         "label": "Thyroid Issues",   "emoji": "🦋"},
    {"id": "ibs",             "label": "IBS / Gut Issues", "emoji": "🌿"},
    {"id": "insomnia",        "label": "Insomnia",         "emoji": "🌙"},
    {"id": "asthma",          "label": "Asthma",           "emoji": "💨"},
    {"id": "arthritis",       "label": "Arthritis",        "emoji": "🦴"},
    {"id": "migraine",        "label": "Migraines",        "emoji": "🔮"},
    {"id": "autoimmune",      "label": "Autoimmune",       "emoji": "🛡️"},
    {"id": "ptsd",            "label": "PTSD",             "emoji": "🕊️"},
    {"id": "ocd",             "label": "OCD",              "emoji": "🔄"},
    {"id": "eating_disorder", "label": "Eating Disorder",  "emoji": "🍃"},
    {"id": "bipolar",         "label": "Bipolar Disorder", "emoji": "🌊"},
]

CONDITION_TIPS = {
    "hypertension": [
        "Even 5 minutes of slow, deep breathing can meaningfully ease blood pressure spikes.",
        "Swapping salt for herbs and spices - gradually, not all at once - makes a real difference.",
        "A gentle 10-minute walk after meals supports healthy blood pressure naturally.",
        "Notice the link between stress and your pressure. Awareness itself is a form of management.",
    ],
    "anxiety": [
        "Box breathing (4 counts in, hold, out, hold) activates your nervous system's calm response.",
        "Writing worries down for 10 minutes can help your mind release its grip on them.",
        "When anxiety spikes, the 5-4-3-2-1 grounding technique can bring you back to now.",
        "Cold water on your wrists can activate the dive reflex and slow your heart rate quickly.",
    ],
    "depression": [
        "Even tiny moments of connection - a quick text, stepping outside - can shift the weather.",
        "Morning sunlight for 10 minutes supports serotonin production more than you might expect.",
        "Gentle movement, not intense exercise, is often more sustainable and still lifts mood.",
        "Depression often lies about tomorrow. What felt impossible yesterday may shift today.",
    ],
    "pcos": [
        "Anti-inflammatory eating - more leafy greens, less refined sugar - supports hormonal balance.",
        "Stress significantly affects PCOS symptoms; gentle practices like yoga help regulate cortisol.",
        "Tracking your cycle and symptoms helps you understand your personal patterns over time.",
        "Inositol (myo-inositol) is worth discussing with your doctor for insulin sensitivity.",
    ],
    "adhd": [
        "Breaking tasks into 10-minute chunks makes starting far less daunting.",
        "Body doubling - working alongside someone - is a genuinely effective ADHD strategy.",
        "Externalizing your working memory (sticky notes, voice memos) reduces cognitive load.",
        "Movement breaks aren't a distraction; they're often what makes focus possible.",
    ],
    "chronic_pain": [
        "Pacing - not pushing through or fully resting - is often what helps most with chronic pain.",
        "A pain journal can reveal patterns: triggers, fluctuations, and what actually helps.",
        "Gentle pool exercises or slow walking maintains function without flaring pain.",
        "Sleep quality and chronic pain are deeply linked - small sleep improvements ease pain.",
    ],
    "diabetes": [
        "Post-meal walks of even 10 minutes meaningfully support blood sugar regulation.",
        "Protein and fibre at meals slow glucose absorption and reduce spikes.",
        "Stress raises blood sugar through cortisol - stress management is diabetes management.",
        "Consistency matters more than perfection with food timing and sleep habits.",
    ],
    "thyroid": [
        "Selenium and zinc from brazil nuts and pumpkin seeds support thyroid function.",
        "Fatigue is a real thyroid symptom. Rest is part of managing the condition, not laziness.",
        "Tracking energy, temperature, and mood helps optimize your treatment over time.",
        "Gluten sensitivity is more common with thyroid conditions - worth discussing with your doctor.",
    ],
    "ibs": [
        "A low-FODMAP approach with a dietitian's guidance helps many people significantly.",
        "Stress and gut health are deeply connected - your gut literally has its own nervous system.",
        "Eating slowly and chewing thoroughly reduces the digestive burden considerably.",
        "Peppermint oil capsules have good evidence for reducing IBS-related cramping.",
    ],
    "insomnia": [
        "Keeping your wake time consistent - even on weekends - is the most powerful sleep habit.",
        "Using your bed only for sleep trains your brain to associate it with rest.",
        "If you're not asleep in 20 minutes, getting up until you feel sleepy is counterintuitive but effective.",
        "Blue light from screens suppresses melatonin; dimming screens an hour before bed helps.",
    ],
    "asthma": [
        "Pursed-lip breathing helps manage breathlessness and slow anxious breathing cycles.",
        "Identifying your personal triggers and planning around them reduces flares significantly.",
        "Nasal breathing (not mouth breathing) warms and filters air before it reaches your lungs.",
        "Keeping rescue medication accessible reduces anxiety, which itself can trigger symptoms.",
    ],
    "arthritis": [
        "Movement is medicine for arthritis - gentle range-of-motion exercises reduce stiffness.",
        "Anti-inflammatory foods like oily fish, turmeric, and berries can reduce joint inflammation.",
        "Heat before activity and ice after is a practical self-management pattern.",
        "Ergonomic tools and pacing during daily tasks matter as much as medical treatment.",
    ],
    "migraine": [
        "A migraine diary for 2-3 months reveals personal triggers more accurately than general lists.",
        "Consistent sleep timing is one of the strongest known migraine prevention factors.",
        "Magnesium deficiency is common in migraine - worth discussing with your doctor.",
        "Acting at the first sign of prodrome makes treatment far more effective.",
    ],
    "autoimmune": [
        "Reducing stress isn't optional with autoimmune conditions - it directly affects immune regulation.",
        "An elimination approach to food, with professional guidance, can identify dietary triggers.",
        "Sleep is when cellular repair happens - sleep quality is especially important.",
        "A multidisciplinary care team often leads to better integrated support.",
    ],
    "ptsd": [
        "Safety and predictability are foundational. Consistent routines create a sense of control.",
        "Grounding techniques work best when practiced before you need them, not only in crisis.",
        "Trauma-focused therapies like EMDR and CPT have strong evidence behind them.",
        "Healing from trauma isn't linear. It's okay to work at your own pace.",
    ],
    "ocd": [
        "ERP (Exposure and Response Prevention) therapy is the gold-standard treatment for OCD.",
        "Recognizing the difference between OCD thoughts and your actual values reduces their power.",
        "Reducing reassurance-seeking, even gradually, is an important part of recovery.",
        "OCD takes genuine effort to manage and that deserves real acknowledgment.",
    ],
    "eating_disorder": [
        "Recovery isn't linear - a difficult day doesn't erase real progress.",
        "Building a relationship with food that isn't about rules takes time and professional support.",
        "Nourishment is self-care, not a reward or a punishment.",
        "Having trusted support - a therapist, dietitian, or community - makes a real difference.",
    ],
    "bipolar": [
        "Sleep regularity is one of the most protective factors for mood stability.",
        "Daily mood, sleep, and energy tracking helps you notice patterns and warning signs early.",
        "Alcohol significantly destabilizes mood - minimizing it is worth the effort.",
        "A written wellness plan for early episode signs is an incredibly useful tool.",
    ],
}

HABITS = [
    {"id": "exercise",          "label": "Regular Exercise",  "emoji": "🏃"},
    {"id": "meditation",        "label": "Meditation",        "emoji": "🧘"},
    {"id": "journaling",        "label": "Journaling",        "emoji": "📓"},
    {"id": "sleep_routine",     "label": "Consistent Sleep",  "emoji": "😴"},
    {"id": "healthy_eating",    "label": "Mindful Eating",    "emoji": "🥗"},
    {"id": "hydration",         "label": "Staying Hydrated",  "emoji": "💧"},
    {"id": "screen_limits",     "label": "Screen Limits",     "emoji": "📵"},
    {"id": "social_connection", "label": "Social Connection", "emoji": "🤝"},
]

GOALS = [
    {"id": "reduce_stress",     "label": "Reduce Stress",        "emoji": "🌿"},
    {"id": "better_sleep",      "label": "Better Sleep",         "emoji": "🌙"},
    {"id": "manage_anxiety",    "label": "Manage Anxiety",       "emoji": "🌊"},
    {"id": "boost_mood",        "label": "Boost Mood",           "emoji": "☀️"},
    {"id": "build_resilience",  "label": "Build Resilience",     "emoji": "💪"},
    {"id": "improve_nutrition", "label": "Improve Nutrition",    "emoji": "🥦"},
    {"id": "mindfulness",       "label": "Practice Mindfulness", "emoji": "🧘"},
    {"id": "self_compassion",   "label": "Self-Compassion",      "emoji": "💕"},
]

# ---------------------------------------------------------------------------
# Affirmations + journal prompts
# ---------------------------------------------------------------------------
AFFIRMATIONS = [
    {"id": 1,  "text": "I am allowed to take up space and ask for what I need."},
    {"id": 2,  "text": "My feelings are valid, even when they're hard to hold."},
    {"id": 3,  "text": "I don't have to have it all figured out today."},
    {"id": 4,  "text": "I am worthy of rest, care, and kindness - especially from myself."},
    {"id": 5,  "text": "Difficult days are part of the journey, not the destination."},
    {"id": 6,  "text": "I have survived every hard moment so far. That matters."},
    {"id": 7,  "text": "My growth doesn't need to be visible to be real."},
    {"id": 8,  "text": "I can be both imperfect and enough at the same time."},
    {"id": 9,  "text": "It's okay to move slowly. Slow is still forward."},
    {"id": 10, "text": "I am more than my productivity, my appearance, my struggles."},
    {"id": 11, "text": "I am learning, and that's one of the bravest things a person can do."},
    {"id": 12, "text": "Today, just being here is enough."},
]

JOURNAL_PROMPTS = [
    "What's one small thing that felt good today, even briefly?",
    "What's weighing on you right now? Let it out without judgment.",
    "If you could give yourself one gift today, what would it be?",
    "What's something you've been avoiding thinking about?",
    "Who made you feel seen recently, and what did they do?",
    "What does your body need more of right now?",
    "If today were a weather pattern, what would it be - and why?",
    "What would you say to a close friend who felt exactly how you feel?",
    "What's one thing you'd like to release or let go of this week?",
    "What's been quietly bringing you comfort lately?",
]

# ---------------------------------------------------------------------------
# Guided breathing / grounding exercises
# ---------------------------------------------------------------------------
EXERCISES = [
    {
        "id": "box_breathing", "name": "Box Breathing", "emoji": "⬜",
        "tagline": "Calm under pressure",
        "description": "Used by athletes and first responders. Four equal counts create a steady, calming rhythm.",
        "duration_label": "~4 min", "cycles": 4,
        "steps": [
            {"label": "Breathe in",  "duration": 4, "hint": "Slowly through your nose"},
            {"label": "Hold",        "duration": 4, "hint": "Gently, no strain"},
            {"label": "Breathe out", "duration": 4, "hint": "Fully through your mouth"},
            {"label": "Hold",        "duration": 4, "hint": "Rest before the next breath"},
        ],
    },
    {
        "id": "pmr", "name": "Progressive Relaxation", "emoji": "💆",
        "tagline": "Release held tension",
        "description": "Systematically tense and release each muscle group. Most people carry tension they can't feel until they let it go.",
        "duration_label": "~8 min", "cycles": 1,
        "steps": [
            {"label": "Hands & Arms", "duration": 10, "hint": "Clench fists, tense arms. Hold."},
            {"label": "Release",      "duration": 15, "hint": "Let go completely. Notice the warmth."},
            {"label": "Shoulders",    "duration": 10, "hint": "Raise to your ears. Hold tight."},
            {"label": "Release",      "duration": 15, "hint": "Drop slowly. Feel tension drain away."},
            {"label": "Face",         "duration": 10, "hint": "Scrunch everything - eyes, jaw, nose."},
            {"label": "Release",      "duration": 15, "hint": "Soften. Let your face completely relax."},
            {"label": "Core",         "duration": 10, "hint": "Tighten stomach and back muscles."},
            {"label": "Release",      "duration": 15, "hint": "Breathe. Feel the ground beneath you."},
            {"label": "Legs & Feet",  "duration": 10, "hint": "Flex legs, curl toes tight."},
            {"label": "Full release", "duration": 20, "hint": "Let go everywhere. Your whole body relaxes."},
        ],
    },
    {
        "id": "breathing_478", "name": "4-7-8 Breathing", "emoji": "🌬️",
        "tagline": "Activate rest mode",
        "description": "The extended exhale activates the parasympathetic nervous system. Four cycles can lower heart rate noticeably.",
        "duration_label": "~4 min", "cycles": 4,
        "steps": [
            {"label": "Breathe in",  "duration": 4, "hint": "Quietly through your nose"},
            {"label": "Hold",        "duration": 7, "hint": "Completely still"},
            {"label": "Breathe out", "duration": 8, "hint": "Fully through your mouth - a soft whoosh"},
        ],
    },
    {
        "id": "physiological_sigh", "name": "Physiological Sigh", "emoji": "😮‍💨",
        "tagline": "Fastest stress relief",
        "description": "A double inhale followed by a long exhale - the fastest known way to reduce stress in real time.",
        "duration_label": "~2 min", "cycles": 5,
        "steps": [
            {"label": "First inhale",  "duration": 2, "hint": "Deep breath in through your nose"},
            {"label": "Top up",        "duration": 2, "hint": "A short second sniff - fill completely"},
            {"label": "Long exhale",   "duration": 6, "hint": "Slowly out through your mouth until empty"},
            {"label": "Natural pause", "duration": 3, "hint": "Rest naturally before the next sigh"},
        ],
    },
    {
        "id": "body_scan", "name": "Body Scan", "emoji": "🌿",
        "tagline": "Notice, don't fix",
        "description": "Move your attention slowly from head to toe, noticing sensations without trying to change them.",
        "duration_label": "~3 min", "cycles": 1,
        "steps": [
            {"label": "Head & face",   "duration": 20, "hint": "Soften your forehead, eyes and jaw."},
            {"label": "Neck & shoulders", "duration": 20, "hint": "Let your shoulders drop away from your ears."},
            {"label": "Arms & hands",  "duration": 20, "hint": "Notice warmth, weight, tingling - anything."},
            {"label": "Chest & belly", "duration": 25, "hint": "Feel the natural rise and fall of your breath."},
            {"label": "Hips & legs",   "duration": 25, "hint": "Feel the support of the chair or floor."},
            {"label": "Whole body",    "duration": 30, "hint": "Rest in the feeling of your body as a whole."},
        ],
    },
    {
        "id": "gratitude_pause", "name": "Gratitude Pause", "emoji": "🙏",
        "tagline": "Shift your focus",
        "description": "Three short prompts to bring to mind what is going right, however small.",
        "duration_label": "~2 min", "cycles": 1,
        "steps": [
            {"label": "Something small that helped today", "duration": 30, "hint": "A warm drink, a message, a moment of quiet."},
            {"label": "Someone you're glad exists", "duration": 30, "hint": "Picture their face. Let yourself feel it."},
            {"label": "Something about yourself you appreciate", "duration": 30, "hint": "Even one thing counts."},
            {"label": "Breathe it in", "duration": 15, "hint": "One slow breath, holding that warmth."},
        ],
    },
    {
        "id": "grounding_54321", "name": "5-4-3-2-1 Grounding", "emoji": "🌍",
        "tagline": "Anchor to the present",
        "description": "Use your five senses to interrupt anxious thinking and bring yourself fully back to now.",
        "duration_label": "~5 min", "cycles": 1,
        "steps": [
            {"label": "5 things you see",   "duration": 30, "hint": "Look around. Name 5 things - notice colour, shape, light."},
            {"label": "4 things you touch", "duration": 25, "hint": "Feel 4 surfaces. Fabric, skin, chair, air."},
            {"label": "3 things you hear",  "duration": 20, "hint": "Listen carefully. Near sounds and far ones."},
            {"label": "2 things you smell", "duration": 20, "hint": "Notice 2 scents, however faint."},
            {"label": "1 thing you taste",  "duration": 20, "hint": "What's the faint taste in your mouth right now?"},
        ],
    },
]

# ---------------------------------------------------------------------------
# Chat-side recommendation cards + scoring function
# ---------------------------------------------------------------------------
RECOMMENDATIONS = [
    {"id": "box_breathing", "title": "Box Breathing", "emoji": "⬜", "body": "A 4-minute breathing pattern used by first responders. Four counts in, hold, out, hold - it creates calm quickly.", "goals": ["reduce_stress", "manage_anxiety"], "moods": ["stressed", "anxious"], "conds": ["anxiety", "ptsd", "hypertension"]},
    {"id": "gratitude_3", "title": "3 Good Things", "emoji": "📓", "body": "Write down 3 things that went well today, however small. Research shows this shifts the brain's negativity bias over time.", "goals": ["boost_mood", "self_compassion"], "moods": ["sad", "tired", "hopeful"], "conds": ["depression"]},
    {"id": "cold_water", "title": "Cold Water Reset", "emoji": "💧", "body": "Splash cold water on your face. It activates the dive reflex and slows your heart rate within seconds.", "goals": ["manage_anxiety", "reduce_stress"], "moods": ["anxious", "stressed"], "conds": ["anxiety", "hypertension"]},
    {"id": "sunshine_break", "title": "10 Min of Sunlight", "emoji": "☀️", "body": "Step outside for just 10 minutes. Morning light regulates cortisol and serotonin more powerfully than most things.", "goals": ["boost_mood", "better_sleep"], "moods": ["sad", "tired", "hopeful"], "conds": ["depression", "insomnia"]},
    {"id": "body_scan", "title": "Body Scan", "emoji": "🌿", "body": "A slow scan from head to toe that releases tension you didn't know you were holding.", "goals": ["mindfulness", "reduce_stress"], "moods": ["tired", "stressed", "anxious"], "conds": ["chronic_pain", "insomnia"]},
    {"id": "nature_sounds", "title": "Nature Soundscape", "emoji": "🌲", "body": "Even recordings of rain or birdsong measurably reduce stress hormones within a few minutes.", "goals": ["reduce_stress", "mindfulness"], "moods": ["stressed", "anxious", "sad"], "conds": ["anxiety", "insomnia"]},
    {"id": "mindful_drink", "title": "Mindful Warm Drink", "emoji": "🍵", "body": "Make something warm and drink it without your phone. The ritual itself is a micro-meditation.", "goals": ["mindfulness", "self_compassion"], "moods": ["calm", "tired", "sad"], "conds": []},
    {"id": "gentle_walk", "title": "Gentle Movement", "emoji": "🚶", "body": "Five minutes of walking or light stretching shifts your physiology and mental state more than you'd expect.", "goals": ["boost_mood", "build_resilience"], "moods": ["tired", "sad", "stressed"], "conds": ["depression", "adhd", "chronic_pain"]},
    {"id": "reach_out", "title": "Reach Out", "emoji": "💬", "body": "Send a short message to someone you trust. Connection is one of the strongest protective factors for wellbeing.", "goals": ["build_resilience", "self_compassion"], "moods": ["sad", "anxious", "hopeful"], "conds": ["depression"]},
    {"id": "wind_down", "title": "Wind-Down Ritual", "emoji": "🌙", "body": "Dim your lights and put screens away 30 minutes before bed. Your body needs this signal to begin releasing melatonin.", "goals": ["better_sleep"], "moods": ["tired", "stressed", "anxious"], "conds": ["insomnia", "bipolar"]},
    {"id": "sigh", "title": "Physiological Sigh", "emoji": "😮‍💨", "body": "Double inhale through your nose, then a long slow exhale. Repeat 3 times for the fastest nervous system reset known.", "goals": ["reduce_stress", "manage_anxiety"], "moods": ["stressed", "anxious"], "conds": ["anxiety", "ptsd"]},
    {"id": "affirm", "title": "Say Something Kind", "emoji": "💕", "body": "Tell yourself one genuinely kind thing, like you would to a close friend. It feels awkward - do it anyway.", "goals": ["self_compassion", "boost_mood"], "moods": ["sad", "tired", "hopeful"], "conds": ["depression", "eating_disorder"]},
]


def get_personalized_recs(profile, detected_mood, last_rec_id=None):
    """Score each recommendation against the user's profile + current mood
    and return the top 4, matching the web app's scoring logic exactly."""
    cond_ids = profile.get("conditions", []) if profile else []
    goal_ids = profile.get("goals", []) if profile else []

    scored = []
    for rec in RECOMMENDATIONS:
        if rec["id"] == last_rec_id:
            continue
        score = 0
        if detected_mood in rec["moods"]:
            score += 3
        for g in goal_ids:
            if g in rec["goals"]:
                score += 2
        for c in cond_ids:
            if c in rec["conds"]:
                score += 1
        scored.append({**rec, "score": score})

    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:4]


# ---------------------------------------------------------------------------
# Support resources by country (trimmed set, DEFAULT covers everyone else)
# ---------------------------------------------------------------------------
SUPPORT_RESOURCES = {
    "US": {
        "crisis": [
            {"name": "988 Suicide & Crisis Lifeline", "contact": "Call or text 988", "url": "https://988lifeline.org", "note": "24/7 free support"},
            {"name": "Crisis Text Line", "contact": "Text HOME to 741741", "url": "https://www.crisistextline.org", "note": "Free 24/7 text support"},
        ],
        "mental": [
            {"name": "NAMI Helpline", "contact": "1-800-950-6264", "url": "https://www.nami.org", "note": "National Alliance on Mental Illness"},
        ],
        "physical": [
            {"name": "Health Resources & Services Administration", "contact": "", "url": "https://www.hrsa.gov", "note": "Find affordable health care near you"},
        ],
    },
    "GB": {
        "crisis": [
            {"name": "Samaritans", "contact": "116 123", "url": "https://www.samaritans.org", "note": "Free, 24/7, anonymous support"},
        ],
        "mental": [
            {"name": "Mind", "contact": "0300 123 3393", "url": "https://www.mind.org.uk", "note": "Mental health information & support"},
        ],
        "physical": [
            {"name": "NHS 111", "contact": "111", "url": "https://111.nhs.uk", "note": "Non-emergency medical advice 24/7"},
        ],
    },
    "IN": {
        "crisis": [
            {"name": "iCall", "contact": "9152987821", "url": "https://icallhelpline.org", "note": "Psychosocial support helpline"},
            {"name": "Vandrevala Foundation", "contact": "1860-2662-345", "url": "https://www.vandrevalafoundation.com", "note": "24/7 mental health helpline"},
        ],
        "mental": [
            {"name": "NIMHANS", "contact": "", "url": "https://nimhans.ac.in", "note": "National Institute of Mental Health"},
        ],
        "physical": [
            {"name": "National Health Portal", "contact": "1800-180-1104", "url": "https://www.nhp.gov.in", "note": "Health information and resources"},
        ],
    },
    "DEFAULT": {
        "crisis": [
            {"name": "Befrienders Worldwide", "contact": "", "url": "https://www.befrienders.org", "note": "Global emotional support network"},
            {"name": "IASP Crisis Centres Directory", "contact": "", "url": "https://www.iasp.info/resources/Crisis_Centres/", "note": "Find crisis centres worldwide"},
        ],
        "mental": [
            {"name": "World Health Organization - Mental Health", "contact": "", "url": "https://www.who.int/health-topics/mental-health", "note": "Global mental health resources"},
        ],
        "physical": [
            {"name": "World Health Organization", "contact": "", "url": "https://www.who.int", "note": "Global health information"},
        ],
    },
}
