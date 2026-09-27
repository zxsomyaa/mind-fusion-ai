import { useState } from 'react';
import { C, FONT, MOODS, HABITS } from '../data';
import { balanceTone, summariseMeals } from '../nutritionLogic';
import { loadSessions, logSession, deleteSession } from '../exerciseStorage';
import {
  RANGES, window as timeWindow, sliceData, dailyScores, weekdayPositiveShare,
  checkinStreaks, calendarGrid, kpiCards, findInsights, niceCeiling, toDay,
} from '../insightsLogic';
import { DonutChart, BarChart, LineChart, MoodCalendar } from './charts';
import AddExerciseModal from './AddExerciseModal';

const MACRO_COLOURS = { protein: '#E07A5F', carbs: '#D4A017', fat: '#748CAB', fibre: '#52B788' };
const MACRO_NAMES = { protein: 'Protein', carbs: 'Carbs', fat: 'Fat', fibre: 'Fibre' };
const TONE_TINTS = { good: '82,183,136', warn: '224,122,95', gentle: '116,140,171', neutral: '168,155,144' };
const MAX_SLEEP_BARS = 30, MAX_CALORIE_BARS = 14, MAX_TREND_POINTS = 60, CALENDAR_WEEKS = 12;

function load(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } }
function save(k, v) { localStorage.setItem(k, JSON.stringify(v)); }

function collectData(moodHistory) {
  const sleepLog = load('mf_sleep_log', {});
  const habitLog = load('mf_habit_log', {});
  const habitDays = {};
  for (const [day, ids] of Object.entries(habitLog)) for (const id of ids) (habitDays[id] ??= new Set()).add(day);
  return {
    moods: moodHistory,
    sleep: Object.entries(sleepLog).map(([day, v]) => ({ day, hours: v.hours, quality: v.quality })),
    habitDays,
    meals: load('mf_nutrition_history', []),
    exercises: loadSessions(),
    journal: load('mf_journal', []),
  };
}

function Card({ children, style }) {
  return <div style={{ background: C.surface, borderRadius: 16, border: `1px solid ${C.border}`, padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 10, ...style }}>{children}</div>;
}
function Heading({ children }) { return <div style={{ fontSize: 15, fontWeight: 700, color: C.text }}>{children}</div>; }
function Muted({ children, size = 12 }) { return <p style={{ color: C.textMuted, fontSize: size, lineHeight: 1.5 }}>{children}</p>; }

function StatCard({ label, value, delta, sign }) {
  const arrow = sign > 0 ? '▲' : sign < 0 ? '▼' : '';
  const colour = sign > 0 ? C.sage : sign < 0 ? '#E07A5F' : C.textMuted;
  return (
    <Card style={{ flex: 1, minWidth: 140, padding: '14px 18px', gap: 2 }}>
      <span style={{ color: C.textMuted, fontSize: 12, fontWeight: 600 }}>{label}</span>
      <span style={{ color: C.text, fontSize: 26, fontWeight: 800 }}>{value}</span>
      {delta && <span style={{ fontSize: 11, color: colour }}>{arrow} {delta} vs previous</span>}
    </Card>
  );
}

function Section({ id, title, summary, open, onToggle, children }) {
  return (
    <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 10 }}>
      <button onClick={() => onToggle(id)} style={{
        width: '100%', display: 'flex', alignItems: 'center', gap: 8, background: 'none', border: 'none',
        cursor: 'pointer', padding: '2px 0', textAlign: 'left', fontFamily: FONT.sans,
      }}>
        <span style={{ color: C.textMuted, fontSize: 10, transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 0.15s', display: 'inline-block' }}>▶</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: C.text }}>{title}</span>
        <span style={{ flex: 1 }} />
        {!open && <span style={{ fontSize: 12, color: C.textMuted, textAlign: 'right' }}>{summary}</span>}
      </button>
      {open && <div style={{ paddingTop: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>{children}</div>}
    </div>
  );
}

export default function InsightsTab({ moodHistory, userProfile }) {
  const [rangeDays, setRangeDays] = useState(30);
  const [open, setOpen] = useState(() => new Set(load('mf_insights_open', [])));
  const [addingExercise, setAddingExercise] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const toggle = (key) => {
    setOpen(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      save('mf_insights_open', [...next]);
      return next;
    });
  };

  const today = new Date().toISOString().slice(0, 10);
  const data = collectData(moodHistory);
  void refreshKey; // recomputation trigger after logging/deleting an exercise from this tab

  const hasAnything = data.moods.length || data.sleep.length || data.meals.length || data.exercises.length ||
    data.journal.length || Object.values(data.habitDays).some(s => s.size);

  if (!hasAnything) {
    return (
      <Card style={{ alignItems: 'center', textAlign: 'center', padding: '48px 24px' }}>
        <div style={{ fontSize: 44 }}>✨</div>
        <p style={{ fontSize: 18, fontWeight: 700 }}>Your insights will appear here</p>
        <Muted size={13}>Check in with how you feel, log your sleep, tick a habit or analyse a meal — patterns start to show after a few days.</Muted>
      </Card>
    );
  }

  const [start, end] = timeWindow(rangeDays, today);
  const current = sliceData(data, start, end);
  const rangeLabel = RANGES.find(([, d]) => d === rangeDays)[0];
  const note = (rangeDays ? `Last ${rangeLabel}` : "Everything you've logged") + (rangeDays ? ` — compared with the ${rangeDays} days before` : '');

  const kpis = kpiCards(data, rangeDays, today);
  const findings = findInsights(data, today);

  const moodCounts = {};
  for (const m of current.moods) moodCounts[m.mood] = (moodCounts[m.mood] || 0) + 1;
  const moodSegments = Object.entries(moodCounts)
    .sort((a, b) => b[1] - a[1])
    .filter(([m]) => MOODS[m])
    .map(([m, n]) => ({ label: MOODS[m].label, value: n, colour: MOODS[m].color }));

  const trendPoints = dailyScores(current.moods).slice(-MAX_TREND_POINTS).map(([d, s]) => ({
    x: d, y: s, label: new Date(d + 'T00:00:00').toLocaleDateString('en', { day: '2-digit', month: 'short' }),
    tooltip: `${new Date(d + 'T00:00:00').toLocaleDateString('en', { weekday: 'short', day: '2-digit', month: 'short' })}: ` +
      (s >= 0.34 ? 'mostly positive' : s <= -0.34 ? 'mostly heavy' : 'mixed'),
  }));

  const grid = calendarGrid(data.moods, today, CALENDAR_WEEKS);
  const streaks = checkinStreaks(data.moods, today);
  const weekdayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const shares = weekdayPositiveShare(data.moods);
  const rated = shares.map((s, i) => [s[0], weekdayNames[i], s[1]]).filter(([share, , count]) => share != null && count >= 3);
  let weekdaySummary = 'Check in on a few more days to see this';
  if (rated.length >= 2) {
    const best = rated.reduce((a, b) => (b[0] > a[0] ? b : a));
    const worst = rated.reduce((a, b) => (b[0] < a[0] ? b : a));
    if (best[0] - worst[0] >= 15) weekdaySummary = `Brightest: ${best[1]} (${best[0]}%)  ·  Toughest: ${worst[1]} (${worst[0]}%)`;
  }
  const weekdayBars = shares.map(([share, count], i) => share == null
    ? { label: weekdayNames[i], value: 0, tooltip: `${weekdayNames[i]}: no check-ins yet` }
    : { label: weekdayNames[i], value: share, colour: share >= 60 ? C.sage : share >= 40 ? '#D9B26F' : '#E07A5F', tooltip: `${weekdayNames[i]}: ${share}% positive (${count} check-in${count !== 1 ? 's' : ''})` });

  const sleepRows = [...current.sleep].sort((a, b) => a.day < b.day ? -1 : 1).slice(-MAX_SLEEP_BARS);
  const sleepBars = sleepRows.map(r => ({
    label: sleepRows.length > 8 ? r.day.slice(8) : new Date(r.day + 'T00:00:00').toLocaleDateString('en', { day: '2-digit', month: 'short' }),
    value: r.hours, colour: r.hours >= 7 && r.hours <= 9 ? C.sage : C.primaryLight,
    tooltip: `${new Date(r.day + 'T00:00:00').toLocaleDateString('en', { weekday: 'short', day: '2-digit', month: 'short' })}: ${r.hours}h${r.quality ? `, quality ${r.quality}/5` : ''}`,
  }));
  let sleepSummary = 'Log your sleep on the Today page';
  if (sleepRows.length) {
    const hours = sleepRows.map(r => r.hours);
    const onTarget = hours.filter(h => h >= 7 && h <= 9).length;
    sleepSummary = `Average ${(hours.reduce((a, b) => a + b, 0) / hours.length).toFixed(1)} h  ·  ${onTarget} of ${hours.length} nights on target`;
  }

  const mealsSummary = summariseMeals(current.meals);
  const caloriesByDay = {};
  for (const m of current.meals) if (m.caloriesEstimate != null) {
    const d = toDay(m.timestamp);
    const [tot, n] = caloriesByDay[d] || [0, 0];
    caloriesByDay[d] = [tot + m.caloriesEstimate, n + 1];
  }
  const calorieDays = Object.keys(caloriesByDay).sort().slice(-MAX_CALORIE_BARS);
  const calorieBars = calorieDays.map(d => ({
    label: calorieDays.length <= 8 ? new Date(d + 'T00:00:00').toLocaleDateString('en', { day: '2-digit', month: 'short' }) : d.slice(8),
    value: caloriesByDay[d][0], colour: C.primaryLight,
    tooltip: `${new Date(d + 'T00:00:00').toLocaleDateString('en', { weekday: 'short', day: '2-digit', month: 'short' })}: ${caloriesByDay[d][0]} kcal from ${caloriesByDay[d][1]} meal${caloriesByDay[d][1] !== 1 ? 's' : ''}`,
  }));
  const calorieSummary = calorieDays.length
    ? `Average ${Math.round(calorieDays.reduce((a, d) => a + caloriesByDay[d][0], 0) / calorieDays.length).toLocaleString()} kcal on days you logged meals`
    : 'No calorie data yet';

  const withMacros = current.meals.filter(m => Object.keys(MACRO_NAMES).some(k => m[k] != null));
  const macroAverages = {};
  for (const k of Object.keys(MACRO_NAMES)) {
    const vals = withMacros.map(m => m[k]).filter(v => v != null);
    if (vals.length) macroAverages[k] = Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10;
  }
  const macroTotal = Object.values(macroAverages).reduce((a, b) => a + b, 0);
  const macrosSummary = withMacros.length
    ? 'Per meal: ' + Object.entries(macroAverages).map(([k, v]) => `${v}g ${MACRO_NAMES[k].toLowerCase()}`).join('  ·  ')
    : 'Saved with each meal you analyse from now on';

  const habitIds = [...new Set([...(userProfile?.habits || []), ...Object.keys(current.habitDays).filter(h => current.habitDays[h].size)])];
  const span = start == null
    ? Math.max(1, Math.round((new Date(today) - new Date(Math.min(...Object.values(current.habitDays).flatMap(s => [...s]).map(d => +new Date(d)), +new Date(today)))) / 86400000) + 1)
    : Math.round((new Date(end) - new Date(start)) / 86400000) + 1;
  const habitRows = habitIds.map(hid => {
    const meta = HABITS.find(h => h.id === hid);
    if (!meta) return null;
    const ticked = current.habitDays[hid]?.size || 0;
    return { fraction: ticked / span, label: `${meta.emoji} ${meta.label}`, value: `${ticked}/${span}` };
  }).filter(Boolean).sort((a, b) => b.fraction - a.fraction).slice(0, 5);

  const exerciseCounts = {};
  for (const x of current.exercises) exerciseCounts[x.name] = (exerciseCounts[x.name] || 0) + 1;
  const topExercises = Object.entries(exerciseCounts).sort((a, b) => b[1] - a[1]);
  const topCount = topExercises[0]?.[1] || 1;
  const exerciseMinutes = current.exercises.reduce((a, x) => a + (x.minutes || 0), 0);

  const journalWords = current.journal.reduce((a, e) => a + e.text.split(/\s+/).filter(Boolean).length, 0);
  const journalMoods = {};
  for (const e of current.journal) if (MOODS[e.mood]) journalMoods[e.mood] = (journalMoods[e.mood] || 0) + 1;
  const topJournalMoods = Object.entries(journalMoods).sort((a, b) => b[1] - a[1]).slice(0, 4);

  const ghostBtn = { padding: '7px 16px', borderRadius: 20, border: `1.5px solid ${C.border}`, background: 'none', color: C.text, fontSize: 13, cursor: 'pointer', fontFamily: FONT.sans };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 24, fontWeight: 800, marginBottom: 4 }}>Insights</h1>
          <Muted size={13}>{note}</Muted>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {RANGES.map(([label, days]) => (
            <button key={label} onClick={() => setRangeDays(days)} style={{
              ...ghostBtn, borderRadius: 100,
              background: rangeDays === days ? C.primary : 'none',
              color: rangeDays === days ? '#FFF' : C.text,
              border: rangeDays === days ? 'none' : `1.5px solid ${C.border}`,
            }}>{label}</button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
        {kpis.map(k => <StatCard key={k.key} label={k.label} value={k.value} delta={k.delta} sign={k.sign} />)}
      </div>

      <Card>
        <Heading>What we noticed</Heading>
        {findings.length === 0 ? (
          <Muted size={13}>Keep checking in — once you have about a week of moods (and some sleep or exercise logged) we'll point out patterns here.</Muted>
        ) : (
          <>
            {findings.map(([emoji, tone, text], i) => (
              <p key={i} style={{ background: `rgba(${TONE_TINTS[tone] || TONE_TINTS.neutral}, 0.16)`, borderRadius: 12, padding: '10px 14px', fontSize: 13 }}>
                <span style={{ fontSize: 16 }}>{emoji}</span>&nbsp;&nbsp;{text}
              </p>
            ))}
            <Muted size={11}>These are patterns in your own data, not medical advice or proof of cause.</Muted>
          </>
        )}
      </Card>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'stretch' }}>
        <Card style={{ flex: '4 1 260px' }}>
          <Heading>Mood mix</Heading>
          {moodSegments.length === 0 ? <Muted>No check-ins in this period.</Muted> : (
            <DonutChart segments={moodSegments} centre={String(current.moods.length)} sub="check-ins" />
          )}
        </Card>
        <Card style={{ flex: '6 1 340px' }}>
          <Heading>Mood trend</Heading>
          <Muted>Daily average: 'positive' means every check-in that day was a good one</Muted>
          <LineChart points={trendPoints} />
        </Card>
      </div>

      <Card>
        <Heading>Mood calendar — last {CALENDAR_WEEKS} weeks</Heading>
        <Muted>Hover a day for details</Muted>
        <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <MoodCalendar grid={grid} />
          <div style={{ display: 'flex', gap: 24 }}>
            {[[streaks.current, 'day streak'], [streaks.longest, 'longest streak'], [streaks.days, 'days checked in']].map(([v, caption]) => (
              <div key={caption}>
                <div style={{ fontSize: 26, fontWeight: 800 }}>{v}</div>
                <Muted>{caption}</Muted>
              </div>
            ))}
          </div>
        </div>
        <Section id="weekday" title="Best days of the week" summary={weekdaySummary} open={open.has('weekday')} onToggle={toggle}>
          <Muted>Share of your check-ins that were positive, by weekday (all your data)</Muted>
          <BarChart bars={weekdayBars} yMax={100} emptyText="Check in on a few days to see this" />
        </Section>
        <Section id="sleep" title="Sleep" summary={sleepSummary} open={open.has('sleep')} onToggle={toggle}>
          <Muted>Bars in the green band met the 7-9 hour target</Muted>
          <BarChart bars={sleepBars} yMax={Math.max(10, niceCeiling(Math.max(0, ...sleepRows.map(r => r.hours))))} band={[7, 9]} emptyText="Log your sleep on the Today page to see it here" />
        </Section>
      </Card>

      <Card>
        <Heading>Nutrition</Heading>
        {current.meals.length === 0 ? (
          <Muted>No meals analysed in this period — analyse one on the Nutrition page.</Muted>
        ) : (
          <>
            <Muted>{mealsSummary.count} meal{mealsSummary.count !== 1 ? 's' : ''}{mealsSummary.avgBalance != null ? `  ·  average balance ${mealsSummary.avgBalance}/10` : ''}</Muted>
            {current.meals.slice(0, 5).map((meal, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <ScoreBadge score={meal.balanceScore} />
                <div>
                  <p style={{ fontWeight: 700, fontSize: 13 }}>{meal.foods || 'Meal'}</p>
                  <Muted>{new Date(meal.timestamp).toLocaleDateString('en', { weekday: 'short', day: '2-digit', month: 'short' })}{meal.caloriesEstimate != null ? `  ·  ${meal.caloriesEstimate} kcal` : ''}</Muted>
                </div>
              </div>
            ))}
          </>
        )}
        <Section id="calories" title="Calories per day" summary={calorieSummary} open={open.has('calories')} onToggle={toggle}>
          <Muted>Estimated from the meals you analysed</Muted>
          <BarChart bars={calorieBars} colour={C.primaryLight} emptyText="Analyse a meal on the Nutrition page to see calories here" />
        </Section>
        <Section id="macros" title="Macros" summary={macrosSummary} open={open.has('macros')} onToggle={toggle}>
          <Muted>Average per meal, by weight</Muted>
          {macroTotal > 0 ? (
            <DonutChart segments={Object.entries(macroAverages).map(([k, v]) => ({ label: MACRO_NAMES[k], value: v, colour: MACRO_COLOURS[k] }))} centre={`${Math.round(macroTotal)}g`} sub="per meal" />
          ) : <Muted>Saved with each meal you analyse from now on.</Muted>}
        </Section>
      </Card>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <Card style={{ flex: '6 1 320px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <Heading>Exercises</Heading>
              <Muted>{current.exercises.length} session{current.exercises.length !== 1 ? 's' : ''}{exerciseMinutes ? `  ·  ${exerciseMinutes} min logged` : ''}</Muted>
            </div>
            <button onClick={() => setAddingExercise(true)} title="Log something you did outside the app — a walk, a workout, a class" style={ghostBtn}>＋ Add exercise</button>
          </div>
          {current.exercises.length === 0 ? (
            <Muted>Finish a guided exercise, or add one you did yourself.</Muted>
          ) : (
            <>
              {topExercises.slice(0, 5).map(([name, n]) => (
                <div key={name} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <span>{name}</span><span style={{ color: C.textMuted }}>{n}x</span>
                  </div>
                  <div style={{ height: 8, borderRadius: 4, background: C.border, overflow: 'hidden' }}>
                    <div style={{ width: `${(n / topCount) * 100}%`, height: '100%', background: C.primary }} />
                  </div>
                </div>
              ))}
              <Muted size={11}>Recent</Muted>
              {current.exercises.slice(0, 5).map(x => (
                <div key={x.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                  <span style={{ flex: 1 }}>
                    <b>{x.name}</b>{' '}
                    <span style={{ color: C.textMuted }}>
                      {new Date(x.timestamp).toLocaleString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      {x.minutes ? ` · ${x.minutes} min` : ''}
                    </span>
                  </span>
                  {x.source === 'manual' && <span style={{ padding: '2px 10px', borderRadius: 100, background: C.primaryPale, color: C.primary, fontSize: 11 }}>added by you</span>}
                  <button onClick={() => { deleteSession(x.id); setRefreshKey(k => k + 1); }} title="Remove this entry" style={{ width: 22, height: 22, borderRadius: 6, border: `1px solid ${C.border}`, background: 'none', color: C.textMuted, cursor: 'pointer', fontSize: 13 }}>×</button>
                </div>
              ))}
            </>
          )}
        </Card>

        <div style={{ flex: '4 1 240px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card style={{ padding: '14px 18px' }}>
            <Heading>Habit consistency</Heading>
            {habitRows.length === 0 ? <Muted>Tick habits on the Today page to see them here.</Muted> : (
              <>
                {habitRows.map(r => (
                  <div key={r.label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                    <span style={{ width: 130, flexShrink: 0 }}>{r.label}</span>
                    <div style={{ flex: 1, height: 6, borderRadius: 3, background: C.border, overflow: 'hidden' }}>
                      <div style={{ width: `${r.fraction * 100}%`, height: '100%', background: r.fraction >= 0.6 ? C.sage : r.fraction >= 0.3 ? C.primaryLight : '#D4A017' }} />
                    </div>
                    <span style={{ width: 40, textAlign: 'right', color: C.textMuted, fontSize: 11 }}>{r.value}</span>
                  </div>
                ))}
                <Muted size={11}>{start != null ? `Days ticked, out of the last ${span}` : 'Days ticked'}</Muted>
              </>
            )}
          </Card>

          <Card style={{ padding: '14px 18px' }}>
            <Heading>Journal</Heading>
            <Muted>{current.journal.length} entr{current.journal.length !== 1 ? 'ies' : 'y'} written</Muted>
            {current.journal.length === 0 ? <Muted>Write in your journal to see a summary here.</Muted> : (
              <>
                <Muted size={13}>About {journalWords.toLocaleString()} words  ·  averaging {Math.round(journalWords / current.journal.length)} per entry</Muted>
                {topJournalMoods.length > 0 && (
                  <>
                    <Muted>How your entries felt:</Muted>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {topJournalMoods.map(([mood, n]) => (
                        <span key={mood} style={{ padding: '4px 12px', borderRadius: 100, background: `${MOODS[mood].color}2E`, color: MOODS[mood].color, fontSize: 12, fontWeight: 600 }}>
                          {MOODS[mood].emoji} {MOODS[mood].label} · {n}
                        </span>
                      ))}
                    </div>
                  </>
                )}
              </>
            )}
          </Card>
        </div>
      </div>

      {addingExercise && (
        <AddExerciseModal
          onClose={() => setAddingExercise(false)}
          onSave={(entry) => { logSession({ name: entry.name, minutes: entry.minutes, source: 'manual', timestamp: entry.when }); setAddingExercise(false); setRefreshKey(k => k + 1); }}
        />
      )}
    </div>
  );
}

function ScoreBadge({ score }) {
  const tone = balanceTone(score);
  const colour = tone === 'high' ? C.sage : tone === 'mid' ? '#D4A017' : '#E07A5F';
  return (
    <div style={{ width: 38, height: 38, borderRadius: 19, flexShrink: 0, background: `${colour}2E`, color: colour, border: `2px solid ${colour}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 13 }}>
      {score != null ? score : '?'}
    </div>
  );
}
