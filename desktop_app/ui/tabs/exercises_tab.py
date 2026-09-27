"""Guided breathing / grounding exercises - a grid of cards that open a
step-by-step countdown timer dialog - plus a way to log an exercise you did
yourself, and a list of what you've logged recently."""

from datetime import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QDialog, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from data import COLORS as C, EXERCISES
from ui.exercise_dialog import log_manual_exercise
from ui.widgets import Card, pill

RECENT_LIMIT = 6


class ExerciseDialog(QDialog):
    def __init__(self, exercise, db, user_id, parent=None):
        super().__init__(parent)
        self.exercise = exercise
        self.db = db
        self.user_id = user_id
        self._logged_this_session = False
        self.setWindowTitle(exercise["name"])
        self.setMinimumWidth(360)

        self.phase = "ready"  # ready | running | complete
        self.cycle_num = 1
        self.step_idx = 0
        self.time_left = exercise["steps"][0]["duration"]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        self.layout_ = QVBoxLayout(self)
        self._render_ready()

    def _clear(self):
        while self.layout_.count():
            item = self.layout_.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _render_ready(self):
        self._clear()
        header = QLabel(f"{self.exercise['emoji']}  {self.exercise['name']}")
        header.setStyleSheet(f"font-size:18px; font-weight:700; color:{C['primary']};")
        self.layout_.addWidget(header)

        desc = QLabel(self.exercise["description"])
        desc.setWordWrap(True)
        self.layout_.addWidget(desc)

        info = QLabel(f"{self.exercise['cycles']} cycle(s) · {self.exercise['duration_label']}")
        self.layout_.addWidget(info)

        begin_btn = QPushButton("Begin")
        begin_btn.clicked.connect(self._start)
        self.layout_.addWidget(begin_btn)

    def _start(self):
        self.phase = "running"
        self.step_idx = 0
        self.cycle_num = 1
        self.time_left = self.exercise["steps"][0]["duration"]
        self._logged_this_session = False
        self._render_running()
        self.timer.start(1000)

    def _render_running(self):
        self._clear()
        step = self.exercise["steps"][self.step_idx]

        self.countdown_label = QLabel(str(self.time_left))
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet(f"font-size:36px; font-weight:700; color:{C['primary']};")
        self.layout_.addWidget(self.countdown_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, step["duration"])
        self.progress_bar.setValue(step["duration"] - self.time_left)
        self.progress_bar.setTextVisible(False)
        self.layout_.addWidget(self.progress_bar)

        self.step_label = QLabel(step["label"])
        self.step_label.setStyleSheet("font-size:16px; font-weight:600;")
        self.layout_.addWidget(self.step_label)

        self.hint_label = QLabel(step["hint"])
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(f"color:{C['text_muted']};")
        self.layout_.addWidget(self.hint_label)

        if self.exercise["cycles"] > 1:
            cycle_label = QLabel(f"Cycle {self.cycle_num} of {self.exercise['cycles']}")
            cycle_label.setStyleSheet(f"color:{C['text_muted']}; font-size:11px;")
            self.layout_.addWidget(cycle_label)

        btn_row = QVBoxLayout()
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.clicked.connect(self._toggle_pause)
        stop_btn = QPushButton("Stop")
        stop_btn.setObjectName("ghost")
        stop_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.pause_btn)
        btn_row.addWidget(stop_btn)
        self.layout_.addLayout(btn_row)

    def _toggle_pause(self):
        if self.timer.isActive():
            self.timer.stop()
            self.pause_btn.setText("▶ Resume")
        else:
            self.timer.start(1000)
            self.pause_btn.setText("⏸ Pause")

    def _tick(self):
        self.time_left -= 1
        if self.time_left <= 0:
            steps = self.exercise["steps"]
            next_step = self.step_idx + 1
            if next_step < len(steps):
                self.step_idx = next_step
                self.time_left = steps[next_step]["duration"]
            else:
                next_cycle = self.cycle_num + 1
                if next_cycle <= self.exercise["cycles"]:
                    self.cycle_num = next_cycle
                    self.step_idx = 0
                    self.time_left = steps[0]["duration"]
                else:
                    self.timer.stop()
                    self._render_complete()
                    return
            self._render_running()
        else:
            self.countdown_label.setText(str(self.time_left))
            step = self.exercise["steps"][self.step_idx]
            self.progress_bar.setValue(step["duration"] - self.time_left)

    def _render_complete(self):
        self.phase = "complete"
        if not self._logged_this_session:
            self.db.add_exercise_session(self.user_id, self.exercise["id"], self.exercise["name"])
            self._logged_this_session = True
        self._clear()
        emoji = QLabel("🌿")
        emoji.setAlignment(Qt.AlignCenter)
        emoji.setStyleSheet("font-size:44px;")
        self.layout_.addWidget(emoji)

        title = QLabel("Well done")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size:20px; font-weight:700; color:{C['sage']};")
        self.layout_.addWidget(title)

        msg = QLabel("You just gave your nervous system a real gift. Take a moment to notice how you feel.")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignCenter)
        self.layout_.addWidget(msg)

        again_btn = QPushButton("Do it again")
        again_btn.setObjectName("ghost")
        again_btn.clicked.connect(self._start)
        done_btn = QPushButton("Done ✓")
        done_btn.clicked.connect(self.accept)
        self.layout_.addWidget(again_btn)
        self.layout_.addWidget(done_btn)


class ExercisesTab(QWidget):
    def __init__(self, db, user_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id

        # scrolls, so the cards keep their natural size however many exercises
        # there are (squeezed into a fixed height they clipped their buttons)
        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page.addWidget(scroll)
        inner = QWidget()
        scroll.setWidget(inner)
        outer = QVBoxLayout(inner)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("Guided exercises")
        title.setStyleSheet(f"font-size:22px; font-weight:700; color:{C['primary']};")
        titles.addWidget(title)
        subtitle = QLabel("Breathing and grounding practices for real moments.")
        subtitle.setStyleSheet(f"color:{C['text_muted']};")
        titles.addWidget(subtitle)
        head.addLayout(titles, stretch=1)
        self.add_exercise_btn = QPushButton("＋  Add exercise")
        self.add_exercise_btn.setObjectName("ghost")
        self.add_exercise_btn.setCursor(Qt.PointingHandCursor)
        self.add_exercise_btn.setToolTip("Log something you did yourself - a walk, a workout, a class")
        self.add_exercise_btn.clicked.connect(self._log_exercise)
        head.addWidget(self.add_exercise_btn, alignment=Qt.AlignTop)
        outer.addLayout(head)

        self.logged_label = QLabel("")
        self.logged_label.setStyleSheet(f"color:{C['sage']}; font-size:13px; font-weight:600;")
        self.logged_label.setVisible(False)
        outer.addWidget(self.logged_label)

        grid = QGridLayout()
        grid.setSpacing(16)
        for i, ex in enumerate(EXERCISES):
            grid.addWidget(self._exercise_card(ex), i // 2, i % 2)
        outer.addLayout(grid)

        recent_head = QLabel("Recently logged")
        recent_head.setStyleSheet("font-size:15px; font-weight:700;")
        outer.addWidget(recent_head)
        self.recent_layout = QVBoxLayout()
        self.recent_layout.setSpacing(8)
        outer.addLayout(self.recent_layout)
        outer.addStretch()
        self.refresh_recent()

    # -- logging your own exercise ------------------------------------------------------

    def _log_exercise(self):
        entry = log_manual_exercise(self.db, self.user_id, self)
        if entry:
            self.logged_label.setText(f"✓ Logged {entry['name']} · {entry['minutes']} min")
            self.logged_label.setVisible(True)
            self.refresh_recent()

    def _begin(self, exercise):
        ExerciseDialog(exercise, self.db, self.user_id, self).exec()
        self.refresh_recent()                 # a finished guided session shows up too

    def refresh_recent(self):
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            widget = item.widget()              # look it up once: after setParent(None) the item no longer has it
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        sessions = self.db.get_exercise_history(self.user_id)[:RECENT_LIMIT]
        if not sessions:
            empty = QLabel("Nothing yet - finish a guided exercise below, or add one you did yourself.")
            empty.setStyleSheet(f"color:{C['text_muted']}; font-size:12px;")
            self.recent_layout.addWidget(empty)
            return
        for x in sessions:
            box = QWidget()
            box.setObjectName("flowHost")
            row = QHBoxLayout(box)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            when = datetime.fromtimestamp(x["timestamp"] / 1000).strftime("%a %d %b, %H:%M")
            label = QLabel(f"<b>{x['exercise_name']}</b>  <span style='color:{C['text_muted']};'>{when}"
                           + (f"  ·  {x['duration_min']} min" if x.get("duration_min") else "") + "</span>")
            label.setStyleSheet("font-size:12px;")
            row.addWidget(label, stretch=1)
            if x.get("source") == "manual":
                row.addWidget(pill("added by you"))
            delete = QPushButton("×")
            delete.setObjectName("tinyBtn")
            delete.setToolTip("Remove this entry")
            delete.setCursor(Qt.PointingHandCursor)
            delete.clicked.connect(lambda _c, sid=x["id"]: self._delete(sid))
            row.addWidget(delete)
            self.recent_layout.addWidget(box)

    def _delete(self, session_id):
        self.db.delete_exercise_session(session_id)
        self.refresh_recent()

    def _exercise_card(self, exercise):
        card = Card()
        header = QLabel(f"{exercise['emoji']}  {exercise['name']}")
        header.setStyleSheet(f"font-size:15px; font-weight:700; color:{C['primary']};")
        card.layout_.addWidget(header)

        tagline = QLabel(exercise["tagline"])
        tagline.setStyleSheet(f"color:{C['sage']}; font-size:12px; font-weight:600;")
        card.layout_.addWidget(tagline)

        desc = QLabel(exercise["description"])
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{C['text_muted']}; font-size:12px;")
        card.layout_.addWidget(desc)

        duration = QLabel(f"⏱ {exercise['duration_label']}")
        card.layout_.addWidget(duration)

        begin_btn = QPushButton("Begin")
        begin_btn.clicked.connect(lambda: self._begin(exercise))
        card.layout_.addWidget(begin_btn)
        return card
