import { C, FONT, HEALTH_CONDITIONS, CONDITION_TIPS } from '../data';

export default function HealthTab({ userProfile }) {
  const { conditions = [] } = userProfile;

  const presetIds  = conditions.filter(c => typeof c === 'string' && HEALTH_CONDITIONS.find(h => h.id === c));
  const customIds  = conditions.filter(c => typeof c === 'string' && !HEALTH_CONDITIONS.find(h => h.id === c));

  if (conditions.length === 0) {
    return (
      <EmptyState
        emoji="🌿"
        title="Your health profile"
        body="You haven't added any health conditions yet. Head to your profile to add them, and we'll show you personalised daily tips here."
      />
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 24, marginBottom: 6 }}>Your daily tips</h2>
        <p style={{ color: C.textMuted, fontSize: 14 }}>
          Personalised to your health conditions — small actions with real impact.
        </p>
      </div>

      {presetIds.map(condId => {
        const meta = HEALTH_CONDITIONS.find(h => h.id === condId);
        const tips = CONDITION_TIPS[condId] || [];
        return (
          <ConditionCard key={condId} emoji={meta.emoji} title={meta.label} tips={tips} />
        );
      })}

      {customIds.map(custom => (
        <ConditionCard
          key={custom}
          emoji="💙"
          title={custom}
          tips={null}
          customMessage={`We don't have preset tips for "${custom}" yet, but your companion in the Chat tab can offer personalised guidance whenever you need it.`}
        />
      ))}
    </div>
  );
}

function ConditionCard({ emoji, title, tips, customMessage }) {
  return (
    <div className="animate-in" style={{
      background: C.surface, borderRadius: 20, boxShadow: C.shadow,
      border: `1px solid ${C.border}`, padding: '22px 24px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <span style={{ fontSize: 28 }}>{emoji}</span>
        <h3 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 18 }}>{title}</h3>
      </div>

      {customMessage ? (
        <p style={{ color: C.textMuted, fontSize: 14, lineHeight: 1.7, fontStyle: 'italic' }}>
          {customMessage}
        </p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {tips.map((tip, i) => (
            <div key={i} style={{
              display: 'flex', gap: 12, alignItems: 'flex-start',
              padding: '12px 14px', borderRadius: 12,
              background: i % 2 === 0 ? C.bg : C.sagePale,
            }}>
              <span style={{
                width: 22, height: 22, borderRadius: '50%',
                background: C.primaryPale, color: C.primary,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 700, flexShrink: 0, marginTop: 1,
              }}>{i + 1}</span>
              <p style={{ fontSize: 14, color: C.text, lineHeight: 1.65, margin: 0 }}>{tip}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EmptyState({ emoji, title, body }) {
  return (
    <div style={{
      textAlign: 'center', padding: '64px 24px',
      background: C.surface, borderRadius: 20, boxShadow: C.shadow,
    }}>
      <div style={{ fontSize: 44, marginBottom: 14 }}>{emoji}</div>
      <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 22, marginBottom: 10 }}>{title}</h2>
      <p style={{ color: C.textMuted, fontSize: 15, lineHeight: 1.6, maxWidth: 360, margin: '0 auto' }}>{body}</p>
    </div>
  );
}
