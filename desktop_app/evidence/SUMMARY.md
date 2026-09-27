# Evidence summary — Mind Fusion desktop build

Generated 2026-09-26 on an Apple M1, 16 GiB, macOS 14.6.1, Python 3.14.5, Ollama 0.30.7.
All paths below are relative to `desktop_app/evidence/` unless they start with a source-file name.
Nothing was committed or pushed. No application code was changed. Every result file is raw script output.

## Read this first

1. **There is no fusion engine in this codebase.** `test_components.py` assumed one (channel scores → one mood + ambiguity flag, a 0.12 margin, "Figure 9"). Neither the desktop app nor the React prototype in `src/` contains it (searched for `fuse`, `ambiguous`, margin logic: no matches). In the desktop app, text, speech and camera each write their own mood entry (`ui/tabs/chat_tab.py:363-366`, `:_on_face_mood`); nothing compares them. The 8 fusion tests are therefore **SKIPPED, not passed** (`pytest.txt:22-29`). If your report describes a fusion engine, the report and the build disagree.
2. **The recommender returns four suggestions, not three** (question 1 below). Your screenshots are right; the text is wrong.
3. **Voice check-in makes one outbound DNS lookup (`huggingface.co`) the first time Whisper loads**, unless `HF_HUB_OFFLINE=1` is set. No audio is sent by that lookup, but "no outbound requests" is not literally true for the shipped build (`output/06_network_guard_default.txt:15`).
4. **TC-E02 (Hindi) no longer fails.** The Devanagari test sentence is now classified correctly because a Hindi/Hinglish lexicon was added during this project. The recorded failure is out of date (`moods.txt:19`). I was asked to confirm it and cannot.
5. **Two new failures you had not recorded:** TC-F07's "stressed" phrase (`stressful` is not in the lexicon) and the missing contraindication filter (`pytest.txt:14, 31`).
6. **The nutrition analyser can show and save placeholder data.** With the app's own prompt and a photo of a laptop, llava echoed the prompt's example (`item1`, 450 kcal, 22/55/14 g, balance 7) and the app accepted and would save it (`output/03b_meal_analyser_NO_FOOD_photo.txt`). Reported, not fixed.
7. I could not obtain test-case definitions for several IDs (see table). They are marked BLOCKED rather than guessed.

## Results table

| Test case | Result | Evidence (file:line) and notes |
|---|---|---|
| TC-F01 onboarding answers saved | **PASS** | `database_after_restart.txt:90-108` — `profiles` row holds country, language, age_group, conditions, habits, goals (six fields). Test account `evidence@example.com`. |
| TC-F04 | **BLOCKED** | Definition not available to me; no run maps to it. |
| TC-F07 all eight moods reachable | **FAIL (7 of 8)** | `pytest.txt:14,74`; `moods.txt:14` — "work has been stressful all week" → `calm` 0.30. `stressful` is not in `MOOD_WORDS["stressed"]`; `stressed`, `overwhelmed`, etc. are. Left in as a real lexicon gap. |
| TC-F09 | **BLOCKED** | Definition not available. |
| TC-F10 | **BLOCKED** | Definition not available. |
| TC-F11 journal entry saved | **PASS** | `database_before_restart.txt:46-60`, `database_after_restart.txt:46-60`. |
| TC-F12 | **BLOCKED** | Definition not available. |
| TC-F13 | **BLOCKED** | Definition not available. |
| TC-F15 | **BLOCKED** | Definition not available. |
| TC-F16 | **BLOCKED** | Definition not available. |
| TC-F19 meal analyser returns an analysis | **PASS** (definition inferred from the script header) | `meal.txt:11-60` (both runs returned nutrition JSON); `output/03_meal_analyser_twice.txt` (app path, parsed). Content accuracy is not asserted; run 1 in `meal.txt` is not strictly valid JSON (missing comma, trailing `//` comment) and only the app's tolerant parser accepts it. |
| TC-F21 calorie totals | **FAIL (indicative)** | `output/08_calorie_consistency.txt` — real-photo run: reported 650 kcal vs 745 kcal implied by its own macros (−95). `meal.txt` (your script): run 1 reported 800 vs 1090 implied; run 2 reported 600 vs 724 implied (my arithmetic, 4/4/9 kcal per g). App does not reconcile them (`nutrition_logic.py:78-79`). **My reading of "calorie totals" is an assumption**; the placeholder rows in that file are self-consistent and prove nothing. |
| TC-F22 image with no food | **FAIL (confirmed)** | `meal.txt:170-187` — laptop photo → `"foods": ["Laptop"]`, 10 kcal, balance 5/10. Worse on the app's own path: `output/03b_meal_analyser_NO_FOOD_photo.txt:12-75` — `item1`, 450 kcal, accepted by `parse_analysis` and displayed. |
| TC-I01 latency | **FAIL against the script's 5 s budget; figures below** | Your `bench`: `latency.txt:12-25` warm runs 4.69–5.88 s, worst 5.88 s. Real ChatTab path, 20+20 runs: `output/07_timing.txt` — text warm median 2.74 s / p95 3.51 s / max 3.59 s; voice total (Whisper + reply) warm median 3.53 s / p95 4.47 s / **max 5.01 s**. Whisper alone median 0.76 s. First voice run 20.6 s (Whisper model load). The 5 s budget is something `evidence_run.py` invented — you did not give me the report's figure. The bench prompt asks for 4–6 sentences, so its replies are longer than the app's (~2.7 s). Caveats in the file: TTS speech, offscreen window. |
| TC-I02 | **BLOCKED** | Definition not available. |
| TC-I03 no outbound traffic | **FAIL as shipped (voice path only)** | `output/06_network_guard_default.txt:15` — DNS lookup `huggingface.co` at Whisper load; blocked by the guard, transcription still worked from cache. `output/06_network_guard_hf_offline.txt:36` — with `HF_HUB_OFFLINE=1`: PASS. Text, meal and face paths: only `127.0.0.1:11434`. **Not done:** a run with Wi-Fi physically off; native sockets (ONNX, OpenCV) are not covered by a Python socket guard. The `lsof` block inside `privacy_*.txt` is machine-wide, ran while the app was not in a check-in, and is **not** evidence for this case. |
| TC-I07 data survives restart | **PASS** (caveat) | `database_restart_process.txt:1-6`, `database_after_restart.txt:46-108` identical to `database_before_restart.txt` apart from the timestamp. The "restart" was a new OS process opening the same file and starting the real `AppWindow` offscreen — not a person quitting and reopening the window. |
| TC-I08 no audio written | **PASS** | `output/05_no_audio_file.txt:6-33,41` — voice.py has no file-writing calls; before/after snapshot 0 created / 1 modified (a HuggingFace `refs/main` metadata file, not audio); positive control planted a `.wav` and the scan found it. `privacy_2_after_voice_checkin.txt:12` — 0 new files. See the two `FIRST_ATTEMPT` files for why the pair was redone. |
| TC-E01 negation | **FAIL (confirmed)** | `moods.txt:18` — "I am not stressed at all" → `stressed`; `pytest.txt:21` XFAIL. |
| TC-E02 Hindi | **PASS — recorded failure NOT confirmed** | `moods.txt:19` — "मुझे बहुत चिंता हो रही है" → `anxious`. Only that one Devanagari sentence was tested here. |
| TC-E03 mixed emotion / stability | **FAIL (confirmed)** for the mixed-emotion behaviour; deterministic | `e03_word_hits.txt` — "overwhelmed" (stressed) and "drained" (tired) tie 1–1; `max()` picks the first by dictionary order (`data.py:157`), confidence 0.33, no ambiguity reported. `moods.txt:20` — the script's own check (repeat runs agree) is `ok`. Which of the two you intend depends on the case definition. |
| TC-E06 neutral text | **PASS** | `moods.txt:21` — calm, 0.30; `pytest.txt:17`. |
| TC-E12 non-determinism | **FAIL (confirmed)** | `meal.txt:95` "identical: NO"; `output/03_meal_analyser_twice.txt:90-96` — all fields differ. Sampling temperature is Ollama's default 0.8 (`/opt/homebrew/var/log/ollama.log`: `temp = 0.800`). |
| TC-E13 text/camera disagreement flagged | **FAIL (not implemented); automated test BLOCKED** | `pytest.txt:27` skipped — no fusion engine exists (see "Read this first" 1). |

Additional results not in your list:

| Item | Result | Evidence |
|---|---|---|
| Recommender contraindication filter (FR19) | **FAIL** | `pytest.txt:31,51-70`. `conds` in `RECOMMENDATIONS` are conditions a tip *helps* (+1 score, `data.py:572-574`); nothing is ever excluded. The original assertion would have passed vacuously, so I rewrote it to check that the data can express a contraindication at all. |
| Unit tests as adapted | 15 passed, 2 failed, 8 skipped, 1 xfailed | `pytest.txt:76` |
| Earlier full suite | 101 passed | `output/01_pytest_output.txt` |

## Step 1 — where things live

| Component | Real location |
|---|---|
| Mood mapper | `data:detect_mood(text)` → dict with `mood`, `confidence` (`data.py:144-159`); whole-word keyword match over `MOOD_WORDS` |
| Fusion engine | **does not exist** |
| Recommendation mapper | `data:get_personalized_recs(profile, detected_mood, last_rec_id)` (`data.py:556-578`) |
| Ollama client | `ai_client.py`: `chat_ai` (`:59`), `vision_ai`, `check_connection`, `pull_model`; default `llama3.2` / `llava` (`:38-41`) |
| Whisper wrapper | `voice.py`: `MicRecorder` (in-memory frames, `:19-40`), `TranscribeWorker` (`:43-72`, `WhisperModel("base", device="cpu", compute_type="int8")` at `:66`) |
| SQLite | `db.py:16` `DB_PATH = <app folder>/mind_fusion.db`; `db.py:21` `sqlite3.connect(path)`; tables: users, profiles, ai_config, mood_history, journal_entries, affirm_favorites, nutrition_history, chat_messages, app_settings, habit_log, sleep_log, exercise_sessions, session |

## Step 2 — what I changed in the scripts (originals in `user_scripts/original/`)

`test_components.py` (in `desktop_app/`):
- `MOOD_MAPPER = "data:detect_mood"`, `RECOMMENDER = "data:get_personalized_recs"`, `FUSION_ENGINE = None` (fusion tests skip with an explicit reason).
- `RECOMMENDER_CALL` adapted to the real signature (a `profile` dict; only the previous top suggestion id is passed).
- "exactly three" → "exactly four".
- "recent suggestions not repeated" → the previous *top* suggestion is not repeated (the app remembers only one id).
- The contraindication test rewritten as described above.
- The mood phrase list is untouched, so the `stressful` failure is genuine.

`evidence_run.py` (in `desktop_app/`):
- `MOOD_MAPPER = "data:detect_mood"`, `CHAT_MODEL = "llama3.2"`.
- `DB_PATH` points at the **scratch test-account database** `output/evidence.db`, not `mind_fusion.db` (with `DB_PATH` empty the script globs `*.db` in the current folder and would have opened your real one).
- `"nutrition"` added to the table filter (the table is `nutrition_history`, which `"meal"` did not match).
- Known limitation left as is: its `meal` command sends its own prompt, not the app's `NUTRITION_PROMPT`; the app's own path is in `output/03*`.

## Step 4 — answers from the code

1. **Suggestions:** four. `data.py:558` docstring "return the top 4", `data.py:578` `return scored[:4]`; the panel renders every item (`ui/tabs/chat_tab.py:428`). Test: `pytest.txt:30`.
2. **Fallback when Ollama is unreachable:** yes, scripted. `chat_tab.py:385` routes any worker error to `_on_reply_failed`; `:394-398` picks `CRISIS_FALLBACK` (`data.py:96`) or `MOOD_FALLBACKS[mood]` (`data.py:74`), stores it with mood `"offline"`, and shows it with "(offline response)" (`chat_tab.py:60`). No error surfaces. Requests time out after 180 s (`ai_client.py:73`), so a hung Ollama means up to three minutes before the fallback appears. That happened three times while timing: Ollama's GPU runner stalled with no output for about five minutes and returned HTTP 500 (`output/07_timing_ATTEMPT3_aborted_ollama_stall.txt`). I did not capture a clean screenshot of the fallback bubble.
3. **History in the prompt:** yes, the last 20 messages (10 exchanges), including the message just sent — `chat_tab.py:379` (`self.messages[-20:]`). Saved history is reloaded at start-up (`:283`, `:303-309`), excluding scripted offline replies. The system prompt is sent separately (`ai_client.py:67`).
4. **Temporary audio file:** no. `MicRecorder` appends numpy blocks to a list (`voice.py:29-30`) and returns one array (`:40`); `TranscribeWorker` passes that array straight to `transcribe` (`voice.py:68`). No `open`, `write`, `tempfile`, or `wave` in the file (`output/05_no_audio_file.txt:6-7`). Confirmed dynamically (TC-I08). Caveat: the Whisper *model* is cached on disk in `~/.cache/huggingface`.
5. **Model tags and sizes** (`models.txt:12-15`, `models_extra.txt`): `llama3.2:latest` 2.0 GB (3.2B, Q4_K_M); `llava:latest` 4.7 GB (7B, Q4_0); `mistral:latest` 4.4 GB (7.2B, Q4_K_M) is installed but the app never uses it by default; faster-whisper `base` (Systran) 141 MB on disk, faster-whisper 1.2.1; `emotion-ferplus-8.onnx` 35.0 MB and `face_detection_yunet_2023mar.onnx` 233 KB in `models/`. **There is no `llama3` on this machine** — the report should say `llama3.2`. The app auto-pulls only the vision model (`ui/tabs/nutrition_tab.py:305-328`).
6. **SQLite encrypted at rest:** no. Plain `sqlite3.connect` with no key (`db.py:21`); no SQLCipher or encryption code anywhere. `encryption_check.txt` shows the `SQLite format 3` header and journal text and the email readable with `strings`. macOS FileVault is **On** on this machine, which protects the disk, not the file.

## Personal data and hygiene — check before pasting into the report

- `privacy_1_baseline.txt`, `privacy_2_after_voice_checkin.txt` and both `FIRST_ATTEMPT` files contain a machine-wide `lsof` listing: other applications' connections (OneDrive, Spotify, Discord, VS Code, and system services), your global IPv6 address and local IP `192.168.10.130`. **Personal — redact or omit that block.** I saved them unedited as asked.
- Every file contains `/Users/somya/...` paths. `assets/meal_photo_source.json` names a public Wikimedia author (CC BY-SA 4.0; needs attribution). `assets/nofood_photo.jpg` is CC0.
- All database evidence uses the scratch account `evidence@example.com` in `output/evidence.db`. Your `mind_fusion.db` was not opened by any script here.

## What went wrong along the way (kept, not hidden)

- **Disk was at 100%** (about 52 MB free at the start). Cause is not this project (207 GiB used on the data volume). I freed 2.1 GB by purging pip's download cache (regenerable) and nothing else. About 1 GB is still free, so timings were taken under some memory/disk pressure (swap 1.3 GB used).
- **Ollama wedged** with a dead llava runner listed as "Stopping…" for hours. Some early runs were affected: `meal.txt` run 2 took 991 s and `latency_ATTEMPT1_before_ollama_restart.txt` was measured in that state. I restarted the Ollama service (`brew services restart ollama`; models untouched), then re-ran the bench and timing. Aborted timing attempts are kept as `output/07_timing_ATTEMPT1/2/3_*`. The final `output/07_timing.txt` completed 20 + 20 runs with zero failures and zero scripted fallbacks.
- **First privacy pair was contaminated** by my own text-to-speech test clip being written into a scanned folder (it showed up as a "new audio file"). I moved the stimulus outside every scanned location and redid the pair; the first pair is kept as `privacy_*_FIRST_ATTEMPT_*.txt`.
- `pkill` earlier stopped your running app; it is running again (one instance).

## Limits of this evidence

- No microphone: speech is macOS text-to-speech (Whisper got 20/20 exact), which is easier than real speech. No human-audio accuracy claim is supported.
- The windows were rendered offscreen; timings exclude real painting.
- Not done: Wi-Fi-off run; camera/FER evidence on a real face; screenshots (crisis alert, fallback bubble, Journal with search, exercise timer). Those need to be captured by hand.
- The "restart" in TC-I07 was a new process, not a GUI quit.
