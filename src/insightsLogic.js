/**
 * The calculations behind the Insights page — a JS port of the desktop app's
 * insights_logic.py, kept framework-free so it's easy to reason about.
 *
 * `data` (used throughout) is a plain object of everything the page shows:
 *   moods      [{mood, timestamp}]              timestamp = milliseconds
 *   sleep      [{day: 'YYYY-MM-DD', hours, quality}]
 *   habitDays  {habitId: Set<'YYYY-MM-DD'>}
 *   meals      [{caloriesEstimate, balanceScore, protein, ..., timestamp}]
 *   exercises  [{name, timestamp}]
 *   journal    [{text, timestamp}]
 */

export const POSITIVE_MOODS = new Set(['happy', 'calm', 'grateful', 'hopeful']);
export const RANGES = [['7 days', 7], ['30 days', 30], ['90 days', 90], ['All time', null]];

const MIN_PAIRED_DAYS = 5;
const MIN_DAYS_PER_GROUP = 2;
const MIN_DIFFERENCE_PTS = 15;

const DAY_MS = 86400000;
export const toDay = (timestamp) => new Date(timestamp).toISOString().slice(0, 10);
const dayNum = (isoDay) => Math.floor(new Date(isoDay + 'T00:00:00').getTime() / DAY_MS);
const addDays = (isoDay, n) => {
  const d = new Date(isoDay + 'T00:00:00');
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
};
const mean = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length;

/** [start, end] iso days (inclusive) of a `days`-long window ending `back` windows
 * ago (back=0 is current). days=null means all time: [null, today]. */
export function window(days, today, back = 0) {
  if (days == null) return [null, today];
  const end = addDays(today, -days * back);
  return [addDays(end, -(days - 1)), end];
}

function inWindow(day, start, end) {
  return (start == null || day >= start) && day <= end;
}

/** A copy of `data` containing only what falls between start and end (iso days). */
export function sliceData(data, start, end) {
  const byTs = (rows) => rows.filter(r => inWindow(toDay(r.timestamp), start, end));
  const habitDays = {};
  for (const [h, days] of Object.entries(data.habitDays)) {
    habitDays[h] = new Set([...days].filter(d => inWindow(d, start, end)));
  }
  return {
    moods: byTs(data.moods),
    meals: byTs(data.meals),
    exercises: byTs(data.exercises),
    journal: byTs(data.journal),
    sleep: data.sleep.filter(r => inWindow(r.day, start, end)),
    habitDays,
  };
}

/** Percentage (0-100) of check-ins that were positive; null if there are none. */
export function positiveShare(moods) {
  if (!moods.length) return null;
  return Math.round(100 * moods.filter(m => POSITIVE_MOODS.has(m.mood)).length / moods.length);
}

/** {isoDay: share of that day's check-ins that were positive (0..1)} */
export function dailyPositiveRatio(moods) {
  const perDay = {};
  for (const m of moods) (perDay[toDay(m.timestamp)] ??= []).push(POSITIVE_MOODS.has(m.mood) ? 1 : 0);
  const out = {};
  for (const [d, v] of Object.entries(perDay)) out[d] = v.reduce((a, b) => a + b, 0) / v.length;
  return out;
}

/** [[isoDay, score]] in date order; score runs -1 (all heavy) to +1 (all positive). */
export function dailyScores(moods) {
  return Object.entries(dailyPositiveRatio(moods)).sort((a, b) => a[0] < b[0] ? -1 : 1).map(([d, r]) => [d, r * 2 - 1]);
}

/** For Mon..Sun: [percent positive (or null), count]. */
export function weekdayPositiveShare(moods) {
  const buckets = [[], [], [], [], [], [], []];
  for (const m of moods) {
    const jsDay = new Date(toDay(m.timestamp) + 'T00:00:00').getDay(); // 0=Sun..6=Sat
    const mon0 = (jsDay + 6) % 7; // 0=Mon..6=Sun
    buckets[mon0].push(POSITIVE_MOODS.has(m.mood) ? 1 : 0);
  }
  return buckets.map(b => [b.length ? Math.round(100 * b.reduce((a, c) => a + c, 0) / b.length) : null, b.length]);
}

export function checkinStreaks(moods, today) {
  const days = new Set(moods.map(m => toDay(m.timestamp)));
  let cursor = days.has(today) ? today : addDays(today, -1);
  let current = 0;
  while (days.has(cursor)) { current += 1; cursor = addDays(cursor, -1); }
  const sortedDays = [...days].sort();
  let longest = 0, run = 0, previous = null;
  for (const d of sortedDays) {
    run = previous !== null && dayNum(d) - dayNum(previous) === 1 ? run + 1 : 1;
    longest = Math.max(longest, run);
    previous = d;
  }
  return { current, longest, days: days.size };
}

/** Columns of 7 days (Monday first) covering the last `weeks` weeks. Each day is
 * {date, score, count} or null for days after today. */
export function calendarGrid(moods, today, weeks = 12) {
  const perDay = {};
  for (const m of moods) (perDay[toDay(m.timestamp)] ??= []).push(POSITIVE_MOODS.has(m.mood) ? 1 : -1);
  const todayJsDay = new Date(today + 'T00:00:00').getDay();
  const thisMonday = addDays(today, -((todayJsDay + 6) % 7));
  const grid = [];
  for (let w = weeks - 1; w >= 0; w--) {
    const monday = addDays(thisMonday, -7 * w);
    const column = [];
    for (let i = 0; i < 7; i++) {
      const d = addDays(monday, i);
      if (d > today) { column.push(null); continue; }
      const marks = perDay[d] || [];
      column.push({ date: d, score: marks.length ? mean(marks) : null, count: marks.length });
    }
    grid.push(column);
  }
  return grid;
}

/** A gentle note when the last few check-ins lean heavy (or bright). `recentMoods`
 * is mood names, oldest first. Needs at least 5. */
export function patternMessage(recentMoods) {
  if (recentMoods.length < 5) return null;
  const recent = recentMoods.slice(-7);
  const total = recent.length;
  const count = (...names) => recent.filter(m => names.includes(m)).length / total;
  if (count('stressed', 'anxious') >= 0.5) {
    return ['🌊', 'warn', "Stress and anxiety have come up often in your recent check-ins. That's a lot to " +
      'carry. It might be a good time for a calming exercise — or to talk to someone you trust.'];
  }
  if (count('sad', 'tired') >= 0.5) {
    return ['🕯️', 'gentle', 'Your recent check-ins have felt heavier and more tired. Low patches come and go, ' +
      "but if this has lasted a while, you don't have to sit with it alone."];
  }
  if (count('happy', 'grateful', 'hopeful', 'calm') >= 0.6) {
    return ['✨', 'good', "There's real warmth in your recent check-ins. Something is working — whatever " +
      "you've been doing, it's worth noticing."];
  }
  return null;
}

function kpiValues(d) {
  const sleepHours = d.sleep.map(r => r.hours);
  return {
    checkins: d.moods.length,
    positive: positiveShare(d.moods),
    sleep: sleepHours.length ? Math.round(mean(sleepHours) * 10) / 10 : null,
    habits: Object.values(d.habitDays).reduce((a, s) => a + s.size, 0),
  };
}

/** The four headline cards for the chosen range, each compared with the previous
 * range of the same length (no comparison for "All time"). */
export function kpiCards(data, days, today) {
  const [start, end] = window(days, today);
  const now = kpiValues(sliceData(data, start, end));
  let before = null;
  if (days != null) {
    const [pStart, pEnd] = window(days, today, 1);
    before = kpiValues(sliceData(data, pStart, pEnd));
  }
  const sign = (a, b) => (a > b ? 1 : a < b ? -1 : 0);
  const delta = (key, fmt) => {
    if (before == null || now[key] == null || before[key] == null) return [null, null];
    const diff = Math.round((now[key] - before[key]) * 10) / 10;
    return [diff ? fmt(diff) : 'no change', sign(now[key], before[key])];
  };
  const defs = [
    ['checkins', 'Mood check-ins', v => `${v}`, d => `${d > 0 ? '+' : ''}${d}`],
    ['positive', 'Positive moods', v => `${v}%`, d => `${d > 0 ? '+' : ''}${d} pts`],
    ['sleep', 'Average sleep', v => `${v.toFixed(1)} h`, d => `${d > 0 ? '+' : ''}${d.toFixed(1)} h`],
    ['habits', 'Habits ticked', v => `${v}`, d => `${d > 0 ? '+' : ''}${d}`],
  ];
  return defs.map(([key, label, valueFmt, deltaFmt]) => {
    const [dText, dSign] = delta(key, deltaFmt);
    return { key, label, value: now[key] != null ? valueFmt(now[key]) : '—', delta: dText, sign: dSign };
  });
}

/** Up to four findings as [emoji, tone, text]. */
export function findInsights(data, today) {
  const findings = [];
  const ratio = dailyPositiveRatio(data.moods);

  const pattern = patternMessage([...data.moods].sort((a, b) => a.timestamp - b.timestamp).map(m => m.mood));
  if (pattern) findings.push(pattern);

  const sleepByDay = {};
  for (const r of data.sleep) sleepByDay[r.day] = r.hours;
  const paired = Object.keys(ratio).filter(d => d in sleepByDay).map(d => [sleepByDay[d], ratio[d]]);
  if (paired.length >= MIN_PAIRED_DAYS) {
    const longSleep = paired.filter(([h]) => h >= 7).map(([, r]) => r);
    const shortSleep = paired.filter(([h]) => h < 7).map(([, r]) => r);
    if (longSleep.length >= MIN_DAYS_PER_GROUP && shortSleep.length >= MIN_DAYS_PER_GROUP) {
      const a = Math.round(mean(longSleep) * 100), b = Math.round(mean(shortSleep) * 100);
      if (a - b >= MIN_DIFFERENCE_PTS) {
        findings.push(['😴', 'good', `On days you slept 7+ hours, ${a}% of your check-ins were positive, ` +
          `versus ${b}% after shorter nights (across ${paired.length} days).`]);
      }
    }
  }

  const activeDays = new Set([...data.exercises.map(e => toDay(e.timestamp)), ...(data.habitDays.exercise || [])]);
  const withMove = Object.entries(ratio).filter(([d]) => activeDays.has(d)).map(([, r]) => r);
  const without = Object.entries(ratio).filter(([d]) => !activeDays.has(d)).map(([, r]) => r);
  if (withMove.length >= 3 && without.length >= 3) {
    const a = Math.round(mean(withMove) * 100), b = Math.round(mean(without) * 100);
    if (a - b >= MIN_DIFFERENCE_PTS) {
      findings.push(['🏃', 'good', `${a}% of your check-ins were positive on days you did an exercise session ` +
        `or ticked Regular Exercise, versus ${b}% on other days.`]);
    }
  }

  const week = window(7, today), prev = window(7, today, 1);
  const thisScores = sliceData(data, ...week).meals.map(m => m.balanceScore).filter(v => v != null);
  const prevScores = sliceData(data, ...prev).meals.map(m => m.balanceScore).filter(v => v != null);
  if (thisScores.length >= 2 && prevScores.length >= 2) {
    const a = mean(thisScores), b = mean(prevScores);
    if (Math.abs(a - b) >= 1) {
      const direction = a > b ? 'more balanced' : 'less balanced';
      findings.push(['🥗', a > b ? 'good' : 'gentle',
        `Your meals were ${direction} this week (average ${a.toFixed(1)}/10, ${a > b ? 'up' : 'down'} from ${b.toFixed(1)}).`]);
    }
  }

  const last14 = window(14, today);
  const daysCheckedIn = Object.keys(ratio).filter(d => inWindow(d, ...last14));
  if (daysCheckedIn.length >= 3) findings.push(['📅', 'neutral', `You checked in on ${daysCheckedIn.length} of the last 14 days.`]);

  return findings.slice(0, 4);
}

/** Top of a sleep chart: the next whole hour above the longest night (never below 10). */
export function niceCeiling(value) {
  return Math.max(10, Math.floor(value) + 1);
}
