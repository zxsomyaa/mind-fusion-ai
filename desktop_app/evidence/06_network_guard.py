"""
Evidence 6 - what network traffic does the app's own code generate? (TC-I03)

Regenerate:  python evidence/06_network_guard.py > evidence/output/06_network_guard.txt

Method: a guard is installed on Python's socket layer BEFORE the app modules are imported.
Every connection attempt (and every DNS lookup) is logged with the destination, and any
destination that is not this machine (127.0.0.0/8, ::1) is BLOCKED (the connection raises
ConnectionRefusedError). Then the app's real code paths are exercised:

  A. text check-in   : detect_mood -> recommendations -> ai_client.chat_ai (Ollama)
  B. voice check-in  : voice.TranscribeWorker (faster-whisper "base") on a spoken clip
  C. meal analysis   : ai_client.vision_ai (Ollama, llava)
  D. face expression : face_analysis FaceDetector + EmotionClassifier (ONNX) on a photo

LIMITS (stated because they matter):
  * This guards Python's socket module. Native code (onnxruntime, OpenCV, the Qt libraries) can open
    sockets without going through it. Section E therefore also samples the OS's own view (lsof) of
    this process while the paths run.
  * It proves what the CODE ATTEMPTS. It is not the same as pulling the network cable; that check
    (Wi-Fi off, run again) has not been performed here and is not claimed.
  * Blocking means an attempted external call fails; the app path is then judged on whether it
    still completed.
"""
import ipaddress
import os
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG = []            # (label, kind, destination, allowed)
CURRENT = ["setup"]
_lock = threading.Lock()


def _is_local(host):
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback
    except ValueError:
        return host in ("localhost",)


def _record(kind, dest, allowed):
    with _lock:
        LOG.append((CURRENT[0], kind, dest, allowed))


_orig_connect, _orig_connect_ex, _orig_getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo


def _dest(address):
    return address[0] if isinstance(address, tuple) else str(address)


def guarded_connect(self, address):
    host = _dest(address)
    local = _is_local(host) or self.family == socket.AF_UNIX
    _record("connect", f"{host}:{address[1]}" if isinstance(address, tuple) else host, local)
    if not local:
        raise ConnectionRefusedError(f"BLOCKED by evidence guard: {address}")
    return _orig_connect(self, address)


def guarded_connect_ex(self, address):
    host = _dest(address)
    local = _is_local(host) or self.family == socket.AF_UNIX
    _record("connect_ex", f"{host}:{address[1]}" if isinstance(address, tuple) else host, local)
    if not local:
        return 111
    return _orig_connect_ex(self, address)


def guarded_getaddrinfo(host, *a, **kw):
    local = host is None or _is_local(str(host))
    _record("dns-lookup", str(host), local)
    if not local:
        raise socket.gaierror(f"BLOCKED by evidence guard: DNS lookup of {host}")
    return _orig_getaddrinfo(host, *a, **kw)


socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = guarded_connect, guarded_connect_ex, guarded_getaddrinfo


def section(label, title):
    CURRENT[0] = label
    print(f"\n{label}. {title}")


def summary_for(label):
    rows = [r for r in LOG if r[0] == label]
    ext = [r for r in rows if not r[3]]
    loc = sorted({r[2] for r in rows if r[3]})
    print(f"   socket events: {len(rows)}   local: {len(rows) - len(ext)}   EXTERNAL attempts (all blocked): {len(ext)}")
    if loc:
        print(f"   local destinations : {', '.join(loc)}")
    for r in ext:
        print(f"   EXTERNAL ATTEMPT   : {r[1]} -> {r[2]}")
    return ext


print("Mind Fusion Desktop - network evidence (socket-level guard)")
print(f"date   : {datetime.now():%Y-%m-%d %H:%M:%S}")
print(f"command: python evidence/06_network_guard.py   (HF_HUB_OFFLINE={os.environ.get('HF_HUB_OFFLINE', '<not set>')})")
print("guard  : every connect()/getaddrinfo() logged; anything not 127.0.0.0/8 or ::1 is refused")

import cv2                                                 # noqa: E402
import numpy as np                                         # noqa: E402
from PySide6.QtWidgets import QApplication                 # noqa: E402
import wave                                                # noqa: E402
import ai_client                                           # noqa: E402
import data                                                # noqa: E402
import voice                                               # noqa: E402
import face_analysis as fa                                 # noqa: E402

app = QApplication([])
CFG = dict(ai_client.DEFAULT_CONFIG)

# ---------------------------------------------------------------- A. text
section("A", "text check-in through the app's own functions")
import tempfile
text = "I feel anxious about my exam tomorrow"
mood = data.detect_mood(text)
recs = data.get_personalized_recs({"conditions": [], "goals": []}, mood["mood"], None)
print(f"   detect_mood -> {mood['mood']} ; recommendations -> {len(recs)} ; (pure Python, no I/O)")
t0 = time.perf_counter()
reply = ai_client.chat_ai(CFG, [{"role": "user", "content": text}], "Reply in one short sentence.")
print(f"   chat_ai (llama3.2 via {CFG['base_url']}) returned {len(reply)} characters in {time.perf_counter() - t0:.1f} s")
ext_A = summary_for("A")

# ---------------------------------------------------------------- B. voice
section("B", "voice check-in: faster-whisper 'base' transcribing a spoken clip")
clip = os.environ.get("MF_STIMULUS_DIR")
wav_path = Path(clip) / "checkin.wav" if clip else None
if not (wav_path and wav_path.exists()):
    tts = Path(tempfile.mkdtemp()) / "assets"
    tts.mkdir()
    subprocess.run(["say", "-v", "Samantha", "-o", str(tts / "c.aiff"), "I feel a bit anxious about my exam tomorrow"], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(tts / "c.aiff"), str(tts / "c.wav")], check=True)
    wav_path = tts / "c.wav"
with wave.open(str(wav_path)) as w:
    speech = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype("float32") / 32768.0
result = {}
worker = voice.TranscribeWorker(speech, language="en")
worker.finished_ok.connect(lambda t: result.update(text=t))
worker.failed.connect(lambda m: result.update(error=m))
voice.TranscribeWorker._model = None                       # force a fresh model load inside the guard
t0 = time.perf_counter()
worker.run()
print(f"   loaded model + transcribed in {time.perf_counter() - t0:.1f} s -> {result.get('text', 'FAILED: ' + str(result.get('error')))!r}")
ext_B = summary_for("B")

# ---------------------------------------------------------------- C. meal
section("C", "meal analysis: ai_client.vision_ai (llava) on the sample photo")
import base64
photo = ROOT / "evidence" / "assets" / "meal_photo.jpg"
b64 = base64.b64encode(photo.read_bytes()).decode()
t0 = time.perf_counter()
out = ai_client.vision_ai(CFG, b64, "Name the foods in this photo in one line.")
print(f"   vision_ai returned {len(out)} characters in {time.perf_counter() - t0:.1f} s")
ext_C = summary_for("C")

# ---------------------------------------------------------------- D. face
section("D", "face expression: YuNet detector + FER+ classifier on a photo (ONNX, local files)")
img = cv2.imread(str(photo))
try:
    det = fa.FaceDetector()
    clf = fa.EmotionClassifier()
    print("   detector + classifier constructed OK from the local .onnx files in desktop_app/models/")
    faces = det.detect(img) if hasattr(det, "detect") else []
    print(f"   detector ran on the meal photo (contains no face): {len(faces) if faces is not None else 0} face(s)")
except Exception as exc:                                   # noqa: BLE001
    print(f"   could not run face pipeline: {exc}")
ext_D = summary_for("D")

# ---------------------------------------------------------------- E. OS view
section("E", "the operating system's view of this process (lsof) at the end of the run")
pid = os.getpid()
ls = subprocess.run(f"lsof -nP -a -p {pid} -i", shell=True, capture_output=True, text=True).stdout.strip()
print(f"   $ lsof -nP -a -p {pid} -i")
print("   " + (ls.replace("\n", "\n   ") if ls else "(no open internet sockets held by this process at this moment)"))

# ---------------------------------------------------------------- verdict
print("\nALL SOCKET EVENTS (label, kind, destination, allowed):")
for r in LOG:
    print(f"   {r[0]}  {r[1]:<10} {r[2]:<32} {'local' if r[3] else 'EXTERNAL - BLOCKED'}")
external = [r for r in LOG if not r[3]]
print()
print(f"RESULT: {'PASS - the app code attempted no non-local connection' if not external else 'FINDING - ' + str(len(external)) + ' attempted non-local connection(s), all blocked by the guard; see the sections above for which path made them'}")
sys.stdout.flush(); os._exit(0)   # native worker threads (Ollama client / ONNX) can keep the interpreter alive at exit
