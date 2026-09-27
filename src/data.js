// ─── Design Tokens ───────────────────────────────────────────
// `C` is mutated in place (see applyTheme below) rather than reassigned, so
// every component that imported it keeps working from the same object and
// picks up the new palette the next time it renders - mirrors how the
// desktop app's data.py swaps its shared COLORS dict for a theme change.
export const LIGHT_COLORS = {
  bg: '#FAF8F4',
  surface: '#FFFFFF',
  primary: '#8B5E3C',
  primaryLight: '#C8956C',
  primaryPale: '#F5EDE5',
  sage: '#7D9B76',
  sagePale: '#EFF5EE',
  sageLight: '#B5CDB2',
  text: '#3D2C1E',
  textMuted: '#8A7168',
  border: '#E8DDD5',
  shadow: '0 4px 20px rgba(139,94,60,0.09)',
  shadowLg: '0 8px 40px rgba(139,94,60,0.14)',
};

export const DARK_COLORS = {
  bg: '#1B1714',
  surface: '#26211D',
  primary: '#D4A373',
  primaryLight: '#E6BC8F',
  primaryPale: '#3A2F27',
  sage: '#9DBB96',
  sagePale: '#26332A',
  sageLight: '#4E6B4A',
  text: '#F1E9E2',
  textMuted: '#A99B90',
  border: '#3B332D',
  shadow: '0 4px 20px rgba(0,0,0,0.35)',
  shadowLg: '0 8px 40px rgba(0,0,0,0.5)',
};

export const C = { ...LIGHT_COLORS };

export function applyTheme(name) {
  Object.assign(C, name === 'dark' ? DARK_COLORS : LIGHT_COLORS);
}

/** '#8B5E3C' -> '139, 94, 60', for CSS rgba(var(--x), alpha) custom properties. */
export function hexToRgb(hex) {
  const m = hex.replace('#', '').match(/.{1,2}/g) || [];
  return m.map(h => parseInt(h, 16)).join(', ');
}

// The desktop app uses one plain system sans-serif everywhere (see
// desktop_app/styles.py) - no serif display face, no loaded web fonts. `serif`
// is kept only so existing call sites don't need to change; it's now an alias
// of `sans` so the web app matches that same, single typeface.
const SYSTEM_SANS = "'Helvetica Neue', 'Segoe UI', Arial, sans-serif";
export const FONT = {
  serif: SYSTEM_SANS,
  sans: SYSTEM_SANS,
};

// ─── Mood System ─────────────────────────────────────────────
export const MOODS = {
  happy:    { emoji: '😊', label: 'Happy',    color: '#E97D3F', bg: '#FEF3E6' },
  calm:     { emoji: '😌', label: 'Calm',     color: '#74C69D', bg: '#EAF7F0' },
  sad:      { emoji: '😢', label: 'Sad',      color: '#748CAB', bg: '#EBF0F5' },
  anxious:  { emoji: '😰', label: 'Anxious',  color: '#B5838D', bg: '#F5EAEC' },
  stressed: { emoji: '😤', label: 'Stressed', color: '#E07A5F', bg: '#FCEEE9' },
  grateful: { emoji: '🙏', label: 'Grateful', color: '#D4A017', bg: '#FDF6E3' },
  tired:    { emoji: '😴', label: 'Tired',    color: '#A8DADC', bg: '#EAF6F7' },
  hopeful:  { emoji: '🌱', label: 'Hopeful',  color: '#52B788', bg: '#EBF7F2' },
};

const MOOD_WORDS = {
  happy:    ['happy','joyful','excited','great','wonderful','fantastic','amazing','love','laugh','smile','cheerful','delighted','thrilled','elated','ecstatic','awesome','brilliant','enjoy','glad','pleased'],
  calm:     ['calm','peaceful','relaxed','serene','tranquil','quiet','centered','balanced','zen','content','ease','fine','alright','steady','grounded','composed','settled'],
  sad:      ['sad','unhappy','down','depressed','miserable','cry','crying','tears','lonely','empty','hopeless','gloomy','heartbroken','hurt','grief','lost','alone','terrible','awful','devastated'],
  anxious:  ['anxious','anxiety','worry','worried','nervous','scared','fear','afraid','panic','tense','uneasy','dread','apprehensive','restless','overthinking','on edge','racing thoughts'],
  stressed: ['stressed','stress','overwhelmed','pressure','burnout','struggling','overloaded','frazzled','swamped','deadline','behind','chaotic','chaos','too much'],
  grateful: ['grateful','thankful','appreciate','blessed','lucky','fortunate','gratitude','thank you','thanks','appreciative','abundance'],
  tired:    ['tired','exhausted','fatigue','sleepy','drained','worn out','no energy','weary','sluggish','lethargic','depleted','heavy','low energy'],
  hopeful:  ['hopeful','hope','optimistic','looking forward','positive','better','improve','progress','trying','getting there','working on','can do'],
};

export function detectMood(text) {
  const lower = text.toLowerCase();
  const scores = {};
  for (const [mood, words] of Object.entries(MOOD_WORDS)) {
    scores[mood] = words.reduce((n, w) => n + (lower.includes(w) ? 1 : 0), 0);
  }
  const total = Object.values(scores).reduce((a, b) => a + b, 0);
  if (total === 0) return { mood: 'calm', confidence: 0.3, ...MOODS.calm };
  const [topMood] = Object.entries(scores).sort((a, b) => b[1] - a[1])[0];
  return { mood: topMood, confidence: Math.min(scores[topMood] / Math.max(total, 3), 1), ...MOODS[topMood] };
}

export const MOOD_FALLBACKS = {
  happy:    "Something brightened your day — I can feel it in your words. What's been sparking that joy?",
  calm:     "There's a quiet steadiness in what you've shared. That kind of peace is worth protecting.",
  sad:      "Whatever you're carrying right now, you don't have to carry it alone. I'm right here with you.",
  anxious:  "Your mind is working overtime and that's genuinely exhausting. Let's slow things down together.",
  stressed: "You're carrying a heavy load right now. It makes complete sense to feel stretched thin.",
  grateful: "Gratitude has such a warm energy to it. It sounds like something good found its way into your day.",
  tired:    "Your body and mind are asking for rest — that's a real signal worth listening to.",
  hopeful:  "There's something quietly brave about holding onto hope. That reaching-forward in you matters.",
};

// ─── Crisis detection ─────────────────────────────────────────
// Deliberately simple and over-cautious: a false alarm just shows a support
// banner, a miss could matter a lot more.
export const CRISIS_PHRASES = [
  'kill myself', 'suicide', 'suicidal', 'end my life', 'want to die', 'wanna die',
  'self harm', 'self-harm', 'hurt myself', "don't want to live", 'dont want to live',
  'no reason to live', 'better off dead', 'take my own life',
  // Hindi / Hinglish
  'marna chahta', 'marna chahti', 'mar jana chahta', 'mar jana chahti', 'jeene ka mann nahi',
  'jeene ka man nahi', 'khudkushi', 'aatmahatya', 'atmahatya', 'khud ko khatam',
  'आत्महत्या', 'मरना चाहता', 'मरना चाहती', 'जीने का मन नहीं', 'खुद को खत्म',
];

export function detectCrisis(text) {
  const lower = text.toLowerCase();
  return CRISIS_PHRASES.some(phrase => lower.includes(phrase));
}

export const CRISIS_FALLBACK =
  "I'm really glad you told me. What you're feeling matters, and you don't have to hold it alone — " +
  'please reach out to someone right now, like a crisis line or a person you trust. ' +
  'If you might act on these thoughts, call your local emergency number.';

// ─── Onboarding Data ─────────────────────────────────────────
export const COUNTRIES = [
  { code: 'US', name: 'United States',   flag: '🇺🇸' },
  { code: 'GB', name: 'United Kingdom',  flag: '🇬🇧' },
  { code: 'CA', name: 'Canada',          flag: '🇨🇦' },
  { code: 'AU', name: 'Australia',       flag: '🇦🇺' },
  { code: 'IN', name: 'India',           flag: '🇮🇳' },
  { code: 'DE', name: 'Germany',         flag: '🇩🇪' },
  { code: 'FR', name: 'France',          flag: '🇫🇷' },
  { code: 'ES', name: 'Spain',           flag: '🇪🇸' },
  { code: 'IT', name: 'Italy',           flag: '🇮🇹' },
  { code: 'JP', name: 'Japan',           flag: '🇯🇵' },
  { code: 'BR', name: 'Brazil',          flag: '🇧🇷' },
  { code: 'MX', name: 'Mexico',          flag: '🇲🇽' },
  { code: 'NG', name: 'Nigeria',         flag: '🇳🇬' },
  { code: 'ZA', name: 'South Africa',    flag: '🇿🇦' },
  { code: 'NZ', name: 'New Zealand',     flag: '🇳🇿' },
  { code: 'SG', name: 'Singapore',       flag: '🇸🇬' },
  { code: 'AE', name: 'UAE',             flag: '🇦🇪' },
  { code: 'PK', name: 'Pakistan',        flag: '🇵🇰' },
  { code: 'PH', name: 'Philippines',     flag: '🇵🇭' },
  { code: 'KE', name: 'Kenya',           flag: '🇰🇪' },
];

export const LANGUAGES = [
  { code: 'en', name: 'English',     locale: 'en-US' },
  { code: 'es', name: 'Español',     locale: 'es-ES' },
  { code: 'fr', name: 'Français',    locale: 'fr-FR' },
  { code: 'de', name: 'Deutsch',     locale: 'de-DE' },
  { code: 'it', name: 'Italiano',    locale: 'it-IT' },
  { code: 'pt', name: 'Português',   locale: 'pt-BR' },
  { code: 'hi', name: 'हिंदी',       locale: 'hi-IN' },
  { code: 'ja', name: '日本語',       locale: 'ja-JP' },
  { code: 'ar', name: 'العربية',     locale: 'ar-SA' },
  { code: 'zh', name: '中文',         locale: 'zh-CN' },
  { code: 'sw', name: 'Kiswahili',   locale: 'sw-KE' },
  { code: 'ur', name: 'اردو',        locale: 'ur-PK' },
];

// The language the companion can reply in, chosen from the Chat page — separate
// from the language picked at sign-up. "auto" follows whatever language you
// write in; "hinglish" is Hindi typed in English letters.
const LANGUAGE_ENGLISH_NAMES = {
  en: 'English', es: 'Spanish', fr: 'French', de: 'German', it: 'Italian',
  pt: 'Portuguese', hi: 'Hindi', ja: 'Japanese', ar: 'Arabic', zh: 'Chinese',
};
export const CHAT_LANGUAGES = [
  { code: 'auto', name: 'Match what I write' },
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'हिंदी (Hindi)' },
  { code: 'hinglish', name: 'Hinglish (Hindi in English letters)' },
  ...LANGUAGES.filter(l => l.code !== 'en' && l.code !== 'hi').map(l => ({ code: l.code, name: l.name })),
];

/** What replies use until the user picks something on the Chat page. */
export function defaultChatLanguage(profileLanguage) {
  return profileLanguage in LANGUAGE_ENGLISH_NAMES && profileLanguage !== 'en' ? profileLanguage : 'auto';
}

/** The line added to the model's instructions for a reply language ('' if unknown). */
export function languageInstruction(code) {
  if (code === 'auto') {
    return 'Reply in the same language the person writes in. They may mix languages or write Hindi in ' +
           'English letters — if so, reply the same way.';
  }
  if (code === 'hinglish') {
    return 'IMPORTANT: Reply in Hinglish — Hindi written in English (Roman) letters, the way people text, ' +
           'e.g. "Mujhe samajh aa raha hai ki tum kaisa feel kar rahe ho." Never use Devanagari script.';
  }
  if (code === 'en') return 'IMPORTANT: Reply in English, even if the person writes in another language.';
  if (code in LANGUAGE_ENGLISH_NAMES) {
    return `IMPORTANT: Respond entirely in ${LANGUAGE_ENGLISH_NAMES[code]}, even if the person writes in another language.`;
  }
  return '';
}

export const AGE_GROUPS = [
  { id: '18-24', label: '18 – 24' },
  { id: '25-34', label: '25 – 34' },
  { id: '35-44', label: '35 – 44' },
  { id: '45-54', label: '45 – 54' },
  { id: '55-64', label: '55 – 64' },
  { id: '65+',   label: '65 and over' },
];

export const HEALTH_CONDITIONS = [
  { id: 'hypertension',    label: 'Hypertension',      emoji: '❤️'  },
  { id: 'anxiety',         label: 'Anxiety',           emoji: '🌀'  },
  { id: 'depression',      label: 'Depression',        emoji: '🌧️' },
  { id: 'pcos',            label: 'PCOS',              emoji: '🌸'  },
  { id: 'adhd',            label: 'ADHD',              emoji: '⚡'  },
  { id: 'chronic_pain',    label: 'Chronic Pain',      emoji: '💙'  },
  { id: 'diabetes',        label: 'Diabetes',          emoji: '🩺'  },
  { id: 'thyroid',         label: 'Thyroid Issues',    emoji: '🦋'  },
  { id: 'ibs',             label: 'IBS / Gut Issues',  emoji: '🌿'  },
  { id: 'insomnia',        label: 'Insomnia',          emoji: '🌙'  },
  { id: 'asthma',          label: 'Asthma',            emoji: '💨'  },
  { id: 'arthritis',       label: 'Arthritis',         emoji: '🦴'  },
  { id: 'migraine',        label: 'Migraines',         emoji: '🔮'  },
  { id: 'autoimmune',      label: 'Autoimmune',        emoji: '🛡️' },
  { id: 'ptsd',            label: 'PTSD',              emoji: '🕊️' },
  { id: 'ocd',             label: 'OCD',               emoji: '🔄'  },
  { id: 'eating_disorder', label: 'Eating Disorder',   emoji: '🍃'  },
  { id: 'bipolar',         label: 'Bipolar Disorder',  emoji: '🌊'  },
];

export const CONDITION_TIPS = {
  hypertension: [
    'Even 5 minutes of slow, deep breathing can meaningfully ease blood pressure spikes.',
    'Swapping salt for herbs and spices — gradually, not all at once — makes a real difference.',
    'A gentle 10-minute walk after meals supports healthy blood pressure naturally.',
    'Notice the link between stress and your pressure. Awareness itself is a form of management.',
  ],
  anxiety: [
    'Box breathing (4 counts in, hold, out, hold) activates your nervous system\'s calm response.',
    'Writing worries down for 10 minutes can help your mind release its grip on them.',
    'When anxiety spikes, the 5-4-3-2-1 grounding technique can bring you back to now.',
    'Cold water on your wrists can activate the dive reflex and slow your heart rate quickly.',
  ],
  depression: [
    'Even tiny moments of connection — a quick text, stepping outside — can shift the weather.',
    'Morning sunlight for 10 minutes supports serotonin production more than you might expect.',
    'Gentle movement, not intense exercise, is often more sustainable and still lifts mood.',
    'Depression often lies about tomorrow. What felt impossible yesterday may shift today.',
  ],
  pcos: [
    'Anti-inflammatory eating — more leafy greens, less refined sugar — supports hormonal balance.',
    'Stress significantly affects PCOS symptoms; gentle practices like yoga help regulate cortisol.',
    'Tracking your cycle and symptoms helps you understand your personal patterns over time.',
    'Inositol (myo-inositol) is worth discussing with your doctor for insulin sensitivity.',
  ],
  adhd: [
    'Breaking tasks into 10-minute chunks makes starting far less daunting.',
    'Body doubling — working alongside someone — is a genuinely effective ADHD strategy.',
    'Externalizing your working memory (sticky notes, voice memos) reduces cognitive load.',
    'Movement breaks aren\'t a distraction; they\'re often what makes focus possible.',
  ],
  chronic_pain: [
    'Pacing — not pushing through or fully resting — is often what helps most with chronic pain.',
    'A pain journal can reveal patterns: triggers, fluctuations, and what actually helps.',
    'Gentle pool exercises or slow walking maintains function without flaring pain.',
    'Sleep quality and chronic pain are deeply linked — small sleep improvements ease pain.',
  ],
  diabetes: [
    'Post-meal walks of even 10 minutes meaningfully support blood sugar regulation.',
    'Protein and fibre at meals slow glucose absorption and reduce spikes.',
    'Stress raises blood sugar through cortisol — stress management is diabetes management.',
    'Consistency matters more than perfection with food timing and sleep habits.',
  ],
  thyroid: [
    'Selenium and zinc from brazil nuts and pumpkin seeds support thyroid function.',
    'Fatigue is a real thyroid symptom. Rest is part of managing the condition, not laziness.',
    'Tracking energy, temperature, and mood helps optimize your treatment over time.',
    'Gluten sensitivity is more common with thyroid conditions — worth discussing with your doctor.',
  ],
  ibs: [
    'A low-FODMAP approach with a dietitian\'s guidance helps many people significantly.',
    'Stress and gut health are deeply connected — your gut literally has its own nervous system.',
    'Eating slowly and chewing thoroughly reduces the digestive burden considerably.',
    'Peppermint oil capsules have good evidence for reducing IBS-related cramping.',
  ],
  insomnia: [
    'Keeping your wake time consistent — even on weekends — is the most powerful sleep habit.',
    'Using your bed only for sleep trains your brain to associate it with rest.',
    'If you\'re not asleep in 20 minutes, getting up until you feel sleepy is counterintuitive but effective.',
    'Blue light from screens suppresses melatonin; dimming screens an hour before bed helps.',
  ],
  asthma: [
    'Pursed-lip breathing helps manage breathlessness and slow anxious breathing cycles.',
    'Identifying your personal triggers and planning around them reduces flares significantly.',
    'Nasal breathing (not mouth breathing) warms and filters air before it reaches your lungs.',
    'Keeping rescue medication accessible reduces anxiety, which itself can trigger symptoms.',
  ],
  arthritis: [
    'Movement is medicine for arthritis — gentle range-of-motion exercises reduce stiffness.',
    'Anti-inflammatory foods like oily fish, turmeric, and berries can reduce joint inflammation.',
    'Heat before activity and ice after is a practical self-management pattern.',
    'Ergonomic tools and pacing during daily tasks matter as much as medical treatment.',
  ],
  migraine: [
    'A migraine diary for 2–3 months reveals personal triggers more accurately than general lists.',
    'Consistent sleep timing is one of the strongest known migraine prevention factors.',
    'Magnesium deficiency is common in migraine — worth discussing with your doctor.',
    'Acting at the first sign of prodrome makes treatment far more effective.',
  ],
  autoimmune: [
    'Reducing stress isn\'t optional with autoimmune conditions — it directly affects immune regulation.',
    'An elimination approach to food, with professional guidance, can identify dietary triggers.',
    'Sleep is when cellular repair happens — sleep quality is especially important.',
    'A multidisciplinary care team often leads to better integrated support.',
  ],
  ptsd: [
    'Safety and predictability are foundational. Consistent routines create a sense of control.',
    'Grounding techniques work best when practiced before you need them, not only in crisis.',
    'Trauma-focused therapies like EMDR and CPT have strong evidence behind them.',
    'Healing from trauma isn\'t linear. It\'s okay to work at your own pace.',
  ],
  ocd: [
    'ERP (Exposure and Response Prevention) therapy is the gold-standard treatment for OCD.',
    'Recognizing the difference between OCD thoughts and your actual values reduces their power.',
    'Reducing reassurance-seeking, even gradually, is an important part of recovery.',
    'OCD takes genuine effort to manage and that deserves real acknowledgment.',
  ],
  eating_disorder: [
    'Recovery isn\'t linear — a difficult day doesn\'t erase real progress.',
    'Building a relationship with food that isn\'t about rules takes time and professional support.',
    'Nourishment is self-care, not a reward or a punishment.',
    'Having trusted support — a therapist, dietitian, or community — makes a real difference.',
  ],
  bipolar: [
    'Sleep regularity is one of the most protective factors for mood stability.',
    'Daily mood, sleep, and energy tracking helps you notice patterns and warning signs early.',
    'Alcohol significantly destabilizes mood — minimizing it is worth the effort.',
    'A written wellness plan for early episode signs is an incredibly useful tool.',
  ],
};

export const HABITS = [
  { id: 'exercise',         label: 'Regular Exercise',    emoji: '🏃' },
  { id: 'meditation',       label: 'Meditation',          emoji: '🧘' },
  { id: 'journaling',       label: 'Journaling',          emoji: '📓' },
  { id: 'sleep_routine',    label: 'Consistent Sleep',    emoji: '😴' },
  { id: 'healthy_eating',   label: 'Mindful Eating',      emoji: '🥗' },
  { id: 'hydration',        label: 'Staying Hydrated',    emoji: '💧' },
  { id: 'screen_limits',    label: 'Screen Limits',       emoji: '📵' },
  { id: 'social_connection',label: 'Social Connection',   emoji: '🤝' },
];

export const GOALS = [
  { id: 'reduce_stress',    label: 'Reduce Stress',        emoji: '🌿' },
  { id: 'better_sleep',     label: 'Better Sleep',         emoji: '🌙' },
  { id: 'manage_anxiety',   label: 'Manage Anxiety',       emoji: '🌊' },
  { id: 'boost_mood',       label: 'Boost Mood',           emoji: '☀️' },
  { id: 'build_resilience', label: 'Build Resilience',     emoji: '💪' },
  { id: 'improve_nutrition',label: 'Improve Nutrition',    emoji: '🥦' },
  { id: 'mindfulness',      label: 'Practice Mindfulness', emoji: '🧘' },
  { id: 'self_compassion',  label: 'Self-Compassion',      emoji: '💕' },
];

// ─── Affirmations ─────────────────────────────────────────────
export const AFFIRMATIONS = [
  { id: 1, text: 'I am allowed to take up space and ask for what I need.' },
  { id: 2, text: 'My feelings are valid, even when they\'re hard to hold.' },
  { id: 3, text: 'I don\'t have to have it all figured out today.' },
  { id: 4, text: 'I am worthy of rest, care, and kindness — especially from myself.' },
  { id: 5, text: 'Difficult days are part of the journey, not the destination.' },
  { id: 6, text: 'I have survived every hard moment so far. That matters.' },
  { id: 7, text: 'My growth doesn\'t need to be visible to be real.' },
  { id: 8, text: 'I can be both imperfect and enough at the same time.' },
  { id: 9, text: 'It\'s okay to move slowly. Slow is still forward.' },
  { id: 10, text: 'I am more than my productivity, my appearance, my struggles.' },
  { id: 11, text: 'I am learning, and that\'s one of the bravest things a person can do.' },
  { id: 12, text: 'Today, just being here is enough.' },
];

// ─── Journal Prompts ──────────────────────────────────────────
export const JOURNAL_PROMPTS = [
  "What's one small thing that felt good today, even briefly?",
  "What's weighing on you right now? Let it out without judgment.",
  "If you could give yourself one gift today, what would it be?",
  "What's something you've been avoiding thinking about?",
  "Who made you feel seen recently, and what did they do?",
  "What does your body need more of right now?",
  "If today were a weather pattern, what would it be — and why?",
  "What would you say to a close friend who felt exactly how you feel?",
  "What's one thing you'd like to release or let go of this week?",
  "What's been quietly bringing you comfort lately?",
];

// ─── Exercises ────────────────────────────────────────────────
export const EXERCISES = [
  {
    id: 'box_breathing',
    name: 'Box Breathing',
    emoji: '⬜',
    tagline: 'Calm under pressure',
    description: 'Used by athletes and first responders. Four equal counts create a steady, calming rhythm.',
    durationLabel: '~4 min',
    cycles: 4,
    steps: [
      { label: 'Breathe in',  duration: 4, hint: 'Slowly through your nose' },
      { label: 'Hold',        duration: 4, hint: 'Gently, no strain' },
      { label: 'Breathe out', duration: 4, hint: 'Fully through your mouth' },
      { label: 'Hold',        duration: 4, hint: 'Rest before the next breath' },
    ],
  },
  {
    id: 'pmr',
    name: 'Progressive Relaxation',
    emoji: '💆',
    tagline: 'Release held tension',
    description: 'Systematically tense and release each muscle group. Most people carry tension they can\'t feel until they let it go.',
    durationLabel: '~8 min',
    cycles: 1,
    steps: [
      { label: 'Hands & Arms',  duration: 10, hint: 'Clench fists, tense arms. Hold.' },
      { label: 'Release',       duration: 15, hint: 'Let go completely. Notice the warmth.' },
      { label: 'Shoulders',     duration: 10, hint: 'Raise to your ears. Hold tight.' },
      { label: 'Release',       duration: 15, hint: 'Drop slowly. Feel tension drain away.' },
      { label: 'Face',          duration: 10, hint: 'Scrunch everything — eyes, jaw, nose.' },
      { label: 'Release',       duration: 15, hint: 'Soften. Let your face completely relax.' },
      { label: 'Core',          duration: 10, hint: 'Tighten stomach and back muscles.' },
      { label: 'Release',       duration: 15, hint: 'Breathe. Feel the ground beneath you.' },
      { label: 'Legs & Feet',   duration: 10, hint: 'Flex legs, curl toes tight.' },
      { label: 'Full release',  duration: 20, hint: 'Let go everywhere. Your whole body relaxes.' },
    ],
  },
  {
    id: 'breathing_478',
    name: '4-7-8 Breathing',
    emoji: '🌬️',
    tagline: 'Activate rest mode',
    description: 'The extended exhale activates the parasympathetic nervous system. Four cycles can lower heart rate noticeably.',
    durationLabel: '~4 min',
    cycles: 4,
    steps: [
      { label: 'Breathe in',  duration: 4, hint: 'Quietly through your nose' },
      { label: 'Hold',        duration: 7, hint: 'Completely still' },
      { label: 'Breathe out', duration: 8, hint: 'Fully through your mouth — a soft whoosh' },
    ],
  },
  {
    id: 'physiological_sigh',
    name: 'Physiological Sigh',
    emoji: '😮‍💨',
    tagline: 'Fastest stress relief',
    description: 'A double inhale followed by a long exhale — the fastest known way to reduce stress in real time.',
    durationLabel: '~2 min',
    cycles: 5,
    steps: [
      { label: 'First inhale',   duration: 2, hint: 'Deep breath in through your nose' },
      { label: 'Top up',         duration: 2, hint: 'A short second sniff — fill completely' },
      { label: 'Long exhale',    duration: 6, hint: 'Slowly out through your mouth until empty' },
      { label: 'Natural pause',  duration: 3, hint: 'Rest naturally before the next sigh' },
    ],
  },
  {
    id: 'grounding_54321',
    name: '5-4-3-2-1 Grounding',
    emoji: '🌍',
    tagline: 'Anchor to the present',
    description: 'Use your five senses to interrupt anxious thinking and bring yourself fully back to now.',
    durationLabel: '~5 min',
    cycles: 1,
    steps: [
      { label: '5 things you see',  duration: 30, hint: 'Look around. Name 5 things — notice colour, shape, light.' },
      { label: '4 things you touch',duration: 25, hint: 'Feel 4 surfaces. Fabric, skin, chair, air.' },
      { label: '3 things you hear', duration: 20, hint: 'Listen carefully. Near sounds and far ones.' },
      { label: '2 things you smell',duration: 20, hint: 'Notice 2 scents, however faint.' },
      { label: '1 thing you taste', duration: 20, hint: 'What\'s the faint taste in your mouth right now?' },
    ],
  },
];

// ─── Chat Recommendations ────────────────────────────────────
export const RECOMMENDATIONS = [
  { id: 'box_breathing',   title: 'Box Breathing',       emoji: '⬜', body: 'A 4-minute breathing pattern used by first responders. Four counts in, hold, out, hold — it creates calm quickly.',     goals: ['reduce_stress','manage_anxiety'], moods: ['stressed','anxious'],           conds: ['anxiety','ptsd','hypertension'] },
  { id: 'gratitude_3',     title: '3 Good Things',       emoji: '📓', body: 'Write down 3 things that went well today, however small. Research shows this shifts the brain\'s negativity bias over time.', goals: ['boost_mood','self_compassion'],   moods: ['sad','tired','hopeful'],         conds: ['depression'] },
  { id: 'cold_water',      title: 'Cold Water Reset',    emoji: '💧', body: 'Splash cold water on your face. It activates the dive reflex and slows your heart rate within seconds.',                    goals: ['manage_anxiety','reduce_stress'], moods: ['anxious','stressed'],            conds: ['anxiety','hypertension'] },
  { id: 'sunshine_break',  title: '10 Min of Sunlight',  emoji: '☀️', body: 'Step outside for just 10 minutes. Morning light regulates cortisol and serotonin more powerfully than most things.',        goals: ['boost_mood','better_sleep'],      moods: ['sad','tired','hopeful'],         conds: ['depression','insomnia'] },
  { id: 'body_scan',       title: 'Body Scan',           emoji: '🌿', body: 'A slow scan from head to toe that releases tension you didn\'t know you were holding.',                                       goals: ['mindfulness','reduce_stress'],    moods: ['tired','stressed','anxious'],    conds: ['chronic_pain','insomnia'] },
  { id: 'nature_sounds',   title: 'Nature Soundscape',   emoji: '🌲', body: 'Even recordings of rain or birdsong measurably reduce stress hormones within a few minutes.',                                goals: ['reduce_stress','mindfulness'],    moods: ['stressed','anxious','sad'],      conds: ['anxiety','insomnia'] },
  { id: 'mindful_drink',   title: 'Mindful Warm Drink',  emoji: '🍵', body: 'Make something warm and drink it without your phone. The ritual itself is a micro-meditation.',                              goals: ['mindfulness','self_compassion'],  moods: ['calm','tired','sad'],            conds: [] },
  { id: 'gentle_walk',     title: 'Gentle Movement',     emoji: '🚶', body: 'Five minutes of walking or light stretching shifts your physiology and mental state more than you\'d expect.',              goals: ['boost_mood','build_resilience'],  moods: ['tired','sad','stressed'],        conds: ['depression','adhd','chronic_pain'] },
  { id: 'reach_out',       title: 'Reach Out',           emoji: '💬', body: 'Send a short message to someone you trust. Connection is one of the strongest protective factors for wellbeing.',           goals: ['build_resilience','self_compassion'],moods:['sad','anxious','hopeful'],       conds: ['depression'] },
  { id: 'wind_down',       title: 'Wind-Down Ritual',    emoji: '🌙', body: 'Dim your lights and put screens away 30 minutes before bed. Your body needs this signal to begin releasing melatonin.',      goals: ['better_sleep'],                   moods: ['tired','stressed','anxious'],    conds: ['insomnia','bipolar'] },
  { id: 'sigh',            title: 'Physiological Sigh',  emoji: '😮‍💨', body:'Double inhale through your nose, then a long slow exhale. Repeat 3 times for the fastest nervous system reset known.',  goals: ['reduce_stress','manage_anxiety'], moods: ['stressed','anxious'],            conds: ['anxiety','ptsd'] },
  { id: 'affirm',          title: 'Say Something Kind',  emoji: '💕', body: 'Tell yourself one genuinely kind thing, like you would to a close friend. It feels awkward — do it anyway.',               goals: ['self_compassion','boost_mood'],   moods: ['sad','tired','hopeful'],         conds: ['depression','eating_disorder'] },
];

export function getPersonalizedRecs(profile, detectedMood, lastRecId = null) {
  const condIds = (profile.conditions || []).map(c => c.id || c);
  const goalIds = profile.goals || [];

  return RECOMMENDATIONS
    .filter(r => r.id !== lastRecId)
    .map(r => {
      let score = 0;
      if (r.moods.includes(detectedMood)) score += 3;
      goalIds.forEach(g => { if (r.goals.includes(g)) score += 2; });
      condIds.forEach(c => { if (r.conds.includes(c)) score += 1; });
      return { ...r, score };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, 4);
}

// ─── Support Resources ────────────────────────────────────────
export const SUPPORT_RESOURCES = {
  US: {
    crisis: [
      { name: '988 Suicide & Crisis Lifeline', contact: 'Call or text 988', url: 'https://988lifeline.org', note: '24/7 free support' },
      { name: 'Crisis Text Line', contact: 'Text HOME to 741741', url: 'https://www.crisistextline.org', note: 'Free 24/7 text support' },
    ],
    mental: [
      { name: 'NAMI Helpline', contact: '1-800-950-6264', url: 'https://www.nami.org', note: 'National Alliance on Mental Illness' },
      { name: 'SAMHSA Helpline', contact: '1-800-662-4357', url: 'https://www.samhsa.gov', note: 'Mental health & substance support' },
    ],
    physical: [
      { name: 'Health Resources & Services Administration', contact: '', url: 'https://www.hrsa.gov', note: 'Find affordable health care near you' },
    ],
  },
  GB: {
    crisis: [
      { name: 'Samaritans', contact: '116 123', url: 'https://www.samaritans.org', note: 'Free, 24/7, anonymous support' },
      { name: 'CALM', contact: '0800 58 58 58', url: 'https://www.thecalmzone.net', note: '5pm–midnight every day' },
    ],
    mental: [
      { name: 'Mind', contact: '0300 123 3393', url: 'https://www.mind.org.uk', note: 'Mental health information & support' },
      { name: 'Rethink Mental Illness', contact: '0300 5000 927', url: 'https://www.rethink.org', note: 'Advice and specialist support' },
    ],
    physical: [
      { name: 'NHS 111', contact: '111', url: 'https://111.nhs.uk', note: 'Non-emergency medical advice 24/7' },
    ],
  },
  CA: {
    crisis: [
      { name: 'Canada Suicide Prevention', contact: '1-833-456-4566', url: 'https://www.crisisservicescanada.ca', note: '24/7 support' },
      { name: 'Crisis Text Line (CA)', contact: 'Text HOME to 686868', url: 'https://www.crisistextline.ca', note: 'Free 24/7 text support' },
    ],
    mental: [
      { name: 'Canadian Mental Health Association', contact: '', url: 'https://www.cmha.ca', note: 'Nationwide resources and local chapters' },
    ],
    physical: [
      { name: 'Health Canada', contact: '', url: 'https://www.canada.ca/en/health-canada.html', note: 'Federal health information' },
    ],
  },
  AU: {
    crisis: [
      { name: 'Lifeline Australia', contact: '13 11 14', url: 'https://www.lifeline.org.au', note: '24/7 crisis support' },
      { name: 'Beyond Blue', contact: '1300 22 4636', url: 'https://www.beyondblue.org.au', note: 'Anxiety, depression & mental health' },
    ],
    mental: [
      { name: 'headspace', contact: '', url: 'https://headspace.org.au', note: 'Youth mental health 12–25' },
      { name: 'SANE Australia', contact: '1800 187 263', url: 'https://www.sane.org', note: 'Complex mental health support' },
    ],
    physical: [
      { name: 'Healthdirect', contact: '1800 022 222', url: 'https://www.healthdirect.gov.au', note: '24/7 health advice line' },
    ],
  },
  IN: {
    crisis: [
      { name: 'iCall', contact: '9152987821', url: 'https://icallhelpline.org', note: 'Psychosocial support helpline' },
      { name: 'Vandrevala Foundation', contact: '1860-2662-345', url: 'https://www.vandrevalafoundation.com', note: '24/7 mental health helpline' },
    ],
    mental: [
      { name: 'The Live Love Laugh Foundation', contact: '', url: 'https://www.thelivelovelaughfoundation.org', note: 'Mental health awareness & resources' },
      { name: 'NIMHANS', contact: '', url: 'https://nimhans.ac.in', note: 'National Institute of Mental Health' },
    ],
    physical: [
      { name: 'National Health Portal', contact: '1800-180-1104', url: 'https://www.nhp.gov.in', note: 'Health information and resources' },
    ],
  },
  DE: {
    crisis: [
      { name: 'Telefonseelsorge', contact: '0800 111 0 111', url: 'https://www.telefonseelsorge.de', note: 'Free 24/7 counselling' },
    ],
    mental: [
      { name: 'Deutsche Depressionshilfe', contact: '', url: 'https://www.deutsche-depressionshilfe.de', note: 'Depression awareness and support' },
    ],
    physical: [
      { name: 'Bundesgesundheitsministerium', contact: '', url: 'https://www.bundesgesundheitsministerium.de', note: 'Federal health ministry' },
    ],
  },
  FR: {
    crisis: [
      { name: 'Numéro national prévention suicide', contact: '3114', url: 'https://www.3114.fr', note: '24/7 suicide prevention' },
    ],
    mental: [
      { name: 'France Dépression', contact: '01 40 61 64 64', url: 'https://www.francedepression.fr', note: 'Depression support association' },
    ],
    physical: [
      { name: 'Santé.fr', contact: '', url: 'https://www.sante.fr', note: 'French health services directory' },
    ],
  },
  ES: {
    crisis: [
      { name: 'Teléfono de la Esperanza', contact: '717 003 717', url: 'https://www.telefonodelaesperanza.org', note: '24/7 crisis support' },
      { name: 'Línea de Atención Suicida', contact: '024', url: 'https://www.sanidad.gob.es', note: 'Suicide prevention line' },
    ],
    mental: [
      { name: 'SALUD MENTAL España', contact: '', url: 'https://consaludmental.org', note: 'Mental health resources' },
    ],
    physical: [
      { name: 'Ministerio de Sanidad', contact: '', url: 'https://www.sanidad.gob.es', note: 'Spanish health ministry' },
    ],
  },
  IT: {
    crisis: [
      { name: 'Telefono Amico', contact: '02 2327 2327', url: 'https://www.telefonoamico.it', note: 'Emotional support helpline' },
    ],
    mental: [
      { name: 'SISM', contact: '', url: 'https://www.sism.org', note: 'Italian society for mental health' },
    ],
    physical: [
      { name: 'Ministero della Salute', contact: '', url: 'https://www.salute.gov.it', note: 'Italian health ministry' },
    ],
  },
  JP: {
    crisis: [
      { name: 'Inochi no Denwa', contact: '0120-783-556', url: 'https://www.inochi.or.jp', note: '24/7 crisis line' },
      { name: 'Yorisoi Hotline', contact: '0120-279-338', url: 'https://comarigoto.jp', note: '24/7 broad support' },
    ],
    mental: [
      { name: 'TELL Japan', contact: '03-5774-0992', url: 'https://telljp.com', note: 'English-language support in Japan' },
    ],
    physical: [
      { name: 'Ministry of Health, Labour & Welfare', contact: '', url: 'https://www.mhlw.go.jp', note: 'Health information' },
    ],
  },
  BR: {
    crisis: [
      { name: 'CVV – Centro de Valorização da Vida', contact: '188', url: 'https://www.cvv.org.br', note: '24/7 emotional support' },
    ],
    mental: [
      { name: 'CAPS (Community Mental Health Centers)', contact: '', url: 'https://www.gov.br/saude', note: 'Nationwide mental health network' },
    ],
    physical: [
      { name: 'Ministério da Saúde', contact: '136', url: 'https://www.saude.gov.br', note: 'Brazilian health ministry' },
    ],
  },
  MX: {
    crisis: [
      { name: 'SAPTEL', contact: '800 290 0024', url: 'https://www.saptel.org.mx', note: '24/7 crisis and emotional support' },
      { name: 'Línea de la Vida', contact: '800 911 2000', url: 'https://www.gob.mx/salud', note: 'Mental health and addiction support' },
    ],
    mental: [
      { name: 'Secretaría de Salud', contact: '', url: 'https://www.gob.mx/salud', note: 'Mexican health ministry' },
    ],
    physical: [
      { name: 'IMSS', contact: '800 623 2323', url: 'https://www.imss.gob.mx', note: 'Social security health services' },
    ],
  },
  NG: {
    crisis: [
      { name: 'MANI Helpline', contact: '+234-800-800-2000', url: 'https://www.mani.org.ng', note: 'Mental health crisis support' },
    ],
    mental: [
      { name: 'Mentally Aware Nigeria Initiative', contact: '', url: 'https://www.mani.org.ng', note: 'Mental health awareness and resources' },
    ],
    physical: [
      { name: 'Federal Ministry of Health', contact: '', url: 'https://www.health.gov.ng', note: 'Nigerian health ministry' },
    ],
  },
  ZA: {
    crisis: [
      { name: 'SADAG Crisis Line', contact: '0800 456 789', url: 'https://www.sadag.org', note: '24/7 crisis support' },
      { name: 'LifeLine South Africa', contact: '0800 011 780', url: 'https://lifelinesa.co.za', note: 'Free crisis line' },
    ],
    mental: [
      { name: 'South African Depression & Anxiety Group', contact: '', url: 'https://www.sadag.org', note: 'Comprehensive mental health resources' },
    ],
    physical: [
      { name: 'Department of Health', contact: '0800 60 10 11', url: 'https://www.health.gov.za', note: 'South African health department' },
    ],
  },
  NZ: {
    crisis: [
      { name: 'Lifeline NZ', contact: '0800 543 354', url: 'https://www.lifeline.org.nz', note: '24/7 crisis support' },
      { name: 'Youthline', contact: '0800 376 633', url: 'https://www.youthline.co.nz', note: 'Support for young people' },
    ],
    mental: [
      { name: 'Mental Health Foundation NZ', contact: '', url: 'https://www.mentalhealth.org.nz', note: 'Mental health resources and support' },
    ],
    physical: [
      { name: 'Healthline NZ', contact: '0800 611 116', url: 'https://www.health.govt.nz', note: '24/7 health advice' },
    ],
  },
  SG: {
    crisis: [
      { name: 'Samaritans of Singapore', contact: '1767', url: 'https://www.sos.org.sg', note: '24/7 crisis support' },
    ],
    mental: [
      { name: 'Institute of Mental Health', contact: '6389 2000', url: 'https://www.imh.com.sg', note: 'Mental health specialist care' },
      { name: 'Silver Ribbon Singapore', contact: '6386 1928', url: 'https://www.silverribbonsingapore.com', note: 'Mental health advocacy' },
    ],
    physical: [
      { name: 'HealthHub', contact: '', url: 'https://www.healthhub.sg', note: 'Singapore health platform' },
    ],
  },
  AE: {
    crisis: [
      { name: 'National Mental Health Helpline', contact: '800-HOPE (4673)', url: 'https://www.mohap.gov.ae', note: 'UAE mental health helpline' },
    ],
    mental: [
      { name: 'Dubai Health Authority', contact: '800 342', url: 'https://www.dha.gov.ae', note: 'Mental health services' },
    ],
    physical: [
      { name: 'Ministry of Health & Prevention', contact: '80011111', url: 'https://www.mohap.gov.ae', note: 'UAE health ministry' },
    ],
  },
  PK: {
    crisis: [
      { name: 'Umang Pakistan', contact: '0317-4288665', url: 'https://umang.com.pk', note: 'Mental health helpline' },
      { name: 'Rozan Counseling Centre', contact: '051-2890505', url: 'https://www.rozan.org', note: 'Counseling support' },
    ],
    mental: [
      { name: 'Pakistan Association for Mental Health', contact: '', url: 'https://pamh.org.pk', note: 'Mental health resources' },
    ],
    physical: [
      { name: 'Ministry of National Health', contact: '1166', url: 'https://nhsrc.gov.pk', note: 'Pakistan health helpline' },
    ],
  },
  PH: {
    crisis: [
      { name: 'Hopeline Philippines', contact: '1553', url: 'https://www.ncmh.gov.ph', note: '24/7 crisis support' },
    ],
    mental: [
      { name: 'National Center for Mental Health', contact: '0917 899 8727', url: 'https://www.ncmh.gov.ph', note: 'Mental health services' },
    ],
    physical: [
      { name: 'Department of Health Philippines', contact: '1555', url: 'https://doh.gov.ph', note: 'Health information and services' },
    ],
  },
  KE: {
    crisis: [
      { name: 'Befrienders Kenya', contact: '0800 720 990', url: 'https://www.befrienderskenya.org', note: 'Emotional support and crisis line' },
    ],
    mental: [
      { name: 'Mathari National Hospital', contact: '020-2726300', url: 'https://matharihospital.go.ke', note: 'Mental health services' },
    ],
    physical: [
      { name: 'Ministry of Health Kenya', contact: '', url: 'https://www.health.go.ke', note: 'Kenyan health ministry' },
    ],
  },
  DEFAULT: {
    crisis: [
      { name: 'Befrienders Worldwide', contact: '', url: 'https://www.befrienders.org', note: 'Global emotional support network' },
      { name: 'IASP Crisis Centres Directory', contact: '', url: 'https://www.iasp.info/resources/Crisis_Centres/', note: 'Find crisis centres worldwide' },
    ],
    mental: [
      { name: 'World Health Organization – Mental Health', contact: '', url: 'https://www.who.int/health-topics/mental-health', note: 'Global mental health resources' },
    ],
    physical: [
      { name: 'World Health Organization', contact: '', url: 'https://www.who.int', note: 'Global health information' },
    ],
  },
};
