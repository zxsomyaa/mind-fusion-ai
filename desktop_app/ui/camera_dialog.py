"""
Live camera window for the mood check.

The camera stays on while this window is open and you see yourself (mirrored,
like a selfie camera) with a green box around your face. "Analyse mood" reads
a few frames, averages the expression, and shows the result; "Log this mood"
sends it back to the Chat tab. Closing the window turns the camera off.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from data import COLORS as C, MOODS
from face_analysis import CameraWorker

VIEW_SIZE = (640, 480)


class CameraDialog(QDialog):
    mood_selected = Signal(dict)   # the analysis result the user chose to log

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Camera mood check")
        self.setModal(True)
        self._worker = None
        self._started = False
        self._result = None
        self._face_visible = None
        self._camera_ready = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("How are you looking today?")
        title.setStyleSheet(f"font-size:18px; font-weight:700; color:{C['primary']};")
        layout.addWidget(title)
        hint = QLabel("Face the camera in good light. Nothing is recorded or sent anywhere - "
                      "the picture is analysed on your computer and then discarded.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{C['text_muted']}; font-size:12px;")
        layout.addWidget(hint)

        self.view = QLabel("Starting camera…")
        self.view.setObjectName("cameraView")
        self.view.setFixedSize(*VIEW_SIZE)
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setStyleSheet("background:#000; color:#DDD; border-radius:12px; font-size:14px;")
        layout.addWidget(self.view, alignment=Qt.AlignCenter)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(f"color:{C['text_muted']};")
        layout.addWidget(self.status)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setVisible(False)
        layout.addWidget(self.result_label)

        buttons = QHBoxLayout()
        self.switch_btn = QPushButton("⟲  Switch camera")
        self.switch_btn.setObjectName("ghost")
        self.switch_btn.setToolTip("Use a different camera (e.g. if this is your iPhone)")
        self.switch_btn.clicked.connect(self._switch_camera)
        self.analyse_btn = QPushButton("Analyse mood")
        self.analyse_btn.clicked.connect(self._analyse)
        self.log_btn = QPushButton("Log this mood")
        self.log_btn.clicked.connect(self._log_mood)
        self.log_btn.setVisible(False)
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("ghost")
        self.close_btn.clicked.connect(self.reject)
        buttons.addWidget(self.switch_btn)
        buttons.addStretch()
        buttons.addWidget(self.analyse_btn)
        buttons.addWidget(self.log_btn)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

        self.switch_btn.setEnabled(False)
        self.analyse_btn.setEnabled(False)

    # -- lifecycle ---------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        if not self._started:
            self._started = True
            self._worker = CameraWorker(self)
            self._worker.frame_ready.connect(self._on_frame)
            self._worker.status.connect(self._on_status)
            self._worker.camera_changed.connect(self._on_camera_changed)
            self._worker.result.connect(self._on_result)
            self._worker.capture_failed.connect(self._on_capture_failed)
            self._worker.failed.connect(self._on_failed)
            self._worker.start()

    def done(self, result_code):
        """Every way of closing the window (Close button, Esc, the X) ends
        up here, so the camera is always switched off."""
        self._stop_worker()
        super().done(result_code)

    def _stop_worker(self):
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(4000)
            self._worker = None

    # -- worker signals ------------------------------------------------------

    def _on_frame(self, image, face_visible):
        pixmap = QPixmap.fromImage(image).scaled(self.view.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
        self.view.setPixmap(pixmap)
        if face_visible != self._face_visible:
            self._face_visible = face_visible
            if self._result is None:
                self._set_status(
                    "Face found - hold still, then press Analyse mood." if face_visible
                    else "Looking for your face…",
                    good=face_visible,
                )

    def _on_status(self, text):
        self._set_status(text)

    def _on_camera_changed(self, index):
        self._camera_ready = True
        self.switch_btn.setEnabled(True)
        self.analyse_btn.setEnabled(True)
        self.switch_btn.setText(f"⟲  Switch camera (now #{index + 1})")

    def _on_result(self, result):
        self._result = result
        meta = MOODS[result["mood"]]
        self.result_label.setText(
            f"{meta['emoji']}  Looks like <b>{meta['label']}</b> "
            f"<span style='color:{C['text_muted']}'>(expression: {result['fer_label']}, "
            f"{round(result['confidence'] * 100)}% sure, from {result['frames']} frames)</span>"
        )
        self.result_label.setStyleSheet(
            f"background:{meta['bg']}; color:#3D2C1E; border-radius:10px; padding:10px 14px; font-size:14px;"
        )
        self.result_label.setVisible(True)
        self.log_btn.setVisible(True)
        self.analyse_btn.setText("Analyse again")
        self.analyse_btn.setEnabled(True)
        self._set_status("")

    def _on_capture_failed(self, message):
        self.analyse_btn.setEnabled(True)
        self._set_status(message, error=True)

    def _on_failed(self, message):
        self._camera_ready = False
        self.analyse_btn.setEnabled(False)
        self.switch_btn.setEnabled(False)
        self.view.setText("Camera unavailable")
        self._set_status(message, error=True)

    # -- buttons ---------------------------------------------------------------

    def _analyse(self):
        if self._worker is None:
            return
        self._result = None
        self.result_label.setVisible(False)
        self.log_btn.setVisible(False)
        self.analyse_btn.setEnabled(False)
        self._worker.request_capture()

    def _switch_camera(self):
        if self._worker is None:
            return
        self._face_visible = None
        self.switch_btn.setEnabled(False)
        self.analyse_btn.setEnabled(False)
        self._worker.switch_camera()

    def _log_mood(self):
        if self._result is not None:
            self.mood_selected.emit(self._result)
        self.accept()

    def _set_status(self, text, good=False, error=False):
        colour = "#E07A5F" if error else (C["sage"] if good else C["text_muted"])
        self.status.setStyleSheet(f"color:{colour};")
        self.status.setText(text)
