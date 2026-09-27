"""Insights tab - your mood, sleep, habits, meals and exercise at a glance.

Pick a time range (7 / 30 / 90 days / all time) and everything below follows
it: headline numbers compared with the previous period, a few plain-language
findings, charts, and lists. The calculations live in insights_logic.py and
nutrition_logic.py; the charts are drawn by ui/charts.py.
"""

from collections import Counter
from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import insights_logic as il
from data import COLORS as C, HABITS, MOODS
from nutrition_logic import balance_tone, summarise_meals
from ui.charts import BarChart, DonutChart, LineChart, MoodCalendar
from ui.exercise_dialog import log_manual_exercise
from ui.widgets import CollapsibleSection, Card, StatCard, pill, rgba, score_badge, tone_colour

MAX_SLEEP_BARS = 30
MAX_CALORIE_BARS = 14
MAX_TREND_POINTS = 60
CALENDAR_WEEKS = 12
MACRO_COLOURS = {"protein": "#E07A5F", "carbs": "#D4A017", "fat": "#748CAB", "fibre": "#52B788"}
MACRO_NAMES = {"protein": "Protein", "carbs": "Carbs", "fat": "Fat", "fibre": "Fibre"}
TONE_TINTS = {"good": "82, 183, 136", "warn": "224, 122, 95", "gentle": "116, 140, 171", "neutral": "168, 155, 144"}


def _heading(text):
    label = QLabel(text)
    label.setStyleSheet("font-size:15px; font-weight:700;")
    return label


def _muted(text, size=12):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(f"color:{C['text_muted']}; font-size:{size}px;")
    return label


def _card(title, subtitle=None):
    card = Card()
    card.layout_.setAlignment(Qt.AlignTop)     # cards in a row share a height; keep content at the top
    card.layout_.addWidget(_heading(title))
    if subtitle:
        card.layout_.addWidget(_muted(subtitle))
    return card


def _row(*items):
    """Cards side by side. Each item is (widget, stretch)."""
    row = QHBoxLayout()
    row.setSpacing(16)
    for widget, stretch in items:
        row.addWidget(widget, stretch=stretch)
    return row


def _progress_row(label, fraction, value_text, colour):
    """A label, a thin bar, and a value - used for habit rates and exercise counts."""
    box = QWidget()
    box.setObjectName("flowHost")              # transparent, so it doesn't paint the page colour inside a card
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    top = QHBoxLayout()
    top.addWidget(QLabel(label), stretch=1)
    value = QLabel(value_text)
    value.setStyleSheet(f"color:{C['text_muted']}; font-size:12px;")
    top.addWidget(value)
    layout.addLayout(top)
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(round(max(0.0, min(1.0, fraction)) * 100))
    bar.setTextVisible(False)
    bar.setFixedHeight(8)
    bar.setStyleSheet(
        f"QProgressBar {{ height:8px; border-radius:4px; background:{C['border']}; }}"
        f"QProgressBar::chunk {{ border-radius:4px; background:{colour}; }}"
    )
    layout.addWidget(bar)
    return box


def _compact_row(label, fraction, value_text, colour):
    """One line: label, a slim bar, and a short value. For dense lists."""
    box = QWidget()
    box.setObjectName("flowHost")
    row = QHBoxLayout(box)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)
    name = QLabel(label)
    name.setStyleSheet("font-size:12px;")
    name.setFixedWidth(150)
    row.addWidget(name)
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(round(max(0.0, min(1.0, fraction)) * 100))
    bar.setTextVisible(False)
    bar.setFixedHeight(6)
    bar.setStyleSheet(
        f"QProgressBar {{ height:6px; border-radius:3px; background:{C['border']}; }}"
        f"QProgressBar::chunk {{ border-radius:3px; background:{colour}; }}"
    )
    row.addWidget(bar, stretch=1)
    value = QLabel(value_text)
    value.setStyleSheet(f"color:{C['text_muted']}; font-size:11px;")
    value.setFixedWidth(44)
    value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    row.addWidget(value)
    return box


class InsightsTab(QWidget):
    def __init__(self, db, user_id, profile=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self.profile = profile or {}
        self.range_days = 30          # None = all time
        # which dropdown sections are open is remembered between visits
        self._open_sections = {k for k in db.get_setting("insights_open", "").split(",") if k}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        outer.addWidget(self.scroll)
        self.refresh()

    # -- data -----------------------------------------------------------------------------

    def _collect(self):
        return {
            "moods": self.db.get_mood_history(self.user_id),
            "sleep": self.db.get_sleep_history(self.user_id, limit=100000),
            "habit_days": self.db.get_all_habit_days(self.user_id),
            "meals": self.db.get_nutrition_history(self.user_id),
            "exercises": self.db.get_exercise_history(self.user_id),
            "journal": self.db.get_journal_entries(self.user_id),
        }

    def set_range(self, days):
        self.range_days = days
        self.refresh()

    # -- page --------------------------------------------------------------------------------

    def refresh(self):
        old_scroll = self.scroll.verticalScrollBar().value()
        today = date.today()
        data = self._collect()
        start, end = il.window(self.range_days, today)
        current = il.slice_data(data, start, end)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(16)
        layout.addLayout(self._header())

        if not any(data[key] for key in ("moods", "sleep", "meals", "exercises", "journal")) \
                and not any(data["habit_days"].values()):
            layout.addWidget(self._empty_state())
            layout.addStretch()
            self.scroll.setWidget(page)
            return

        # headline numbers
        kpis = QHBoxLayout()
        kpis.setSpacing(14)
        for card in il.kpi_cards(data, self.range_days, today):
            kpis.addWidget(StatCard(card["label"], card["value"], card["delta"], card["sign"]))
        layout.addLayout(kpis)

        layout.addWidget(self._noticed_card(data, today))

        layout.addLayout(_row((self._mood_mix_card(current), 4), (self._trend_card(current), 6)))
        layout.addWidget(self._calendar_card(data["moods"], today, current))
        layout.addWidget(self._nutrition_card(current))
        side = QWidget()                      # habits and journal stack beside the (taller) exercises card
        side.setObjectName("flowHost")
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(16)
        side_layout.addWidget(self._habits_card(current, start, end, today))
        side_layout.addWidget(self._journal_card(current))
        side_layout.addStretch()
        layout.addLayout(_row((self._exercise_card(current), 6), (side, 4)))
        layout.addStretch()

        self.scroll.setWidget(page)
        # context=self.scroll: Qt skips the call if the scroll area is gone by then
        QTimer.singleShot(0, self.scroll, lambda: self.scroll.verticalScrollBar().setValue(old_scroll))

    def _section(self, key, title, summary):
        """A dropdown whose open/closed state is remembered."""
        section = CollapsibleSection(title, summary, open_=key in self._open_sections)
        section.toggled.connect(lambda is_open, k=key: self._remember_section(k, is_open))
        return section

    def _remember_section(self, key, is_open):
        (self._open_sections.add if is_open else self._open_sections.discard)(key)
        self.db.set_setting("insights_open", ",".join(sorted(self._open_sections)))

    def _header(self):
        row = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("Insights")
        title.setStyleSheet(f"font-size:24px; font-weight:800; color:{C['primary']};")
        titles.addWidget(title)
        label = next(text for text, days in il.RANGES if days == self.range_days)
        note = f"Last {label}" if self.range_days else "Everything you've logged"
        if self.range_days:
            note += f" - compared with the {self.range_days} days before"
        titles.addWidget(_muted(note, 13))
        row.addLayout(titles, stretch=1)

        self.range_group = QButtonGroup(self)
        self.range_group.setExclusive(True)
        self.range_buttons = {}
        for text, days in il.RANGES:
            btn = QPushButton(text)
            btn.setObjectName("rangePill")
            btn.setCheckable(True)
            btn.setChecked(days == self.range_days)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _c, d=days: self.set_range(d))
            self.range_group.addButton(btn)
            self.range_buttons[days] = btn
            row.addWidget(btn, alignment=Qt.AlignTop)
        return row

    def _empty_state(self):
        card = Card()
        card.layout_.setAlignment(Qt.AlignCenter)
        for text, style in (
            ("✨", "font-size:44px;"),
            ("Your insights will appear here", "font-size:18px; font-weight:700;"),
        ):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(style)
            card.layout_.addWidget(lbl)
        hint = _muted("Check in with how you feel, log your sleep, tick a habit or analyse a meal - "
                      "patterns start to show after a few days.", 13)
        hint.setAlignment(Qt.AlignCenter)
        card.layout_.addWidget(hint)
        return card

    # -- sections -------------------------------------------------------------------------------

    def _noticed_card(self, data, today):
        card = _card("What we noticed")
        # findings look at everything you've logged, not just the chosen range, so a
        # short range doesn't hide a pattern that is clear over a longer stretch
        findings = il.find_insights(data, today)
        if not findings:
            card.layout_.addWidget(_muted("Keep checking in - once you have about a week of moods (and some "
                                          "sleep or exercise logged) we'll point out patterns here.", 13))
            return card
        for emoji, tone, text in findings:
            line = QLabel(f"<span style='font-size:16px;'>{emoji}</span>&nbsp;&nbsp;{text}")
            line.setWordWrap(True)
            line.setStyleSheet(
                f"background:rgba({TONE_TINTS.get(tone, TONE_TINTS['neutral'])}, 0.16); "
                f"border-radius:12px; padding:10px 14px; font-size:13px;"
            )
            card.layout_.addWidget(line)
        card.layout_.addWidget(_muted("These are patterns in your own data, not medical advice or proof of cause.", 11))
        return card

    def _mood_mix_card(self, current):
        counts = Counter(m["mood"] for m in current["moods"])
        card = _card("Mood mix")
        donut = DonutChart()
        segments = [(MOODS[m]["label"], n, MOODS[m]["color"]) for m, n in counts.most_common() if m in MOODS]
        total = sum(n for _l, n, _c in segments)
        donut.set_segments(segments, str(total), "check-ins")
        card.layout_.addWidget(donut)
        if not segments:
            card.layout_.addWidget(_muted("No check-ins in this period."))
        return card

    def _trend_card(self, current):
        card = _card("Mood trend", "Daily average: 'positive' means every check-in that day was a good one")
        scores = il.daily_scores(current["moods"])[-MAX_TREND_POINTS:]
        chart = LineChart()
        chart.set_points([
            {"x": d.toordinal(), "y": s, "label": f"{d:%d %b}",
             "tooltip": f"{d:%a %d %b}: " + ("mostly positive" if s >= 0.34 else "mostly heavy" if s <= -0.34 else "mixed")}
            for d, s in scores
        ])
        card.layout_.addWidget(chart)
        return card

    def _calendar_card(self, all_moods, today, current):
        card = _card(f"Mood calendar - last {CALENDAR_WEEKS} weeks", "Hover a day for details")
        row = QHBoxLayout()
        row.setSpacing(28)
        calendar = MoodCalendar()
        calendar.set_grid(il.calendar_grid(all_moods, today, CALENDAR_WEEKS))
        row.addWidget(calendar)

        streaks = il.checkin_streaks(all_moods, today)
        stats = QVBoxLayout()
        stats.setSpacing(14)
        for value, caption in ((streaks["current"], "day streak"), (streaks["longest"], "longest streak"),
                               (streaks["days"], "days checked in")):
            pair = QVBoxLayout()
            pair.setSpacing(0)                     # keep each caption right under its number
            number = QLabel(str(value))
            number.setStyleSheet("font-size:26px; font-weight:800;")
            pair.addWidget(number)
            pair.addWidget(_muted(caption))
            stats.addLayout(pair)
        stats.addStretch()
        row.addLayout(stats)
        row.addStretch()
        card.layout_.addLayout(row)

        shares = il.weekday_positive_share(all_moods)
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        rated = [(share, name) for name, (share, count) in zip(names, shares) if share is not None and count >= 3]
        summary = "Check in on a few more days to see this"
        if len(rated) >= 2 and max(rated)[0] - min(rated)[0] >= 15:
            summary = f"Brightest: {max(rated)[1]} ({max(rated)[0]}%)  ·  Toughest: {min(rated)[1]} ({min(rated)[0]}%)"
        section = self._section("weekday", "Best days of the week", summary)
        section.add_widget(_muted("Share of your check-ins that were positive, by weekday (all your data)"))
        bars = []
        for name, (share, count) in zip(names, shares):
            if share is None:
                bars.append({"label": name, "value": 0, "tooltip": f"{name}: no check-ins yet"})
                continue
            colour = C["sage"] if share >= 60 else "#D9B26F" if share >= 40 else "#E07A5F"
            bars.append({"label": name, "value": share, "colour": colour,
                         "tooltip": f"{name}: {share}% positive ({count} check-in{'s' if count != 1 else ''})"})
        chart = BarChart()
        chart.set_data(bars, y_max=100, empty_text="Check in on a few days to see this")
        section.add_widget(chart)
        card.layout_.addWidget(section)

        sleep_widgets, sleep_summary = self._sleep_content(current)
        sleep = self._section("sleep", "Sleep", sleep_summary)
        for widget in sleep_widgets:
            sleep.add_widget(widget)
        card.layout_.addWidget(sleep)
        return card

    def _sleep_content(self, current):
        """(widgets, one-line summary) for the Sleep dropdown inside the calendar card."""
        rows = sorted(current["sleep"], key=lambda r: r["day"])[-MAX_SLEEP_BARS:]
        widgets = [_muted("Bars in the green band met the 7-9 hour target")]
        chart = BarChart()
        bars = []
        for r in rows:
            d = date.fromisoformat(r["day"])
            quality = f", quality {r['quality']}/5" if r.get("quality") else ""
            bars.append({
                "label": f"{d:%d}" if len(rows) > 8 else f"{d:%d %b}", "value": r["hours"],
                "tooltip": f"{d:%a %d %b}: {r['hours']:g} h{quality}",
                "colour": C["sage"] if 7 <= r["hours"] <= 9 else C["primary_light"],
            })
        chart.set_data(bars, y_max=max(10, nice_ceiling(max((r['hours'] for r in rows), default=0))),
                       band=(7, 9), empty_text="Log your sleep on the Today page to see it here")
        widgets.append(chart)
        if not rows:
            return widgets, "Log your sleep on the Today page"
        hours = [r["hours"] for r in rows]
        on_target = sum(1 for h in hours if 7 <= h <= 9)
        summary = f"Average {sum(hours) / len(hours):.1f} h  ·  {on_target} of {len(hours)} nights on target"
        widgets.append(_muted(f"{summary}  ·  best {max(hours):g} h"))
        return widgets, summary

    def _habits_card(self, current, start, end, today):
        """A deliberately small card: one line per habit."""
        card = Card()
        card.layout_.setAlignment(Qt.AlignTop)
        card.layout_.setContentsMargins(16, 12, 16, 12)
        card.layout_.setSpacing(6)
        card.layout_.addWidget(_heading("Habit consistency"))
        habit_days = current["habit_days"]
        wanted = list(dict.fromkeys(list(self.profile.get("habits", [])) + [h for h, d in habit_days.items() if d]))
        if start is None:
            all_days = [d for days in habit_days.values() for d in days]
            span = max(1, (today - min(all_days)).days + 1) if all_days else 1
        else:
            span = (end - start).days + 1
        rows = []
        for hid in wanted:
            meta = next((h for h in HABITS if h["id"] == hid), None)
            if meta is None:
                continue
            ticked = len(habit_days.get(hid, set()))
            rows.append((ticked / span, f"{meta['emoji']}  {meta['label']}", f"{ticked}/{span}"))
        if not rows:
            card.layout_.addWidget(_muted("Tick habits on the Today page to see them here."))
            return card
        for fraction, label, value in sorted(rows, reverse=True)[:5]:
            colour = C["sage"] if fraction >= 0.6 else C["primary_light"] if fraction >= 0.3 else "#D4A017"
            card.layout_.addWidget(_compact_row(label, fraction, value, colour))
        card.layout_.addWidget(_muted(f"Days ticked, out of the last {span}" if start is not None else "Days ticked", 11))
        return card

    def _nutrition_card(self, current):
        meals = current["meals"]
        summary = summarise_meals(meals)
        subtitle = None
        if meals:
            bits = [f"{summary['count']} meal{'s' if summary['count'] != 1 else ''}"]
            if summary["avg_balance"] is not None:
                bits.append(f"average balance {summary['avg_balance']}/10")
            subtitle = "  ·  ".join(bits)
        card = _card("Nutrition", subtitle)
        if not meals:
            card.layout_.addWidget(_muted("No meals analysed in this period - analyse one on the Nutrition page."))
        for meal in meals[:5]:
            row = QHBoxLayout()
            row.setSpacing(12)
            score = meal.get("balance_score")
            row.addWidget(score_badge(str(score) if score is not None else "?", balance_tone(score), size=38))
            text = QVBoxLayout()
            text.setSpacing(1)
            name = QLabel(meal.get("foods") or "Meal")
            name.setStyleSheet("font-weight:700;")
            text.addWidget(name)
            bits = [datetime.fromtimestamp(meal["timestamp"] / 1000).strftime("%a %d %b")]
            if meal.get("calories_estimate") is not None:
                bits.append(f"{meal['calories_estimate']} kcal")
            text.addWidget(_muted("  ·  ".join(bits)))
            row.addLayout(text, stretch=1)
            card.layout_.addLayout(row)

        calories_chart, calories_summary = self._calories_content(current)
        calories = self._section("calories", "Calories per day", calories_summary)
        calories.add_widget(_muted("Estimated from the meals you analysed"))
        calories.add_widget(calories_chart)
        card.layout_.addWidget(calories)

        macros_chart, macros_summary = self._macros_content(current)
        macros = self._section("macros", "Macros", macros_summary)
        macros.add_widget(_muted("Average per meal, by weight"))
        macros.add_widget(macros_chart)
        card.layout_.addWidget(macros)
        return card

    def _calories_content(self, current):
        """(chart, one-line summary) for the Calories per day dropdown."""
        per_day = {}
        for m in current["meals"]:
            if m.get("calories_estimate") is not None:
                d = il.to_date(m["timestamp"])
                total, n = per_day.get(d, (0, 0))
                per_day[d] = (total + m["calories_estimate"], n + 1)
        days = sorted(per_day)[-MAX_CALORIE_BARS:]
        chart = BarChart()
        chart.set_data(
            [{"label": f"{d:%d %b}" if len(days) <= 8 else f"{d:%d}", "value": per_day[d][0],
              "tooltip": f"{d:%a %d %b}: {per_day[d][0]} kcal from {per_day[d][1]} meal{'s' if per_day[d][1] != 1 else ''}"}
             for d in days],
            colour=C["primary_light"], empty_text="Analyse a meal on the Nutrition page to see calories here")
        if not days:
            return chart, "No calorie data yet"
        average = round(sum(per_day[d][0] for d in days) / len(days))
        return chart, f"Average {average:,} kcal on days you logged meals"

    def _macros_content(self, current):
        """(donut, one-line summary) for the Macros dropdown."""
        with_macros = [m for m in current["meals"] if any(m.get(k) is not None for k in MACRO_NAMES)]
        donut = DonutChart()
        if not with_macros:
            donut.set_segments([])
            return donut, "Saved with each meal you analyse from now on"
        averages = {k: sum(m[k] for m in with_macros if m.get(k) is not None) /
                    max(1, sum(1 for m in with_macros if m.get(k) is not None)) for k in MACRO_NAMES}
        total = sum(averages.values())
        donut.set_segments([(MACRO_NAMES[k], round(averages[k], 1), MACRO_COLOURS[k]) for k in MACRO_NAMES],
                           f"{total:.0f} g", "per meal", unit=" g")
        return donut, "Per meal: " + "  ·  ".join(f"{averages[k]:.0f} g {MACRO_NAMES[k].lower()}" for k in MACRO_NAMES)

    def _exercise_card(self, current):
        sessions = current["exercises"]
        minutes = sum(x["duration_min"] for x in sessions if x.get("duration_min"))
        subtitle = f"{len(sessions)} session{'s' if len(sessions) != 1 else ''}"
        if minutes:
            subtitle += f"  ·  {minutes} min logged"
        card = Card()
        card.layout_.setAlignment(Qt.AlignTop)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(_heading("Exercises"))
        titles.addWidget(_muted(subtitle))
        head.addLayout(titles, stretch=1)
        self.add_exercise_btn = QPushButton("＋  Add exercise")
        self.add_exercise_btn.setObjectName("ghost")
        self.add_exercise_btn.setCursor(Qt.PointingHandCursor)
        self.add_exercise_btn.setToolTip("Log something you did outside the app - a walk, a workout, a class")
        self.add_exercise_btn.clicked.connect(self._add_exercise)
        head.addWidget(self.add_exercise_btn, alignment=Qt.AlignTop)
        card.layout_.addLayout(head)

        if not sessions:
            card.layout_.addWidget(_muted("Finish a guided exercise, or add one you did yourself."))
            return card
        counts = Counter(x["exercise_name"] for x in sessions)
        top = counts.most_common(1)[0][1]
        for name, n in counts.most_common(5):
            card.layout_.addWidget(_progress_row(name, n / top, f"{n}x", C["primary"]))

        card.layout_.addWidget(_muted("Recent", 11))
        for x in sessions[:5]:
            row = QHBoxLayout()
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
            delete.clicked.connect(lambda _c, sid=x["id"]: self._delete_exercise(sid))
            row.addWidget(delete)
            card.layout_.addLayout(row)
        return card

    def _add_exercise(self):
        if log_manual_exercise(self.db, self.user_id, self):
            self.refresh()

    def _delete_exercise(self, session_id):
        self.db.delete_exercise_session(session_id)
        self.refresh()

    def _journal_card(self, current):
        entries = current["journal"]
        card = _card("Journal", f"{len(entries)} entr{'ies' if len(entries) != 1 else 'y'} written")
        if not entries:
            card.layout_.addWidget(_muted("Write in your journal to see a summary here."))
            return card
        words = sum(len(e["text"].split()) for e in entries)
        card.layout_.addWidget(_muted(f"About {words:,} words  ·  averaging {round(words / len(entries))} per entry", 13))
        moods = Counter(e["mood"] for e in entries if e.get("mood") in MOODS)
        if moods:
            card.layout_.addWidget(_muted("How your entries felt:"))
            host = QHBoxLayout()
            host.setSpacing(8)
            for mood, n in moods.most_common(4):
                meta = MOODS[mood]
                host.addWidget(pill(f"{meta['emoji']} {meta['label']} · {n}", rgba(meta["color"], 0.18), meta["color"]))
            host.addStretch()
            card.layout_.addLayout(host)
        return card


def nice_ceiling(value):
    """Top of a sleep chart: the next whole hour above the longest night (never below 10)."""
    return max(10, int(value) + 1)
