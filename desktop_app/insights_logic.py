"""
The calculations behind the Insights page - kept free of Qt so they can be
tested on their own.

`data` (used throughout) is a plain dict of everything the page shows:
    moods      [{"mood", "timestamp"}]                 timestamp = milliseconds
    sleep      [{"day": "YYYY-MM-DD", "hours", "quality"}]
    habit_days {habit_id: {date, ...}}
    meals      [{"calories_estimate", "balance_score", "protein", ..., "timestamp"}]
    exercises  [{"exercise_name", "timestamp"}]
    journal    [{"text", "timestamp"}]
"""

from datetime import date, datetime, timedelta
from statistics import mean

POSITIVE_MOODS = {"happy", "calm", "grateful", "hopeful"}
RANGES = [("7 days", 7), ("30 days", 30), ("90 days", 90), ("All time", None)]

# A pattern is only reported with at least this much data behind it - with
# less, a "correlation" is just noise.
MIN_PAIRED_DAYS = 5
MIN_DAYS_PER_GROUP = 2
MIN_DIFFERENCE_PTS = 15


def to_date(timestamp_ms):
    return datetime.fromtimestamp(timestamp_ms / 1000).date()


# -- time windows ---------------------------------------------------------------------

def window(days, today, back=0):
    """(start, end) dates, inclusive, of a `days`-long window that ended `back`
    windows ago (back=0 is the current one, back=1 the one before). days=None
    means all time: (None, today)."""
    if days is None:
        return None, today
    end = today - timedelta(days=days * back)
    return end - timedelta(days=days - 1), end


def _in_window(day, start, end):
    return (start is None or day >= start) and day <= end


def slice_data(data, start, end):
    """A copy of `data` containing only what falls between start and end."""
    def by_ts(rows):
        return [r for r in rows if _in_window(to_date(r["timestamp"]), start, end)]

    return {
        "moods": by_ts(data["moods"]),
        "meals": by_ts(data["meals"]),
        "exercises": by_ts(data["exercises"]),
        "journal": by_ts(data["journal"]),
        "sleep": [r for r in data["sleep"] if _in_window(date.fromisoformat(r["day"]), start, end)],
        "habit_days": {h: {d for d in days if _in_window(d, start, end)} for h, days in data["habit_days"].items()},
    }


# -- moods ----------------------------------------------------------------------------------

def positive_share(moods):
    """Percentage (0-100) of check-ins that were positive; None if there are none."""
    names = [m["mood"] if isinstance(m, dict) else m for m in moods]
    return round(100 * sum(1 for n in names if n in POSITIVE_MOODS) / len(names)) if names else None


def daily_positive_ratio(moods):
    """{date: share of that day's check-ins that were positive (0..1)}."""
    per_day = {}
    for m in moods:
        per_day.setdefault(to_date(m["timestamp"]), []).append(1 if m["mood"] in POSITIVE_MOODS else 0)
    return {d: sum(v) / len(v) for d, v in per_day.items()}


def daily_scores(moods):
    """[(date, score)] in date order; score runs -1 (all heavy moods) to +1 (all positive)."""
    return [(d, ratio * 2 - 1) for d, ratio in sorted(daily_positive_ratio(moods).items())]


def weekday_positive_share(moods):
    """For Monday..Sunday: (percent of that weekday's check-ins that were positive,
    number of check-ins). The percent is None for a weekday with no check-ins."""
    buckets = [[] for _ in range(7)]
    for m in moods:
        buckets[to_date(m["timestamp"]).weekday()].append(1 if m["mood"] in POSITIVE_MOODS else 0)
    return [(round(100 * sum(b) / len(b)) if b else None, len(b)) for b in buckets]


def checkin_streaks(moods, today):
    """Days you checked in: {"current": run of consecutive days ending today (or
    yesterday, if you haven't checked in yet today), "longest": your longest run,
    "days": how many different days have a check-in}."""
    days = {to_date(m["timestamp"]) for m in moods}
    cursor = today if today in days else today - timedelta(days=1)
    current = 0
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)
    longest = run = 0
    previous = None
    for d in sorted(days):
        run = run + 1 if previous is not None and (d - previous).days == 1 else 1
        longest = max(longest, run)
        previous = d
    return {"current": current, "longest": longest, "days": len(days)}


def calendar_grid(moods, today, weeks=12):
    """Columns of 7 days (Monday first) covering the last `weeks` weeks, for the
    mood calendar. Each day is {"date", "score", "count"}; days after today are None."""
    per_day = {}
    for m in moods:
        per_day.setdefault(to_date(m["timestamp"]), []).append(1 if m["mood"] in POSITIVE_MOODS else -1)
    this_monday = today - timedelta(days=today.weekday())
    grid = []
    for w in range(weeks - 1, -1, -1):
        monday = this_monday - timedelta(weeks=w)
        column = []
        for i in range(7):
            d = monday + timedelta(days=i)
            if d > today:
                column.append(None)
            else:
                marks = per_day.get(d, [])
                column.append({"date": d, "score": mean(marks) if marks else None, "count": len(marks)})
        grid.append(column)
    return grid


def pattern_message(recent_moods):
    """A gentle note when the last few check-ins lean heavy (or bright). Takes
    mood names, oldest first. Needs at least 5."""
    if len(recent_moods) < 5:
        return None
    recent = recent_moods[-7:]
    total = len(recent)
    count = lambda *names: sum(1 for m in recent if m in names) / total
    if count("stressed", "anxious") >= 0.5:
        return ("🌊", "warn", "Stress and anxiety have come up often in your recent check-ins. That's a lot to "
                "carry. It might be a good time for a calming exercise - or to talk to someone you trust.")
    if count("sad", "tired") >= 0.5:
        return ("🕯️", "gentle", "Your recent check-ins have felt heavier and more tired. Low patches come and go, "
                "but if this has lasted a while, you don't have to sit with it alone.")
    if count("happy", "grateful", "hopeful", "calm") >= 0.6:
        return ("✨", "good", "There's real warmth in your recent check-ins. Something is working - whatever "
                "you've been doing, it's worth noticing.")
    return None


# -- headline numbers -------------------------------------------------------------------------

def _kpi_values(data):
    sleep_hours = [r["hours"] for r in data["sleep"]]
    return {
        "checkins": len(data["moods"]),
        "positive": positive_share(data["moods"]),
        "sleep": round(mean(sleep_hours), 1) if sleep_hours else None,
        "habits": sum(len(days) for days in data["habit_days"].values()),
    }


def kpi_cards(data, days, today):
    """The four headline cards for the chosen range, each compared with the
    previous range of the same length (no comparison for 'All time').
    Each card: {"key", "label", "value" (text), "delta" (text or None), "sign" (+1/-1/0 or None)}."""
    start, end = window(days, today)
    now = _kpi_values(slice_data(data, start, end))
    before = None
    if days is not None:
        p_start, p_end = window(days, today, back=1)
        before = _kpi_values(slice_data(data, p_start, p_end))

    def sign(a, b):
        return (a > b) - (a < b)

    def delta(key, fmt):
        if before is None or now[key] is None or before[key] is None:
            return None, None
        diff = now[key] - before[key]
        return (fmt(diff) if diff else "no change"), sign(now[key], before[key])

    cards = []
    for key, label, value_fmt, delta_fmt in (
        ("checkins", "Mood check-ins", lambda v: str(v), lambda d: f"{d:+d}"),
        ("positive", "Positive moods", lambda v: f"{v}%", lambda d: f"{d:+d} pts"),
        ("sleep", "Average sleep", lambda v: f"{v:.1f} h", lambda d: f"{d:+.1f} h"),
        ("habits", "Habits ticked", lambda v: str(v), lambda d: f"{d:+d}"),
    ):
        d_text, d_sign = delta(key, delta_fmt)
        cards.append({
            "key": key, "label": label,
            "value": value_fmt(now[key]) if now[key] is not None else "-",
            "delta": d_text, "sign": d_sign,
        })
    return cards


# -- "what we noticed" ---------------------------------------------------------------------------

def find_insights(data, today):
    """Up to four findings as (emoji, tone, text). Deliberately modest: patterns in
    your own data, worded as such ('tends to', 'were'), never as cause and effect,
    and only reported when there is enough data and the gap is clear."""
    findings = []
    ratio = daily_positive_ratio(data["moods"])

    pattern = pattern_message([m["mood"] for m in sorted(data["moods"], key=lambda m: m["timestamp"])])
    if pattern:
        findings.append(pattern)

    # sleep vs mood on the same day
    sleep_by_day = {date.fromisoformat(r["day"]): r["hours"] for r in data["sleep"]}
    paired = [(sleep_by_day[d], ratio[d]) for d in ratio if d in sleep_by_day]
    if len(paired) >= MIN_PAIRED_DAYS:
        long_sleep = [r for h, r in paired if h >= 7]
        short_sleep = [r for h, r in paired if h < 7]
        if len(long_sleep) >= MIN_DAYS_PER_GROUP and len(short_sleep) >= MIN_DAYS_PER_GROUP:
            a, b = round(mean(long_sleep) * 100), round(mean(short_sleep) * 100)
            if a - b >= MIN_DIFFERENCE_PTS:
                findings.append(("😴", "good", f"On days you slept 7+ hours, {a}% of your check-ins were positive, "
                                 f"versus {b}% after shorter nights (across {len(paired)} days)."))

    # movement / exercise vs mood
    active_days = {to_date(e["timestamp"]) for e in data["exercises"]} | set(data["habit_days"].get("exercise", set()))
    with_move = [r for d, r in ratio.items() if d in active_days]
    without = [r for d, r in ratio.items() if d not in active_days]
    if len(with_move) >= 3 and len(without) >= 3:
        a, b = round(mean(with_move) * 100), round(mean(without) * 100)
        if a - b >= MIN_DIFFERENCE_PTS:
            findings.append(("🏃", "good", f"{a}% of your check-ins were positive on days you did an exercise session "
                             f"or ticked Regular Exercise, versus {b}% on other days."))

    # meals: this week vs the week before
    week = window(7, today)
    prev = window(7, today, back=1)
    this_scores = [m["balance_score"] for m in slice_data(data, *week)["meals"] if m.get("balance_score") is not None]
    prev_scores = [m["balance_score"] for m in slice_data(data, *prev)["meals"] if m.get("balance_score") is not None]
    if len(this_scores) >= 2 and len(prev_scores) >= 2:
        a, b = mean(this_scores), mean(prev_scores)
        if abs(a - b) >= 1:
            direction = "more balanced" if a > b else "less balanced"
            findings.append(("🥗", "good" if a > b else "gentle",
                             f"Your meals were {direction} this week (average {a:.1f}/10, up from {b:.1f})." if a > b
                             else f"Your meals were {direction} this week (average {a:.1f}/10, down from {b:.1f})."))

    # consistency
    last14 = window(14, today)
    days_checked_in = {d for d in ratio if _in_window(d, *last14)}
    if len(days_checked_in) >= 3:
        findings.append(("📅", "neutral", f"You checked in on {len(days_checked_in)} of the last 14 days."))

    return findings[:4]
