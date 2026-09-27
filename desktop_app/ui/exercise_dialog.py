"""Dialog for logging an exercise you did outside the app's guided sessions."""

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QComboBox, QDateTimeEdit, QDialog, QFormLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout,
)

from data import COLORS as C, EXERCISES

COMMON_ACTIVITIES = [
    "Walking", "Running", "Cycling", "Swimming", "Yoga", "Gym workout", "Dancing", "Stretching",
    "Hiking", "Sports", "Pilates", "Strength training",
]
MAX_MINUTES = 600


class AddExerciseDialog(QDialog):
    """After the user presses Save, `result` holds {"name", "when" (datetime), "minutes"}."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log an exercise")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.result = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        title = QLabel("Log an exercise")
        title.setStyleSheet(f"font-size:18px; font-weight:700; color:{C['primary']};")
        layout.addWidget(title)
        hint = QLabel("Add something you did outside the app - a walk, a workout, a class. "
                      "It counts towards your insights.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{C['text_muted']}; font-size:12px;")
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)

        self.activity = QComboBox()
        self.activity.setEditable(True)                     # pick from the list, or type your own
        self.activity.addItems(COMMON_ACTIVITIES + [e["name"] for e in EXERCISES])
        self.activity.setCurrentIndex(-1)
        self.activity.lineEdit().setPlaceholderText("Choose or type, e.g. Evening walk")
        form.addRow("What did you do?", self.activity)

        self.when = QDateTimeEdit(QDateTime.currentDateTime())
        self.when.setCalendarPopup(True)
        self.when.setDisplayFormat("ddd d MMM yyyy, HH:mm")
        self.when.setMaximumDateTime(QDateTime.currentDateTime())      # not in the future
        form.addRow("When?", self.when)

        self.minutes = QSpinBox()
        self.minutes.setRange(1, MAX_MINUTES)
        self.minutes.setValue(30)
        self.minutes.setSuffix(" min")
        form.addRow("How long?", self.minutes)
        layout.addLayout(form)

        self.error = QLabel("")
        self.error.setStyleSheet("color:#E07A5F; font-size:12px;")
        self.error.setVisible(False)
        layout.addWidget(self.error)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("ghost")
        cancel.clicked.connect(self.reject)
        self.save_btn = QPushButton("Save exercise")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(self.save_btn)
        layout.addLayout(buttons)

    def _save(self):
        name = self.activity.currentText().strip()
        if not name:
            self.error.setText("Enter what you did, e.g. Walking.")
            self.error.setVisible(True)
            self.activity.setFocus()
            return
        self.result = {
            "name": name[:60],
            "when": self.when.dateTime().toPython(),
            "minutes": self.minutes.value(),
        }
        self.accept()


def log_manual_exercise(db, user_id, parent=None):
    """Opens the 'Log an exercise' dialog and, if the user saves, stores the entry
    (marked as manual, backdated to the chosen time). Returns the entry, or None if cancelled."""
    dialog = AddExerciseDialog(parent)
    if not (dialog.exec() and dialog.result):
        return None
    entry = dialog.result
    db.add_exercise_session(
        user_id, "manual", entry["name"], timestamp_ms=int(entry["when"].timestamp() * 1000),
        duration_min=entry["minutes"], source="manual")
    return entry
