"""Local AI settings dialog - server URL, chat model, vision model, test connection."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

from ai_client import PRESETS, check_connection
from data import COLORS as C
from workers import FnWorker


class AISettingsDialog(QDialog):
    def __init__(self, ai_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Local AI settings")
        self.setMinimumWidth(420)
        self.result_config = None
        self._worker = None

        layout = QVBoxLayout(self)

        title = QLabel("Local AI settings")
        title.setStyleSheet(f"font-size:18px; font-weight:700; color:{C['primary']};")
        layout.addWidget(title)

        info = QLabel("Connect to a local AI server running on your machine. No data leaves your device.")
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{C['text_muted']}; font-size:12px;")
        layout.addWidget(info)

        preset_row = QHBoxLayout()
        for key, preset in PRESETS.items():
            btn = QPushButton(preset["label"])
            btn.setObjectName("ghost")
            btn.clicked.connect(lambda _c, k=key: self._apply_preset(k))
            preset_row.addWidget(btn)
        layout.addLayout(preset_row)

        layout.addWidget(QLabel("Server URL"))
        self.base_url_input = QLineEdit(ai_config["base_url"])
        layout.addWidget(self.base_url_input)

        layout.addWidget(QLabel("Chat model"))
        self.chat_model_input = QLineEdit(ai_config["chat_model"])
        layout.addWidget(self.chat_model_input)

        layout.addWidget(QLabel("Vision model (for meal analysis)"))
        self.vision_model_input = QLineEdit(ai_config["vision_model"])
        layout.addWidget(self.vision_model_input)

        self.provider = ai_config["provider"]

        self.test_result_label = QLabel("")
        self.test_result_label.setWordWrap(True)
        layout.addWidget(self.test_result_label)

        btn_row = QHBoxLayout()
        test_btn = QPushButton("Test connection")
        test_btn.setObjectName("ghost")
        test_btn.clicked.connect(self._test_connection)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("ghost")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save settings")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(test_btn)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _apply_preset(self, key):
        preset = PRESETS[key]
        self.provider = "openai" if key == "custom" else key
        self.base_url_input.setText(preset["base_url"])
        self.chat_model_input.setText(preset["chat_model"])
        self.vision_model_input.setText(preset["vision_model"])

    def _current_config(self):
        return {
            "provider": self.provider,
            "base_url": self.base_url_input.text().strip(),
            "chat_model": self.chat_model_input.text().strip(),
            "vision_model": self.vision_model_input.text().strip(),
        }

    def _test_connection(self):
        self.test_result_label.setText("Testing…")
        self.test_result_label.setStyleSheet(f"color:{C['text_muted']};")
        config = self._current_config()
        self._worker = FnWorker(lambda: check_connection(config))
        self._worker.finished_ok.connect(self._on_test_ok)
        self._worker.failed.connect(self._on_test_fail)
        self._worker.start()

    def _on_test_ok(self, models):
        self.test_result_label.setStyleSheet(f"color:{C['sage']};")
        self.test_result_label.setText(f"✓ Connected! {len(models)} model(s) available.")

    def _on_test_fail(self, message):
        self.test_result_label.setStyleSheet("color:#E07A5F;")
        self.test_result_label.setText(f"✗ {message}")

    def _save(self):
        self.result_config = self._current_config()
        self.accept()
