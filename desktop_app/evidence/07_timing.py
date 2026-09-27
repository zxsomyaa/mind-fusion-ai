"""
Evidence 7 - end-to-end latency of a check-in, per stage (Objective 5 / Table 10).

Regenerate:  MF_STIMULUS_DIR=<dir outside the project> python evidence/07_timing.py > evidence/output/07_timing.txt

Drives the app's REAL ChatTab (the same widget the user types into), 20 text check-ins and 20 voice
check-ins, against a scratch database, using the local Ollama server (llama3.2) and the real
faster-whisper "base" model. Stages are timed by wrapping the functions the tab itself calls.

  text  check-in : press Send -> [crisis check, mood detection, DB writes, recommendations, prompt build,
                   Ollama reply] -> reply bubble shown and Send re-enabled
  voice check-in : press stop on the mic -> [Whisper transcription] -> transcript in the box, THEN the same
                   text pipeline as above (the app makes the user press Send, so the two are reported
                   separately and as a sum)

What is NOT in the numbers, on purpose:
  * the time the person spends speaking or typing
  * a human reading the reply
  * on-screen painting: the window is rendered offscreen and never shown, so layout work is included
    but real GPU/compositor time is not. Treat the totals as a slight underestimate of what a person sees.
Conversation history is cleared before every check-in so each run is an independent "first message".
The first run of each kind is reported separately because it includes loading the model into memory.
There is no microphone: speech is macOS text-to-speech fed through the real MicRecorder (see 05).
"""
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np                                         # noqa: E402
from PySide6.QtCore import QCoreApplication                # noqa: E402
from PySide6.QtWidgets import QApplication                 # noqa: E402

import ai_client                                           # noqa: E402
import voice                                               # noqa: E402
from db import Database                                    # noqa: E402
from ui.tabs import chat_tab                               # noqa: E402

N = int(os.environ.get("MF_N", "20"))
TEXTS = [
    "I feel anxious about my exam tomorrow", "Work has been really stressful this week",
    "I am so tired and I cannot sleep properly", "Today was a good day and I feel happy",
    "I feel sad and a bit lonely tonight", "I am grateful for my friends who helped me today",
    "I feel calm after my evening walk", "I am hopeful that next month will be better",
    "mujhe bahut dar lag raha hai", "I have too much on my plate and I feel overwhelmed",
]
SPOKEN = [
    "I feel a bit anxious about my exam tomorrow", "Work has been really stressful this week",
    "I am very tired and I could not sleep well", "Today was a good day and I feel happy",
    "I feel sad and lonely tonight", "I am grateful for my friends today",
    "I feel calm after my walk this evening", "I am hopeful that next month will be better",
    "I have been worried about my results all day", "I am exhausted after a long day at college",
]

STAGES = ["crisis check", "mood detection", "DB writes", "recommendations (compute + cards)",
          "prompt build", "LLM reply (Ollama)"]
acc = {}


def timed(stage, fn):
    def wrapper(*a, **kw):
        t = time.perf_counter()
        try:
            return fn(*a, **kw)
        finally:
            acc[stage] = acc.get(stage, 0.0) + (time.perf_counter() - t) * 1000
    return wrapper


chat_tab.detect_crisis = timed("crisis check", chat_tab.detect_crisis)
chat_tab.detect_mood = timed("mood detection", chat_tab.detect_mood)
chat_tab.build_system_prompt = timed("prompt build", chat_tab.build_system_prompt)
chat_tab.chat_ai = timed("LLM reply (Ollama)", chat_tab.chat_ai)
chat_tab.ChatTab._refresh_recs = timed("recommendations (compute + cards)", chat_tab.ChatTab._refresh_recs)


def stats(values):
    v = sorted(values)
    p95 = v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]
    return (min(v), statistics.median(v), statistics.mean(v), p95, max(v))


def pump_until(cond, limit=260):   # the app itself gives up on Ollama after 180 s (ai_client.py timeout=180) and shows the scripted fallback
    end = time.time() + limit
    while not cond():
        QCoreApplication.processEvents()
        time.sleep(0.002)
        if time.time() > end:
            raise TimeoutError("timed out waiting")


print("Mind Fusion Desktop - per-stage latency of a check-in")
print(f"date    : {datetime.now():%Y-%m-%d %H:%M:%S}")
print(f"machine : {platform.system()} {platform.machine()} ({platform.mac_ver()[0]}), Python {platform.python_version()}")
print(f"chip    : {subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True).stdout.strip()}"
      f" ; RAM {int(subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True).stdout) / 2**30:.0f} GiB")
print(f"models  : chat={ai_client.DEFAULT_CONFIG['chat_model']} via Ollama {subprocess.run(['ollama', '--version'], capture_output=True, text=True).stdout.strip()}; "
      f"speech=faster-whisper 'base' int8 CPU")
print(f"load    : swap {subprocess.run(['sysctl', '-n', 'vm.swapusage'], capture_output=True, text=True).stdout.strip()} ; "
      f"disk free {subprocess.run('df -h /System/Volumes/Data | tail -1 | tr -s " " | cut -d" " -f4', shell=True, capture_output=True, text=True).stdout.strip()}")
print(f"runs    : {N} text + {N} voice, history cleared before each")
print()

app = QApplication([])
db = Database(str(Path(tempfile.mkdtemp()) / "timing_scratch.db"))
uid = db.create_user("Timing Test", "timing@example.com")
profile = {"country": "IN", "language": "en", "age_group": "18-24", "conditions": [], "habits": [], "goals": ["reduce_stress"]}
config = dict(ai_client.DEFAULT_CONFIG)
chat = chat_tab.ChatTab(db, uid, profile, lambda: config)
chat.resize(1000, 700)

# wrap DB writes on this instance
for name in ("add_mood_entry", "add_chat_message"):
    setattr(db, name, timed("DB writes", getattr(db, name)))

# warm Ollama once so run 1 is not model-load time of the LLM only if the user has been chatting; we report
# cold (first) separately instead of hiding it.


def reset_chat():
    chat.messages.clear()
    acc.clear()


def run_send(text):
    """Type text, press Send, wait for reply. Returns (total_ms, stage dict)."""
    reset_chat()
    chat.input_box.setPlainText(text)
    t0 = time.perf_counter()
    chat._send()
    pump_until(lambda: chat.send_btn.isEnabled() and chat.send_btn.text() != "Sending…")
    total = (time.perf_counter() - t0) * 1000
    offline = any(m.get("role") == "assistant" for m in chat.messages) is False   # reply failed -> scripted fallback shown
    return total, dict(acc), offline


# ------------------------------------------------------------------ text
text_rows = []
for i in range(N):
    total, st, offline = run_send(TEXTS[i % len(TEXTS)])
    text_rows.append((total, st, offline))
    print(f"text  {i + 1:>2}: total {total / 1000:6.2f} s  | LLM {st.get('LLM reply (Ollama)', 0) / 1000:6.2f} s"
          f"{'  [OLLAMA FAILED -> scripted fallback]' if offline else ''}", flush=True)

# ------------------------------------------------------------------ voice
clip_dir = Path(os.environ.get("MF_STIMULUS_DIR", tempfile.mkdtemp())) / "timing"
clip_dir.mkdir(parents=True, exist_ok=True)
clips = []
for i, sentence in enumerate(SPOKEN):
    aiff, wav = clip_dir / f"s{i}.aiff", clip_dir / f"s{i}.wav"
    if not wav.exists():
        subprocess.run(["say", "-v", "Samantha", "-o", str(aiff), sentence], check=True)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(wav)], check=True)
    with wave.open(str(wav)) as w:
        clips.append(np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype("float32") / 32768.0)

current = {"clip": None}


class FakeInputStream:
    def __init__(self, samplerate, channels, dtype, callback):
        self.callback, self._thread = callback, None

    def start(self):
        def feed():
            clip = current["clip"]
            for i in range(0, len(clip), 1024):
                self.callback(clip[i:i + 1024].reshape(-1, 1), 1024, None, None)
        self._thread = threading.Thread(target=feed, daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread:
            self._thread.join()

    def close(self):
        pass


voice.sd.InputStream = FakeInputStream
transcripts = {}
orig_on_transcribed = chat._on_transcribed
chat._on_transcribed = lambda text: (transcripts.update(text=text), orig_on_transcribed(text))

voice_rows = []
for i in range(N):
    clip = clips[i % len(clips)]
    current["clip"] = clip
    reset_chat()
    chat.input_box.clear()
    transcripts.clear()
    chat._toggle_recording()                         # start (real MicRecorder)
    time.sleep(0.05)
    t0 = time.perf_counter()
    chat._toggle_recording()                         # stop -> real TranscribeWorker thread
    pump_until(lambda: "text" in transcripts or "Couldn't transcribe" in chat.assist_status.text())
    stt_ms = (time.perf_counter() - t0) * 1000
    spoken = chat.input_box.toPlainText()
    total_send, st, offline = run_send(spoken) if spoken else (0.0, {}, True)
    voice_rows.append((stt_ms, total_send, st, offline, len(clip) / voice.SAMPLE_RATE, spoken))
    print(f"voice {i + 1:>2}: speech {len(clip) / 16000:4.1f} s of audio | transcribe {stt_ms / 1000:5.2f} s | "
          f"then send->reply {total_send / 1000:6.2f} s | text: {spoken!r}", flush=True)

# ------------------------------------------------------------------ report
def table(title, rows_ms):
    print(f"\n  {title}")
    print(f"    {'':<38}{'min':>9}{'median':>9}{'mean':>9}{'p95':>9}{'max':>9}   (ms)")
    for label, vals in rows_ms:
        if not vals:
            continue
        s = stats(vals)
        print(f"    {label:<38}" + "".join(f"{x:>9.1f}" for x in s))


def stage_series(rows, key_idx=1):
    series = {s: [r[key_idx].get(s, 0.0) for r in rows] for s in STAGES}
    return series


print("\n" + "=" * 100)
print(f"RESULTS - all figures in milliseconds unless stated. n = {N} per kind.")
print("=" * 100)

warm_text = text_rows[1:]
table(f"TEXT check-in, WARM (runs 2-{N}, n={len(warm_text)}): Send pressed -> reply shown", [
    *[(s, v) for s, v in stage_series(warm_text).items()],
    ("other (thread hand-off, widgets, event loop)", [r[0] - sum(r[1].get(s, 0) for s in STAGES) for r in warm_text]),
    ("TOTAL", [r[0] for r in warm_text]),
])
print(f"    first (cold) text run total: {text_rows[0][0]:.0f} ms   (LLM {text_rows[0][1].get('LLM reply (Ollama)', 0):.0f} ms)")

warm_voice = voice_rows[1:]
table(f"VOICE check-in, WARM (runs 2-{N}, n={len(warm_voice)})", [
    ("speech-to-text (Whisper base)", [r[0] for r in warm_voice]),
    *[(s, v) for s, v in stage_series(warm_voice, 2).items()],
    ("send -> reply, total", [r[1] for r in warm_voice]),
    ("VOICE TOTAL = transcribe + send->reply", [r[0] + r[1] for r in warm_voice]),
])
print(f"    first (cold) voice run: transcribe {voice_rows[0][0]:.0f} ms (includes loading Whisper if not already loaded), "
      f"send->reply {voice_rows[0][1]:.0f} ms")

fails_t = sum(1 for r in text_rows if r[2])
fails_v = sum(1 for r in voice_rows if r[3])
print(f"\n  runs where Ollama failed and the scripted fallback was shown: text {fails_t}/{N}, voice {fails_v}/{N}")
correct = sum(1 for r, s in zip(voice_rows, [SPOKEN[i % len(SPOKEN)] for i in range(N)]) if r[5].strip(" .").lower() == s.lower())
print(f"  Whisper transcripts exactly equal to the spoken sentence (ignoring case/final full stop): {correct}/{N}")
print("\nCaveats: text-to-speech, not human speech; offscreen window (no real painting); one machine; "
      "Ollama model was loaded from disk on the first run only.")
sys.stdout.flush()
os._exit(0)
