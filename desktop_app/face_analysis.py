"""
Local webcam-based facial expression detection.

The architecture diagram calls for DeepFace, but DeepFace depends on
TensorFlow, which has no build for Python 3.14 yet (confirmed - `pip install
tensorflow` fails outright on this interpreter). This uses the same idea
with dependencies that do work here: two small local ONNX models run
through onnxruntime/OpenCV's DNN loader - YuNet for face detection and FER+
(8 categories) for expression classification. No TensorFlow, no cloud calls.

Note: OpenCV 5.0 removed the old Haar cascade files and `CascadeClassifier`
bindings from the Python wheel entirely (confirmed against the installed
opencv-python-headless 5.0.0 - `hasattr(cv2, "CascadeClassifier")` is False,
and `cv2.data.haarcascades` is an empty directory). YuNet is OpenCV's own
replacement for exactly this job, so that's what's used here instead.

Both model files download once from their public model zoos and are cached
locally in models/, the same pattern this app already uses for pulling
Ollama models.
"""

import time
from pathlib import Path

import cv2
import numpy as np
import requests
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

MODEL_DIR = Path(__file__).parent / "models"

FACE_MODEL_PATH = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
FACE_MODEL_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)

EMOTION_MODEL_PATH = MODEL_DIR / "emotion-ferplus-8.onnx"
EMOTION_MODEL_URL = (
    "https://github.com/onnx/models/raw/main/validated/vision/"
    "body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx"
)

FER_LABELS = ["neutral", "happiness", "surprise", "sadness", "anger", "disgust", "fear", "contempt"]

# Maps the FER+ model's 8 categories onto this app's own mood taxonomy
# (see MOODS in data.py) so a camera reading feeds the same mood system
# that text-based detection and journaling already use.
FER_TO_APP_MOOD = {
    "neutral": "calm",
    "happiness": "happy",
    "surprise": "hopeful",
    "sadness": "sad",
    "anger": "stressed",
    "disgust": "stressed",
    "fear": "anxious",
    "contempt": "stressed",
}


def _download(url, dest_path, on_progress=None):
    if dest_path.exists():
        return
    MODEL_DIR.mkdir(exist_ok=True)
    tmp_path = dest_path.with_suffix(".part")
    with requests.get(url, stream=True, timeout=60) as res:
        res.raise_for_status()
        total = int(res.headers.get("content-length", 0))
        downloaded = 0
        with open(tmp_path, "wb") as f:
            for chunk in res.iter_content(chunk_size=1 << 16):
                f.write(chunk)
                downloaded += len(chunk)
                if on_progress and total:
                    on_progress(round(downloaded / total * 100))
    tmp_path.rename(dest_path)


def ensure_models_downloaded(on_progress=None):
    if not FACE_MODEL_PATH.exists():
        _download(FACE_MODEL_URL, FACE_MODEL_PATH,
                   lambda pct: on_progress and on_progress(f"Downloading face detector… {pct}%"))
    if not EMOTION_MODEL_PATH.exists():
        _download(EMOTION_MODEL_URL, EMOTION_MODEL_PATH,
                   lambda pct: on_progress and on_progress(f"Downloading emotion model… {pct}%"))


MAX_CAMERA_INDEX_TO_TRY = 3
WARMUP_FRAMES = 12           # webcams need a moment for auto-exposure to settle
FACE_SCORE_THRESHOLD = 0.6   # OpenCV's default is 0.9, which sat right on the edge: in testing a
                             # clear portrait scored 0.909, and the same face at a third of the
                             # size scored 0.898 and was rejected. 0.6 finds both.
DIM_FRAME_MEAN = 90          # below this average brightness, also try a brightened copy
LIVE_DETECT_EVERY = 2        # live view: look for a face on every 2nd frame
LIVE_MAX_FPS = 24            # cap how often the live picture is sent to the window
CAPTURE_SAMPLES = 5          # "Analyse" averages this many frames for a steadier reading
CAPTURE_TIMEOUT_S = 4.0

BLANK_HINT = (
    "The camera is sending a blank picture. If an iPhone is nearby, macOS may be using it as a "
    "Continuity Camera (\"Lock iPhone to Resume\") - try Switch camera, lock the iPhone, or allow "
    "camera access under System Settings -> Privacy & Security -> Camera."
)
NO_CAMERA_MESSAGE = "Could not access a webcam - is one connected and not in use by another app?"


def _looks_blank(frame):
    """True if a frame is (near) solid black - the signature of a camera
    session that opened but isn't actually delivering images. On macOS this
    happens both when camera permission hasn't been granted, and when
    device index 0 turns out to be an iPhone registered as a Continuity
    Camera that's currently paused (locked screen required to resume)."""
    return float(np.std(frame)) < 2.0


def _brighten(frame_bgr):
    """Gamma-lift a dark frame so the detector can see a face in a dim room."""
    table = np.array([((i / 255.0) ** 0.5) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(frame_bgr, table)


class FaceDetector:
    """YuNet face detector. Keeps the loaded model between calls (loading it
    for every frame would make a live view crawl); rebuilt only if the frame
    size changes."""

    def __init__(self, threshold=FACE_SCORE_THRESHOLD):
        self.threshold = threshold
        self._detector = None
        self._size = None

    def _run(self, frame_bgr):
        h, w = frame_bgr.shape[:2]
        if self._detector is None or self._size != (w, h):
            self._detector = cv2.FaceDetectorYN.create(str(FACE_MODEL_PATH), "", (w, h), self.threshold)
            self._size = (w, h)
        _retval, faces = self._detector.detect(frame_bgr)
        if faces is None or len(faces) == 0:
            return None
        # each row is [x, y, w, h, <5 landmark points>, confidence score]
        best = max(faces, key=lambda f: f[-1])
        x, y, fw, fh = [max(0, int(round(v))) for v in best[:4]]
        return x, y, fw, fh

    def detect(self, frame_bgr):
        """(x, y, w, h) of the most confident face, or None. In a dim frame a
        brightened copy is tried too."""
        box = self._run(frame_bgr)
        if box is None and float(frame_bgr.mean()) < DIM_FRAME_MEAN:
            box = self._run(_brighten(frame_bgr))
        return box


def detect_face_box(frame_bgr):
    """One-off convenience wrapper around FaceDetector."""
    return FaceDetector().detect(frame_bgr)


def crop_gray(frame_bgr, box):
    """Grayscale crop of the frame at the given (x, y, w, h) box, or None."""
    x, y, w, h = box
    crop = frame_bgr[y:y + h, x:x + w]
    if crop.size == 0:
        return None
    return cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)


class EmotionClassifier:
    """FER+ expression model. Loaded once, then reused for every frame."""

    def __init__(self):
        import onnxruntime as ort
        self._session = ort.InferenceSession(str(EMOTION_MODEL_PATH))
        self._input = self._session.get_inputs()[0].name

    def probs(self, face_gray):
        """Probability for each of the 8 FER_LABELS, as a numpy array."""
        face = cv2.resize(face_gray, (64, 64)).astype("float32").reshape(1, 1, 64, 64)
        scores = self._session.run(None, {self._input: face})[0][0]
        exp = np.exp(scores - np.max(scores))
        return exp / exp.sum()


def summarise_emotions(prob_list):
    """Averages several frames' probabilities (one noisy frame can't sway the
    result) and returns (fer_label, confidence, app_mood)."""
    mean = np.mean(np.stack(prob_list), axis=0)
    idx = int(np.argmax(mean))
    label = FER_LABELS[idx]
    return label, float(mean[idx]), FER_TO_APP_MOOD.get(label, "calm")


def bgr_to_qimage(frame_bgr):
    """OpenCV frame -> QImage. QImage (unlike QPixmap) is safe to build off
    the GUI thread, so the camera worker can do this itself."""
    rgb = np.ascontiguousarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    h, w, _ch = rgb.shape
    return QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888).copy()  # copy: detach from numpy


def draw_face_box(frame_bgr, box):
    """A copy of the frame with a sage-green box around the face."""
    annotated = frame_bgr.copy()
    if box:
        x, y, w, h = box
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (60, 145, 82), 3)  # BGR
    return annotated


def build_preview_image(frame_bgr, box):
    return bgr_to_qimage(draw_face_box(frame_bgr, box))


def open_camera(index):
    """Opens one camera and returns it if it delivers a real (non-blank)
    picture after warm-up. Returns (cap, reason): cap is None on failure and
    reason is 'none' (no such device) or 'blank' (device opened but black)."""
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        return None, "none"
    frame = None
    for _ in range(WARMUP_FRAMES):
        ok, f = cap.read()
        if ok and f is not None:
            frame = f
        time.sleep(0.03)
    if frame is None:
        cap.release()
        return None, "none"
    if _looks_blank(frame):
        cap.release()
        return None, "blank"
    return cap, "ok"


def open_first_working_camera(start_index=0):
    """Tries camera indices in a circle starting at start_index. Index 0 is
    not reliably the built-in camera on a Mac with Continuity Camera - it can
    be an iPhone, which returns blank frames unless it's the active device.
    Returns (cap, index, reason)."""
    saw_blank = False
    for k in range(MAX_CAMERA_INDEX_TO_TRY):
        index = (start_index + k) % MAX_CAMERA_INDEX_TO_TRY
        cap, reason = open_camera(index)
        if cap is not None:
            return cap, index, "ok"
        saw_blank = saw_blank or reason == "blank"
    return None, None, "blank" if saw_blank else "none"


class CameraWorker(QThread):
    """Runs the camera on a background thread and streams the live picture.

    Every frame is sent to the window (mirrored like a selfie camera, with a
    green box around a detected face). When asked to capture, it reads a few
    more frames, classifies the expression in each, averages them, and sends
    one result. The camera stays open until stop() is called."""

    frame_ready = Signal(object, bool)   # QImage for display, face currently visible?
    status = Signal(str)                 # progress / hints
    camera_changed = Signal(int)         # which camera index is in use
    result = Signal(dict)                # {"mood", "fer_label", "confidence", "preview", "frames"}
    capture_failed = Signal(str)
    failed = Signal(str)                 # camera unusable - live view can't continue

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._capture_requested = False
        self._switch_requested = False
        self._cap = None   # the open camera, so run() can always release it, even after an error

    # -- called from the window (GUI thread) ------------------------------
    def stop(self):
        self._running = False

    def request_capture(self):
        self._capture_requested = True

    def switch_camera(self):
        self._switch_requested = True

    # -- worker thread -------------------------------------------------------
    def run(self):
        try:
            if not FACE_MODEL_PATH.exists() or not EMOTION_MODEL_PATH.exists():
                self.status.emit("Downloading face models (first time only)…")
                ensure_models_downloaded(self.status.emit)
            detector = FaceDetector()
            classifier = EmotionClassifier()

            self.status.emit("Starting camera…")
            cap, index, reason = open_first_working_camera(0)
            if cap is None:
                self.failed.emit(BLANK_HINT if reason == "blank" else NO_CAMERA_MESSAGE)
                return
            self._cap = cap
            self.camera_changed.emit(index)
            self.status.emit("Looking for your face…")
            self._stream(cap, index, detector, classifier)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            if self._cap is not None:
                self._cap.release()
                self._cap = None

    def _stream(self, cap, index, detector, classifier):
        """The live loop. Runs until stop() is called or the camera fails."""
        frame_no, read_failures, blank_run = 0, 0, 0
        last_box, misses = None, 0
        capturing, samples, deadline = False, [], 0.0
        last_emit = 0.0

        while self._running:
            if self._switch_requested:
                self._switch_requested = False
                capturing = False
                cap.release()
                self._cap = None
                self.status.emit("Switching camera…")
                cap, index, reason = open_first_working_camera((index + 1) % MAX_CAMERA_INDEX_TO_TRY)
                if cap is None:
                    self.failed.emit(BLANK_HINT if reason == "blank" else NO_CAMERA_MESSAGE)
                    return
                self._cap = cap
                self.camera_changed.emit(index)
                last_box, misses, blank_run = None, 0, 0
                continue

            ok, frame = cap.read()
            if not ok or frame is None:
                read_failures += 1
                if read_failures > 60:
                    self.failed.emit("The camera stopped sending pictures.")
                    return
                time.sleep(0.03)
                continue
            read_failures = 0
            frame_no += 1

            if _looks_blank(frame):
                blank_run += 1
                if blank_run == 30:
                    self.status.emit(BLANK_HINT)
            else:
                blank_run = 0

            fresh_box = None
            if capturing or frame_no % LIVE_DETECT_EVERY == 0:
                fresh_box = detector.detect(frame)
                if fresh_box is not None:
                    last_box, misses = fresh_box, 0
                else:
                    misses += 1
                    if misses > 3:   # tolerate a couple of missed detections before dropping the box
                        last_box = None

            if self._capture_requested and not capturing:
                self._capture_requested = False
                capturing, samples = True, []
                deadline = time.monotonic() + CAPTURE_TIMEOUT_S
                self.status.emit("Hold still…")

            if capturing:
                if fresh_box is not None:
                    face = crop_gray(frame, fresh_box)
                    if face is not None:
                        samples.append((classifier.probs(face), frame.copy(), fresh_box))
                if len(samples) >= CAPTURE_SAMPLES or time.monotonic() > deadline:
                    capturing = False
                    self._finish_capture(samples)

            now = time.monotonic()
            if now - last_emit >= 1.0 / LIVE_MAX_FPS:
                last_emit = now
                shown = cv2.flip(draw_face_box(frame, last_box), 1)   # mirror, like a selfie camera
                self.frame_ready.emit(bgr_to_qimage(shown), last_box is not None)

    def _finish_capture(self, samples):
        if not samples:
            self.capture_failed.emit(
                "I couldn't see a face while capturing. Face the camera in good light and try again."
            )
            return
        label, confidence, app_mood = summarise_emotions([s[0] for s in samples])
        _probs, frame, box = samples[-1]
        self.result.emit({
            "mood": app_mood, "fer_label": label, "confidence": confidence,
            "preview": build_preview_image(frame, box), "frames": len(samples),
        })
