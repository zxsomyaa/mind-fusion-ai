"""
Local speech-to-text, using faster-whisper (a local, open-weight Whisper
model - matches the "Speech-to-Text (Whisper)" box in the architecture
diagram). Nothing here calls a cloud API - the model file downloads once
from Hugging Face on first use and then runs entirely on-device.
"""

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QThread, Signal

SAMPLE_RATE = 16000


class MicRecorder:
    """Records microphone audio into memory between start() and stop()."""

    def __init__(self):
        self._frames = []
        self._stream = None

    def start(self):
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=self._on_audio
        )
        self._stream.start()

    def _on_audio(self, indata, _frames, _time, _status):
        self._frames.append(indata.copy())

    def stop(self):
        """Stops recording and returns the captured audio as a 1D float32 array."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._frames:
            return np.zeros((0,), dtype="float32")
        return np.concatenate(self._frames, axis=0).flatten()


class TranscribeWorker(QThread):
    """Runs Whisper transcription on a background thread. The model itself
    is loaded once and cached on the class, since loading it takes a few
    seconds and every tab that uses voice input shares the same model."""

    finished_ok = Signal(str)
    failed = Signal(str)

    _model = None

    def __init__(self, audio, language=None, parent=None):
        super().__init__(parent)
        self.audio = audio
        self.language = language   # ISO code such as 'hi', or None to detect it

    def run(self):
        try:
            if self.audio.size == 0:
                self.finished_ok.emit("")
                return

            if TranscribeWorker._model is None:
                from faster_whisper import WhisperModel
                TranscribeWorker._model = WhisperModel("base", device="cpu", compute_type="int8")

            segments, _info = TranscribeWorker._model.transcribe(self.audio, language=self.language)
            text = " ".join(segment.text.strip() for segment in segments)
            self.finished_ok.emit(text.strip())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
