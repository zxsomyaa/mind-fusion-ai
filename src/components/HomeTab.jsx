import { useState } from 'react';
import { C, FONT, MOODS, HABITS, AFFIRMATIONS, getPersonalizedRecs } from '../data';

function load(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } }
function save(k, v) { localStorage.setItem(k, JSON.stringify(v)); }

const isoDay = (d = new Date()) => d.toISOString().slice(0, 10);

function greetingFor(hour) {
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

/** Consecutive days with activity, counting back from today. If nothing has
 * happened yet today the streak is still alive as long as yesterday had
 * activity - it only breaks once a whole day has been skipped. */
function currentStreak(days) {
  const set = days instanceof Set ? days : new Set(days);
  const today = new Date();
  let cursor = isoDay(today);
  if (!set.has(cursor)) {
    const yest = new Date(today); yest.setDate(yest.getDate() - 1);
    cursor = isoDay(yest);
  }
  let streak = 0;
  let cursorDate = new Date(cursor + 'T00:00:00');
  while (set.has(isoDay(cursorDate))) {
    streak += 1;
    cursorDate.setDate(cursorDate.getDate() - 1);
  }
  return streak;
}

function Card({ children, style }) {
  return (
    <div style={{
      background: C.surface, borderRadius: 16, border: `1px solid ${C.border}`,
      padding: '18px 20px', boxShadow: C.shadow, ...style,
    }}>
      {children}
    </div>
  );
}

function StatCard({ value, caption }) {
  return (
    <Card style={{ flex: 1, textAlign: 'center', padding: '14px 12px' }}>
      <div style={{ fontSize: 20, fontWeight: 700, color: C.primary }}>{value}</div>
      <div style={{ color: C.textMuted, fontSize: 11, marginTop: 2 }}>{caption}</div>
    </Card>
  );
}

export default function HomeTab({ userName, userProfile, moodHistory, addMoodEntry, onNavigate }) {
  const [habitLog, setHabitLog] = useState(() => load('mf_habit_log', {}));
  const [sleepLog, setSleepLog] = useState(() => load('mf_sleep_log', {}));
  const [sleepHours, setSleepHours] = useState(() => (load('mf_sleep_log', {})[isoDay()]?.hours ?? 7.5));
  const [sleepQuality, setSleepQuality] = useState(() => load('mf_sleep_log', {})[isoDay()]?.quality ?? 0);
  const [checkinStatus, setCheckinStatus] = useState('');
  const [sleepStatus, setSleepStatus] = useState(() => {
    const logged = load('mf_sleep_log', {})[isoDay()];
    return logged ? `Logged today: ${logged.hours}h${logged.quality ? ` · quality ${logged.quality}/5` : ''}` : '';
  });

  const now = new Date();
  const journal = load('mf_journal', []);
  const meals = load('mf_nutrition_history', []);
  const exerciseSessions = load('mf_exercise_sessions', []);
  const today = isoDay();

  const activityDays = new Set([
    ...moodHistory.map(m => isoDay(new Date(m.timestamp))),
    ...journal.map(j => isoDay(new Date(j.timestamp))),
    ...meals.map(m => isoDay(new Date(m.timestamp))),
    ...exerciseSessions.map(s => isoDay(new Date(s.timestamp))),
    ...Object.keys(habitLog),
    ...Object.keys(sleepLog),
  ]);
  const streak = currentStreak(activityDays);

  const habitIds = (userProfile?.habits || []).filter(h => HABITS.some(x => x.id === h));
  const doneToday = new Set(habitLog[today] || []);

  const toggleHabit = (hid) => {
    setHabitLog(prev => {
      const day = new Set(prev[today] || []);
      day.has(hid) ? day.delete(hid) : day.add(hid);
      const updated = { ...prev, [today]: [...day] };
      save('mf_habit_log', updated);
      return updated;
    });
  };

  const habitStreak = (hid) => currentStreak(Object.keys(habitLog).filter(d => (habitLog[d] || []).includes(hid)));

  const logMood = (key) => {
    addMoodEntry({ mood: key, ...MOODS[key] });
    setCheckinStatus(`✓ Logged: ${MOODS[key].emoji} ${MOODS[key].label}`);
  };

  const saveSleep = () => {
    const updated = { ...sleepLog, [today]: { hours: sleepHours, quality: sleepQuality || null } };
    setSleepLog(updated);
    save('mf_sleep_log', updated);
    setSleepStatus(`✓ Saved: ${sleepHours}h${sleepQuality ? ` · quality ${sleepQuality}/5` : ''}`);
  };

  const lastMood = moodHistory.length ? moodHistory[moodHistory.length - 1].mood : null;
  const recs = lastMood ? getPersonalizedRecs(userProfile || {}, lastMood) : [];
  const rec = recs[0];
  const aff = AFFIRMATIONS[Math.floor((now - new Date(now.getFullYear(), 0, 0)) / 86400000) % AFFIRMATIONS.length];

  const sectionLabel = { color: C.textMuted, fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 6 };
  const heading = { fontSize: 15, fontWeight: 700, color: C.text, marginBottom: 10 };
  const ghostBtn = { padding: '8px 14px', borderRadius: 20, border: `1.5px solid ${C.border}`, background: 'none', color: C.text, fontSize: 13, cursor: 'pointer', fontFamily: FONT.sans };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 720, margin: '0 auto' }}>
      <div>
        <h1 style={{ fontFamily: FONT.serif, fontSize: 24, fontWeight: 700, color: C.primary }}>
          {greetingFor(now.getHours())}, {userName}
        </h1>
        <p style={{ color: C.textMuted }}>{now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}</p>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <StatCard value={`🔥 ${streak} day${streak !== 1 ? 's' : ''}`} caption="check-in streak" />
        <StatCard value={moodHistory.length} caption="mood check-ins" />
        <StatCard value={journal.length} caption="journal entries" />
        <StatCard value={meals.length} caption="meals analysed" />
        <StatCard value={exerciseSessions.length} caption="exercises done" />
      </div>

      <Card>
        <div style={heading}>How are you feeling right now?</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {Object.entries(MOODS).map(([key, meta]) => (
            <button key={key} onClick={() => logMood(key)} style={ghostBtn}>
              {meta.emoji} {meta.label}
            </button>
          ))}
        </div>
        {checkinStatus && <p style={{ color: C.sage, marginTop: 10, fontSize: 13 }}>{checkinStatus}</p>}
      </Card>

      {habitIds.length > 0 && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div style={{ ...heading, marginBottom: 0 }}>Today's habits</div>
            <span style={{ color: C.textMuted, fontSize: 12 }}>{doneToday.size} of {habitIds.length} done</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {habitIds.map(hid => {
              const meta = HABITS.find(h => h.id === hid);
              const done = doneToday.has(hid);
              const streakN = habitStreak(hid);
              return (
                <label key={hid} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                  <input type="checkbox" checked={done} onChange={() => toggleHabit(hid)}
                    style={{ width: 18, height: 18, accentColor: C.primary, cursor: 'pointer' }} />
                  <span style={{ flex: 1, fontSize: 14, color: done ? C.textMuted : C.text, textDecoration: done ? 'line-through' : 'none' }}>
                    {meta.emoji} {meta.label}
                  </span>
                  {streakN > 0 && <span style={{ color: C.textMuted, fontSize: 12 }} title="Days in a row">🔥 {streakN}</span>}
                </label>
              );
            })}
          </div>
        </Card>
      )}

      <Card>
        <div style={heading}>How did you sleep?</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={() => setSleepHours(h => Math.max(0, h - 0.5))} style={{ ...ghostBtn, padding: '6px 12px', borderRadius: 10 }}>−</button>
          <div style={{ width: 64, textAlign: 'center', fontWeight: 600, fontSize: 14 }}>{sleepHours}h</div>
          <button onClick={() => setSleepHours(h => Math.min(14, h + 0.5))} style={{ ...ghostBtn, padding: '6px 12px', borderRadius: 10 }}>+</button>
          <div style={{ width: 1, height: 20, background: C.border, margin: '0 6px' }} />
          {['😫', '😕', '😐', '🙂', '😄'].map((emoji, i) => (
            <button key={emoji} onClick={() => setSleepQuality(i + 1)} title={`Sleep quality ${i + 1}/5`}
              style={{
                ...ghostBtn, padding: '6px 10px', borderRadius: 10,
                border: `1.5px solid ${sleepQuality === i + 1 ? C.primary : C.border}`,
                background: sleepQuality === i + 1 ? C.primaryPale : 'none',
              }}>{emoji}</button>
          ))}
          <div style={{ flex: 1 }} />
          <button onClick={saveSleep} style={{ ...ghostBtn, background: C.primary, color: '#FFF', border: 'none', fontWeight: 600 }}>Log sleep</button>
        </div>
        {sleepStatus && <p style={{ color: C.sage, marginTop: 10, fontSize: 13 }}>{sleepStatus}</p>}
      </Card>

      {rec && (
        <Card>
          <div style={sectionLabel}>
            {rec.moods.includes(lastMood) ? `Because you last felt ${(MOODS[lastMood]?.label || lastMood).toLowerCase()}` : 'Suggested for your goals'}
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, color: C.primary, marginBottom: 6 }}>{rec.emoji} {rec.title}</div>
          <p style={{ color: C.text, fontSize: 14, lineHeight: 1.5 }}>{rec.body}</p>
        </Card>
      )}

      <Card>
        <div style={sectionLabel}>Today's affirmation</div>
        <p style={{ fontSize: 17, fontStyle: 'italic', color: C.text }}>"{aff.text}"</p>
      </Card>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {[['💬 Talk it through', 'chat'], ['📓 Write in journal', 'journal'], ['🧘 Do an exercise', 'exercises'], ['🥗 Log a meal', 'nutrition']].map(([label, key]) => (
          <button key={key} onClick={() => onNavigate(key)} style={{ ...ghostBtn, flex: 1, minWidth: 140, borderRadius: 12, padding: '11px 14px' }}>
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
