"""Today tab - the landing page: greeting, check-in streak, quick mood
check-in, daily affirmation, and a suggestion based on the latest mood."""

from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox, QButtonGroup, QCheckBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from data import AFFIRMATIONS, COLORS as C, HABITS, MOODS, get_personalized_recs
from ui.flow_layout import FlowLayout
from ui.widgets import Card


def greeting_for(hour):
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def current_streak(days, today=None):
    """Consecutive days with activity, counting back from today. If nothing
    has happened yet today, the streak is still alive as long as yesterday
    had activity - it only breaks once a whole day has been skipped."""
    today = today or date.today()
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


class HomeTab(QWidget):
    def __init__(self, db, user_id, user_name, profile, go_to, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self.user_name = user_name
        self.profile = profile
        self.go_to = go_to  # callable(tab_key) -> switches the main tab

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        outer.addWidget(self.scroll)
        self.refresh()

    def refresh(self):
        old_scroll = self.scroll.verticalScrollBar().value()
        now = datetime.now()
        days = self.db.get_activity_days(self.user_id)
        streak = current_streak(days)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel(f"{greeting_for(now.hour)}, {self.user_name}")
        title.setStyleSheet(f"font-size:24px; font-weight:700; color:{C['primary']};")
        layout.addWidget(title)
        date_lbl = QLabel(now.strftime("%A, %d %B"))
        date_lbl.setStyleSheet(f"color:{C['text_muted']};")
        layout.addWidget(date_lbl)

        # -- stat cards ---------------------------------------------------
        stats = QHBoxLayout()
        stats.setSpacing(14)
        streak_text = f"{streak} day{'s' if streak != 1 else ''}"
        for value, caption in (
            (f"🔥 {streak_text}", "check-in streak"),
            (str(self.db.count_rows("mood_history", self.user_id)), "mood check-ins"),
            (str(self.db.count_rows("journal_entries", self.user_id)), "journal entries"),
            (str(self.db.count_rows("nutrition_history", self.user_id)), "meals analysed"),
            (str(self.db.count_rows("exercise_sessions", self.user_id)), "exercises done"),
        ):
            stats.addWidget(self._stat_card(value, caption))
        layout.addLayout(stats)

        # -- quick mood check-in ----------------------------------------------
        checkin = Card()
        head = QLabel("How are you feeling right now?")
        head.setStyleSheet("font-size:15px; font-weight:700;")
        checkin.layout_.addWidget(head)
        row = QWidget()
        row.setObjectName("flowHost")
        flow = FlowLayout(row, h_spacing=8, v_spacing=8)
        for key, meta in MOODS.items():
            btn = QPushButton(f"{meta['emoji']}  {meta['label']}")
            btn.setObjectName("ghost")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _c, k=key: self._log_mood(k))
            flow.addWidget(btn)
        checkin.layout_.addWidget(row)
        self.checkin_status = QLabel("")
        self.checkin_status.setStyleSheet(f"color:{C['sage']};")
        self.checkin_status.setVisible(False)
        checkin.layout_.addWidget(self.checkin_status)
        layout.addWidget(checkin)

        habits_card = self._habits_card()
        if habits_card:
            layout.addWidget(habits_card)
        layout.addWidget(self._sleep_card())

        # -- suggestion for the latest mood ----------------------------------
        history = self.db.get_mood_history(self.user_id)
        if history:
            last_mood = history[-1]["mood"]
            recs = get_personalized_recs(self.profile, last_mood)
            if recs:
                rec = recs[0]
                meta = MOODS.get(last_mood, {})
                card = Card()
                if last_mood in rec["moods"]:
                    lead_text = f"Because you last felt {meta.get('label', last_mood).lower()}"
                else:
                    lead_text = "Suggested for your goals"
                lead = QLabel(lead_text)
                lead.setStyleSheet(f"color:{C['text_muted']}; font-size:11px; font-weight:600;")
                card.layout_.addWidget(lead)
                name = QLabel(f"{rec['emoji']}  {rec['title']}")
                name.setStyleSheet(f"font-size:16px; font-weight:700; color:{C['primary']};")
                card.layout_.addWidget(name)
                body = QLabel(rec["body"])
                body.setWordWrap(True)
                card.layout_.addWidget(body)
                layout.addWidget(card)

        # -- daily affirmation -------------------------------------------------
        aff = AFFIRMATIONS[now.timetuple().tm_yday % len(AFFIRMATIONS)]
        aff_card = Card()
        aff_lead = QLabel("Today's affirmation")
        aff_lead.setStyleSheet(f"color:{C['text_muted']}; font-size:11px; font-weight:600;")
        aff_card.layout_.addWidget(aff_lead)
        aff_text = QLabel(f'"{aff["text"]}"')
        aff_text.setWordWrap(True)
        aff_text.setStyleSheet("font-size:17px; font-style:italic;")
        aff_card.layout_.addWidget(aff_text)
        layout.addWidget(aff_card)

        # -- quick actions -------------------------------------------------------
        actions = QHBoxLayout()
        actions.setSpacing(12)
        for label, key in (("💬  Talk it through", "chat"), ("📓  Write in journal", "journal"),
                           ("🧘  Do an exercise", "exercises"), ("🥗  Log a meal", "nutrition")):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _c, k=key: self.go_to(k))
            actions.addWidget(btn)
        layout.addLayout(actions)

        layout.addStretch()
        self.scroll.setWidget(inner)
        # context=self.scroll: Qt skips the call if the scroll area is gone by then
        QTimer.singleShot(0, self.scroll, lambda: self.scroll.verticalScrollBar().setValue(old_scroll))

    # -- habits ------------------------------------------------------------

    def _habits_card(self):
        habit_ids = [h for h in self.profile.get("habits", []) if any(x["id"] == h for x in HABITS)]
        if not habit_ids:
            return None
        today = date.today()
        done = self.db.get_habits_done(self.user_id, today)

        card = Card()
        top = QHBoxLayout()
        head = QLabel("Today's habits")
        head.setStyleSheet("font-size:15px; font-weight:700;")
        top.addWidget(head)
        top.addStretch()
        self.habit_progress = QLabel(f"{len(done & set(habit_ids))} of {len(habit_ids)} done")
        self.habit_progress.setStyleSheet(f"color:{C['text_muted']};")
        top.addWidget(self.habit_progress)
        card.layout_.addLayout(top)

        self._habit_boxes = {}
        for hid in habit_ids:
            meta = next(x for x in HABITS if x["id"] == hid)
            row = QHBoxLayout()
            box = QCheckBox(f"{meta['emoji']}  {meta['label']}")
            box.setChecked(hid in done)
            box.setCursor(Qt.PointingHandCursor)
            box.toggled.connect(lambda _checked, h=hid: self._toggle_habit(h))
            row.addWidget(box, stretch=1)
            streak = current_streak(self.db.get_habit_days(self.user_id, hid))
            streak_lbl = QLabel(f"🔥 {streak}" if streak else "")
            streak_lbl.setStyleSheet(f"color:{C['text_muted']}; font-size:12px;")
            streak_lbl.setToolTip("Days in a row")
            row.addWidget(streak_lbl)
            card.layout_.addLayout(row)
            self._habit_boxes[hid] = (box, streak_lbl)
        self._habit_ids = habit_ids
        return card

    def _toggle_habit(self, habit_id):
        self.db.toggle_habit(self.user_id, habit_id, date.today())
        done = self.db.get_habits_done(self.user_id, date.today())
        self.habit_progress.setText(f"{len(done & set(self._habit_ids))} of {len(self._habit_ids)} done")
        streak = current_streak(self.db.get_habit_days(self.user_id, habit_id))
        self._habit_boxes[habit_id][1].setText(f"🔥 {streak}" if streak else "")

    # -- sleep -------------------------------------------------------------

    def _sleep_card(self):
        today = date.today()
        logged = self.db.get_sleep(self.user_id, today)

        card = Card()
        head = QLabel("How did you sleep?")
        head.setStyleSheet("font-size:15px; font-weight:700;")
        card.layout_.addWidget(head)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.sleep_hours = QDoubleSpinBox()
        self.sleep_hours.setRange(0, 14)
        self.sleep_hours.setSingleStep(0.5)
        self.sleep_hours.setDecimals(1)
        self.sleep_hours.setSuffix(" h")
        self.sleep_hours.setValue(logged["hours"] if logged else 7.5)
        self.sleep_hours.setFixedWidth(84)
        self.sleep_hours.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.sleep_hours.setAlignment(Qt.AlignCenter)
        minus = QPushButton("−")
        minus.setObjectName("stepBtn")
        minus.clicked.connect(lambda: self.sleep_hours.stepBy(-1))
        plus = QPushButton("+")
        plus.setObjectName("stepBtn")
        plus.clicked.connect(lambda: self.sleep_hours.stepBy(1))
        for w_ in (minus, self.sleep_hours, plus):
            row.addWidget(w_)
        row.addSpacing(8)

        self.sleep_quality = QButtonGroup(self)
        self.sleep_quality.setExclusive(True)
        for value, emoji in enumerate(("😫", "😕", "😐", "🙂", "😄"), start=1):
            btn = QPushButton(emoji)
            btn.setObjectName("ghost")
            btn.setCheckable(True)
            btn.setToolTip(f"Sleep quality {value}/5")
            btn.setCursor(Qt.PointingHandCursor)
            if logged and logged["quality"] == value:
                btn.setChecked(True)
            self.sleep_quality.addButton(btn, value)
            row.addWidget(btn)
        row.addStretch()
        save = QPushButton("Log sleep")
        save.clicked.connect(self._save_sleep)
        row.addWidget(save)
        card.layout_.addLayout(row)

        self.sleep_status = QLabel(
            f"Logged today: {logged['hours']:g} h" + (f" · quality {logged['quality']}/5" if logged["quality"] else "")
            if logged else "")
        self.sleep_status.setStyleSheet(f"color:{C['sage']};")
        self.sleep_status.setVisible(bool(logged))
        card.layout_.addWidget(self.sleep_status)
        return card

    def _save_sleep(self):
        quality = self.sleep_quality.checkedId()
        self.db.log_sleep(self.user_id, date.today(), self.sleep_hours.value(), quality if quality > 0 else None)
        self.sleep_status.setVisible(True)
        self.sleep_status.setText(
            f"✓ Saved: {self.sleep_hours.value():g} h" + (f" · quality {quality}/5" if quality > 0 else ""))

    def _stat_card(self, value, caption):
        card = Card()
        card.layout_.setContentsMargins(16, 14, 16, 14)
        card.layout_.setSpacing(2)
        v = QLabel(value)
        v.setAlignment(Qt.AlignCenter)
        v.setStyleSheet(f"font-size:20px; font-weight:700; color:{C['primary']};")
        c = QLabel(caption)
        c.setAlignment(Qt.AlignCenter)
        c.setStyleSheet(f"color:{C['text_muted']}; font-size:11px;")
        card.layout_.addWidget(v)
        card.layout_.addWidget(c)
        return card

    def _log_mood(self, mood_key):
        self.db.add_mood_entry(self.user_id, mood_key)
        meta = MOODS[mood_key]
        self.refresh()
        self.checkin_status.setText(f"✓ Logged: {meta['emoji']} {meta['label']}")
        self.checkin_status.setVisible(True)
