"""
Small QThread helpers so calls to the local AI server (or SQLite writes that
might briefly block) never freeze the GUI. Qt does not allow touching widgets
from a background thread, so every worker only emits signals - the widget
itself updates from the main thread when a signal fires.
"""

from PySide6.QtCore import QThread, Signal


class FnWorker(QThread):
    """Runs any zero-argument callable on a background thread.
    Emits `finished_ok(result)` on success or `failed(str)` on exception."""

    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            result = self.fn()
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI, not swallowed
            self.failed.emit(str(exc))
        else:
            self.finished_ok.emit(result)


class PullWorker(QThread):
    """Streams model-download progress from Ollama's /api/pull endpoint."""

    progress = Signal(dict)
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, ai_config, model_name, parent=None):
        super().__init__(parent)
        self.ai_config = ai_config
        self.model_name = model_name

    def run(self):
        from ai_client import pull_model

        try:
            pull_model(self.ai_config, self.model_name, on_progress=self.progress.emit)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        else:
            self.finished_ok.emit()
