import { C, FONT, MOODS } from '../data';

function getPatternMessage(history) {
  if (history.length < 5) return null;
  const recent = history.slice(-7);
  const counts = {};
  for (const h of recent) counts[h.mood] = (counts[h.mood] || 0) + 1;
  const total = recent.length;

  const stressAnxiety = ((counts.stressed || 0) + (counts.anxious || 0)) / total;
  const sadTired      = ((counts.sad || 0) + (counts.tired || 0)) / total;
  const positive      = ((counts.happy || 0) + (counts.grateful || 0) + (counts.hopeful || 0) + (counts.calm || 0)) / total;

  if (stressAnxiety >= 0.5) return {
    type: 'warning',
    emoji: '🌊',
    text: "Over the past week, stress and anxiety have come up often in your reflections. That's a lot to carry. It might be a good time to try a calming exercise — or speak with someone you trust.",
  };
  if (sadTired >= 0.5) return {
    type: 'gentle',
    emoji: '🕯️',
    text: "Your recent check-ins have felt heavier and more tired. Low periods come and go, but if this has been going on a while, you don't have to sit with it alone.",
  };
  if (positive >= 0.6) return {
    type: 'positive',
    emoji: '✨',
    text: "Looking at your recent mood history, there's a real warmth there. Something is working — whatever you've been doing, it's worth noticing.",
  };
  return null;
}

export default function InsightsTab({ moodHistory }) {
  if (moodHistory.length === 0) {
    return (
      <div style={{
        textAlign: 'center', padding: '64px 24px',
        background: C.surface, borderRadius: 20, boxShadow: C.shadow,
      }}>
        <div style={{ fontSize: 44, marginBottom: 14 }}>✨</div>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 22, marginBottom: 10 }}>Mood insights</h2>
        <p style={{ color: C.textMuted, fontSize: 15, lineHeight: 1.6, maxWidth: 320, margin: '0 auto' }}>
          Start a conversation or write in your journal — your mood insights will appear here over time.
        </p>
      </div>
    );
  }

  const counts = {};
  for (const h of moodHistory) counts[h.mood] = (counts[h.mood] || 0) + 1;
  const total = moodHistory.length;

  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const dominant = sorted[0]?.[0];
  const dominantMeta = MOODS[dominant];

  const pattern = getPatternMessage(moodHistory);

  const recentTimeline = moodHistory.slice(-28).reverse();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 24, marginBottom: 6 }}>Your mood insights</h2>
        <p style={{ color: C.textMuted, fontSize: 14 }}>Based on {total} check-in{total !== 1 ? 's' : ''} so far.</p>
      </div>

      {/* Dominant mood */}
      {dominantMeta && (
        <div style={{
          background: `linear-gradient(135deg, ${dominantMeta.bg}, ${C.surface})`,
          border: `1px solid ${dominantMeta.color}44`,
          borderRadius: 20, padding: '22px 24px',
          display: 'flex', alignItems: 'center', gap: 16,
        }}>
          <span style={{ fontSize: 44 }}>{dominantMeta.emoji}</span>
          <div>
            <p style={{ fontSize: 12, color: C.textMuted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>Most frequent mood</p>
            <p style={{ fontFamily: FONT.serif, fontSize: 22, color: dominantMeta.color, marginTop: 4 }}>
              {dominantMeta.label}
            </p>
            <p style={{ fontSize: 13, color: C.textMuted, marginTop: 4 }}>
              {counts[dominant]} of {total} check-ins ({Math.round((counts[dominant] / total) * 100)}%)
            </p>
          </div>
        </div>
      )}

      {/* Pattern message */}
      {pattern && (
        <div style={{
          borderRadius: 16, padding: '18px 20px',
          background: pattern.type === 'positive' ? C.sagePale : pattern.type === 'warning' ? '#FCEEE9' : '#EBF0F5',
          border: `1px solid ${pattern.type === 'positive' ? C.sageLight : pattern.type === 'warning' ? '#F4B8AA' : '#C5D3E0'}`,
          display: 'flex', gap: 14, alignItems: 'flex-start',
        }}>
          <span style={{ fontSize: 24, flexShrink: 0 }}>{pattern.emoji}</span>
          <p style={{ fontSize: 14, lineHeight: 1.65, color: C.text }}>{pattern.text}</p>
        </div>
      )}

      {/* Distribution chart */}
      <div style={{
        background: C.surface, borderRadius: 20, boxShadow: C.shadow,
        border: `1px solid ${C.border}`, padding: '22px 24px',
      }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: C.text, marginBottom: 18 }}>Mood distribution</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {sorted.map(([mood, count]) => {
            const meta = MOODS[mood];
            if (!meta) return null;
            const pct = Math.round((count / total) * 100);
            return (
              <div key={mood}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                  <span style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 6, color: C.text }}>
                    <span>{meta.emoji}</span> {meta.label}
                  </span>
                  <span style={{ fontSize: 12, color: C.textMuted }}>{count} · {pct}%</span>
                </div>
                <div style={{ height: 8, background: C.border, borderRadius: 10, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', borderRadius: 10,
                    width: `${pct}%`, background: meta.color,
                    transition: 'width 0.6s ease',
                  }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Timeline */}
      <div style={{
        background: C.surface, borderRadius: 20, boxShadow: C.shadow,
        border: `1px solid ${C.border}`, padding: '22px 24px',
      }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: C.text, marginBottom: 14 }}>
          Recent check-ins (newest first)
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {recentTimeline.map((h, i) => {
            const meta = MOODS[h.mood];
            return (
              <div key={i} title={`${meta?.label} · ${new Date(h.timestamp).toLocaleDateString()}`} style={{
                width: 38, height: 38, borderRadius: '50%',
                background: meta?.bg || C.border,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 20, cursor: 'default',
              }}>
                {meta?.emoji || '?'}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
