"""
Evidence 5 - a voice check-in leaves no audio file on disk.

Regenerate:  python evidence/05_no_audio_file.py > evidence/output/05_no_audio_file.txt

1. STATIC   : search the voice code for anything that could write audio to disk.
2. DYNAMIC  : run the app's real record -> transcribe path, snapshotting the places a
              temp file would land (system temp dirs, the project folder, the model
              cache) before and after, and list everything that appeared.
3. CONTROL  : plant a real .wav in the temp dir and show the same scan flags it -
              otherwise "found nothing" could just mean "the check can't see".

There is no microphone in this environment, so the speech is macOS text-to-speech.
It is fed to the app's real MicRecorder through a stand-in for the sound-card driver
(sounddevice.InputStream), which delivers audio in blocks exactly like the real one.
The TTS clip itself is written under evidence/assets/tts/ - test input, excluded
from the scan and listed at the end.
"""
import os
import subprocess
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np                                        # noqa: E402
from datetime import datetime                             # noqa: E402
from PySide6.QtWidgets import QApplication                # noqa: E402

AUDIO_EXT = {".wav", ".aiff", ".aif", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".webm", ".caf", ".aac", ".wma", ".raw", ".pcm"}
MAGIC = [(b"RIFF", 0), (b"FORM", 0), (b"ID3", 0), (b"OggS", 0), (b"fLaC", 0), (b"ftyp", 4)]
TTS_DIR = Path(os.environ.get("MF_STIMULUS_DIR", ROOT / "evidence" / "assets" / "tts"))   # test INPUT (text-to-speech clip); keep it outside every scanned folder
SKIP_DIRS = {"venv", ".git", "__pycache__", "node_modules", "assets"}          # 'assets' = the test-input TTS clip

print("Mind Fusion Desktop - voice check-in leaves no audio file")
print(f"date   : {datetime.now():%Y-%m-%d %H:%M:%S}")
print(f"command: python evidence/05_no_audio_file.py")
print()

# ------------------------------------------------------------------ 1. static
print("1. STATIC - can the voice code write a file at all?")
patterns = r"open\(|\.write\(|\.save\(|wave\.|soundfile|tempfile|NamedTemporary|to_file|shutil|os\.remove|Path\(.*\)\.write"
for rel in ("voice.py",):
    cmd = ["grep", "-nE", patterns, str(ROOT / rel)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    print(f"   $ grep -nE '{patterns}' {rel}")
    print("   " + (out.replace("\n", "\n   ") if out else "(no matches - voice.py contains no file-writing calls)"))
chat_out = subprocess.run(["grep", "-nE", r"recorder|Recorder|Transcribe|whisper", str(ROOT / "ui/tabs/chat_tab.py")], capture_output=True, text=True).stdout
print("   how chat_tab.py uses the recording (every reference):")
print("   " + chat_out.strip().replace("\n", "\n   "))
print("   voice.py stores captured audio in a Python list of numpy arrays (self._frames) and returns one numpy array.")
print()

# ------------------------------------------------------------------ scanning helpers
def roots():
    home = Path.home()
    cands = [Path(tempfile.gettempdir()), Path("/tmp"), Path("/var/tmp"), ROOT, home / ".cache"]
    seen, out = set(), []
    for p in cands:
        try:
            rp = p.resolve()
        except OSError:
            continue
        if rp.exists() and rp not in seen:
            seen.add(rp)
            out.append(rp)
    return out


def snapshot():
    snap = {}
    for root in roots():
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                p = os.path.join(dirpath, name)
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                snap[p] = (st.st_size, st.st_mtime_ns)
    return snap


def looks_like_audio(path):
    if Path(path).suffix.lower() in AUDIO_EXT:
        return "extension"
    try:
        with open(path, "rb") as f:
            head = f.read(12)
    except OSError:
        return None
    for magic, offset in MAGIC:
        if head[offset:offset + len(magic)] == magic:
            return "file header"
    return None


def diff(before, after):
    new = sorted(p for p in after if p not in before)
    changed = sorted(p for p in after if p in before and after[p] != before[p])
    return new, changed


def report(new, changed, label):
    audio = [(p, looks_like_audio(p)) for p in new + changed]
    audio = [(p, why) for p, why in audio if why]
    print(f"   files created : {len(new)}")
    print(f"   files modified: {len(changed)}")
    for p in new + changed:
        kind = "NEW     " if p in new else "modified"
        print(f"     {kind} {p}   ({after_snap[p][0]} bytes)" if p in after_snap else f"     {kind} {p}")
    print(f"   AUDIO FILES among them (by extension or file header): {len(audio)}")
    for p, why in audio:
        print(f"     -> {p}  (detected by {why})")
    return audio


print("2. DYNAMIC - snapshot -> real record/transcribe path -> snapshot")
print("   places scanned (skipping venv/.git/__pycache__/evidence assets):")
for r in roots():
    print(f"     {r}")

# make the test speech (TTS) - test INPUT, kept outside the scan
TTS_DIR.mkdir(parents=True, exist_ok=True)
SENTENCE = "I feel a bit anxious about my exam tomorrow"
aiff, wav_path = TTS_DIR / "checkin.aiff", TTS_DIR / "checkin.wav"
subprocess.run(["say", "-v", "Samantha", "-o", str(aiff), SENTENCE], check=True)
subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(wav_path)], check=True)
with wave.open(str(wav_path)) as w:
    speech = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype("float32") / 32768.0
    rate = w.getframerate()
print(f"   test speech: '{SENTENCE}'  ({len(speech) / rate:.1f} s, {rate} Hz) - macOS text-to-speech, in {TTS_DIR}/")

app = QApplication([])
import voice                                              # noqa: E402  (the app's real module)


class FakeInputStream:
    """Stands in for the sound card: like sounddevice.InputStream it calls back with
    blocks of samples on its own thread while 'recording'."""
    def __init__(self, samplerate, channels, dtype, callback):
        self.callback, self._stop = callback, threading.Event()
        self._thread = None

    def start(self):
        def feed():
            block = 1024
            for i in range(0, len(speech), block):
                if self._stop.is_set():
                    break
                self.callback(speech[i:i + block].reshape(-1, 1), block, None, None)
                time.sleep(0.0005)
        self._thread = threading.Thread(target=feed, daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread:
            self._thread.join()
        self._stop.set()

    def close(self):
        pass


before = snapshot()
print(f"   snapshot before: {len(before):,} files")
recorder = voice.MicRecorder()
with mock.patch.object(voice.sd, "InputStream", FakeInputStream):
    recorder.start()                                       # the app's real MicRecorder
    time.sleep(0.5)
    audio = recorder.stop()
print(f"   MicRecorder.stop() returned: {type(audio).__name__} {audio.dtype} with {audio.size:,} samples "
      f"({audio.size / voice.SAMPLE_RATE:.1f} s) - held in memory")

result = {}
worker = voice.TranscribeWorker(audio, language="en")
worker.finished_ok.connect(lambda t: result.update(text=t))
worker.failed.connect(lambda m: result.update(error=m))
worker.run()                                               # the app's real transcription code (same thread, for a simple demo)
print(f"   transcript: {result.get('text', result.get('error'))!r}")

after_snap = snapshot()
print(f"   snapshot after : {len(after_snap):,} files")
new, changed = diff(before, after_snap)
audio_found = report(new, changed, "voice check-in")
print(f"   RESULT: {'PASS - no audio file was written' if not audio_found else 'FAIL - audio file(s) found'}")
print()

# ------------------------------------------------------------------ 3. control
print("3. CONTROL - prove the scan can see an audio file when one exists")
before_c = snapshot()
control = Path(tempfile.gettempdir()) / "control_check.wav"
with wave.open(str(control), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
    w.writeframes((speech[:8000] * 32767).astype("<i2").tobytes())
after_snap = snapshot()
new_c, changed_c = diff(before_c, after_snap)
found_c = report(new_c, changed_c, "control")
print(f"   CONTROL RESULT: {'scan detected the planted .wav, so an empty result above is meaningful' if found_c else 'scan FAILED to detect a planted audio file - result above is not trustworthy'}")
control.unlink()
print()
print(f"test-input files (excluded from the scan on purpose): {[str(p) for p in sorted(TTS_DIR.iterdir())]}")
print(f"system temp dir: {tempfile.gettempdir()}")
print("$ ls -la " + tempfile.gettempdir() + " | grep -iE '\\.(wav|aiff?|mp3|m4a|flac|ogg|webm|caf)$'")
listing = subprocess.run(f"ls -la '{tempfile.gettempdir()}' | grep -iE '\\.(wav|aiff?|mp3|m4a|flac|ogg|webm|caf)$'", shell=True, capture_output=True, text=True).stdout
print(listing.strip() or "(no audio files in the system temp directory)")
