# Mind Fusion Desktop

A native Python desktop port of the Mind Fusion web app - 9 tabs: Today
(dashboard), chat, health, nutrition photo analysis, journal, insights,
exercises, affirmations and support resources, built with PySide6 (Qt) and SQLite instead
of React and localStorage.

All AI features talk to a **local** AI server on your own machine (Ollama by
default, or LM Studio / any OpenAI-compatible server) - nothing is ever sent
to a cloud AI provider.

## What's in it

**Setup screens** - a welcome page, sign-up / sign-in with inline validation,
and a 5-step profile wizard (step indicator, searchable country chips, age
cards, health conditions, habits, up to 3 goals). Signing in with an email
that has no account offers to create one rather than silently making it.

A left sidebar switches between pages; the sidebar also holds the local-AI
status, settings, the light/dark toggle (🌙/☀️), data export and sign out.

- **Today** - greeting, check-in streak, one-click mood check-in, a daily
  **habit checklist** (from the habits you picked at sign-up, with per-habit
  streaks), a **sleep log** (hours + quality), a suggestion for your latest
  mood, the daily affirmation, and quick actions
- **Chat** - local LLM companion; starter prompts on an empty chat; Enter to
  send; history saved between sessions; **🌐 Reply in** picker - change the
  language the companion answers in at any time (Match what I write, English,
  Hindi, **Hinglish** = Hindi in English letters, Spanish, French, German, ...;
  remembered per user; also tells speech-to-text which language to expect); 🎤 speech-to-text; 📷 **live camera
  window** (you see yourself with a box on your face while the camera is on;
  *Analyse mood* averages a few frames, *Switch camera* handles Continuity
  Camera); a **crisis-support alert** that shows your country's helplines if a
  message mentions self-harm
- **Journal** - prompts, live mood detection, search and mood filter
- **Nutrition** - drag-and-drop (or browse) a meal photo; the local vision model's
  answer becomes calorie, balance-score and macro cards, food tags, an
  energy/mood note and a tip. Messy model output is cleaned up (or rejected
  with a clear message - nothing is invented). Today's totals, plus a recent
  meals list with delete.
- **Insights** - pick 7 / 30 / 90 days / all time: headline numbers compared
  with the previous period, plain-language findings ("On days you slept 7+
  hours..."), mood mix, mood trend, a 12-week mood calendar, best days of the
  week, sleep, habit consistency, calories and macros, meals, exercises and
  journal summary. Charts are drawn with Qt (hover for details) and follow the
  light/dark theme. **Calories per day** and **Macros** are dropdowns inside the
  Nutrition card, and **Best days of the week** and **Sleep** are dropdowns inside the mood
  calendar card (which also shows your check-in streaks); each shows a one-line
  summary while closed, and open/closed is remembered. The Exercises card has
  **＋ Add exercise** for things you did outside the app (a walk, a class) -
  pick or type the activity, when, and how long; entries can be removed.
- **Exercises** - 7 guided practices (breathing, relaxation, body scan,
  gratitude, grounding); finished sessions are logged. **＋ Add exercise** logs
  something you did yourself (activity, when, how long), and a *Recently
  logged* list shows your latest entries (also available on Insights)
- **Dark mode** - remembered between launches
- **Export data** - everything (including habits and sleep) as one JSON file

Screenshots are in `screenshots/` (rendered from demo data).

## Setup

```bash
cd desktop_app
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

You'll also want [Ollama](https://ollama.com) installed and running, with a
chat model and a vision model pulled:

```bash
ollama serve
ollama pull llama3.2   # chat
```

You don't need to pull the vision model (`llava`) yourself - the Nutrition
tab downloads it automatically the first time you use meal analysis, if it
isn't already installed.

The first time you use the mic button or the camera button in Chat, their
models (Whisper for speech-to-text, a small FER+ emotion model for the
camera) download automatically too - a few seconds to a minute depending on
your connection, one-time only, fully local afterwards.

## Run

```bash
source venv/bin/activate
python main.py
```

## Tests

```bash
python -m unittest discover -s tests -v
```

101 automated tests covering mood detection (English, Hindi, Hinglish), the
crisis-language check, the photo loader, the live camera (worker, camera
switching, capture, and the window), the setup/sign-in flow, the database
layer, the Nutrition and Insights pages, every chart, and the main screens. They use a temporary database and stand-ins for
the AI server and camera, so they never touch your data, need no camera and
download nothing large. (The face tests fetch one small public sample
portrait the first time and are skipped if you're offline.)

## Notes on language and photos

- **Mood detection** understands English plus Hindi / Hinglish (Hindi typed
  in English letters, e.g. "mujhe dar lagta hai") and matches whole words.
  It is a keyword check, not a language model, so other languages fall back
  to "calm" until keywords are added in `data.py`.
- **Meal photos**: PNG, JPEG, HEIC/HEIF, WebP, BMP, TIFF and GIF. If a photo
  can't be opened, the app says why - e.g. macOS blocking access to the
  folder (allow Python under System Settings -> Privacy & Security ->
  Files and Folders).

## Project layout

```
desktop_app/
  main.py              entry point - creates the window, switches between
                        onboarding and the signed-in app
  data.py               static content: moods, onboarding options, exercises,
                        affirmations, journal prompts, support resources
  db.py                 SQLite persistence (mind_fusion.db, created on first run)
  ai_client.py           talks to the local AI server (chat, vision, model pull)
  image_utils.py         loads meal photos and explains why when one can't be read
  nutrition_logic.py     cleans up the vision model's meal answer (no Qt)
  insights_logic.py      time ranges, comparisons and findings for Insights (no Qt)
  voice.py               local speech-to-text (faster-whisper) for the mic button
  face_analysis.py       live camera worker + face/expression detection (OpenCV +
                        a small ONNX emotion model) for the camera button
  workers.py             background QThreads so network calls never freeze the UI
  styles.py               shared Qt stylesheet
  ui/
    onboarding.py         welcome / sign up / sign in / 5-step profile wizard
    main_window.py         signed-in app shell: sidebar + pages
    camera_dialog.py       the live camera window
    charts.py              painter-drawn charts shared by Nutrition and Insights
    settings_dialog.py     local AI server settings
    widgets.py, flow_layout.py   small reusable UI helpers
    tabs/                  one file per tab
```

## Local AI models used

Everything runs on your machine - nothing goes to Claude, OpenAI, or any
other cloud AI:

| Feature              | Model                                    | Notes |
|-----------------------|-------------------------------------------|-------|
| Chat + mood coaching  | Llama 3 / Mistral (via Ollama)            | you choose the model in Settings |
| Meal photo analysis   | llava (via Ollama)                        | auto-downloaded on first use |
| Speech-to-text (mic)  | Whisper `base` (via faster-whisper)       | auto-downloaded on first use |
| Camera mood check     | FER+ emotion model (via onnxruntime)      | auto-downloaded on first use |

The camera feature is a stand-in for DeepFace, which the original design
called for - DeepFace depends on TensorFlow, and TensorFlow doesn't ship a
build for Python 3.14 yet. FER+ does the same job (an 8-category facial
expression classifier) without that dependency.

## How accounts work

There's no real password checking (this is a local single-user wellbeing
app, not a security product) - an "account" is a row in the `users` table
keyed by email. Signing in with an email that already has a saved profile
skips the onboarding questions entirely, since your answers are tied to
your account, not to a single browser session. Signing out only clears the
"who's currently signed in" pointer - it never deletes your profile, mood
history, or journal entries.
