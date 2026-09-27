import { C, FONT, SUPPORT_RESOURCES, COUNTRIES } from '../data';

const SECTION_META = {
  crisis:   { label: 'Crisis support',       emoji: '🆘', border: '#F4B8AA', bg: '#FCEEE9' },
  mental:   { label: 'Mental health',         emoji: '🧠', border: C.sageLight, bg: C.sagePale },
  physical: { label: 'Physical health',       emoji: '🏥', border: '#A8DADC44', bg: '#EAF6F7' },
};

export default function SupportTab({ userProfile }) {
  const countryCode = userProfile?.country || 'DEFAULT';
  const resources   = SUPPORT_RESOURCES[countryCode] || SUPPORT_RESOURCES.DEFAULT;
  const countryMeta = COUNTRIES.find(c => c.code === countryCode);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 24, marginBottom: 6 }}>Support resources</h2>
        <p style={{ color: C.textMuted, fontSize: 14 }}>
          {countryMeta
            ? `Resources for ${countryMeta.flag} ${countryMeta.name}.`
            : 'Global resources for wherever you are.'}
          {' '}Reach out — help is closer than it may feel.
        </p>
      </div>

      <div style={{
        background: '#FEF3E6', borderRadius: 16, padding: '14px 18px',
        border: '1px solid #F4C97A', fontSize: 14, color: '#9B6000', lineHeight: 1.6,
      }}>
        <strong>In immediate danger?</strong> Please call your local emergency services (999, 911, 112, or your country's number). These resources are for additional support, not emergencies.
      </div>

      {['crisis', 'mental', 'physical'].map(section => {
        const items = resources[section];
        if (!items?.length) return null;
        const meta = SECTION_META[section];
        return (
          <div key={section}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <span style={{ fontSize: 20 }}>{meta.emoji}</span>
              <h3 style={{ fontFamily: FONT.serif, color: C.text, fontSize: 18 }}>{meta.label}</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {items.map((item, i) => (
                <ResourceCard key={i} item={item} bg={meta.bg} border={meta.border} />
              ))}
            </div>
          </div>
        );
      })}

      <div style={{
        background: C.surface, borderRadius: 16, boxShadow: C.shadow,
        border: `1px solid ${C.border}`, padding: '18px 20px',
        display: 'flex', gap: 14, alignItems: 'flex-start',
      }}>
        <span style={{ fontSize: 24 }}>💙</span>
        <div>
          <p style={{ fontSize: 14, fontWeight: 600, color: C.text, marginBottom: 4 }}>
            You don't have to face this alone
          </p>
          <p style={{ fontSize: 13, color: C.textMuted, lineHeight: 1.65 }}>
            Reaching out — whether to a friend, a helpline, or a professional — takes real courage.
            Whatever you're going through, support is available and you deserve it.
          </p>
        </div>
      </div>
    </div>
  );
}

function ResourceCard({ item, bg, border }) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        textDecoration: 'none', display: 'block',
        background: bg, borderRadius: 14, padding: '16px 18px',
        border: `1px solid ${border}`, transition: 'box-shadow 0.2s',
      }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = C.shadow}
      onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 14, fontWeight: 600, color: C.text, marginBottom: 2 }}>{item.name}</p>
          {item.contact && (
            <p style={{ fontSize: 15, fontWeight: 700, color: C.primary, marginBottom: 4, fontFamily: FONT.serif }}>
              {item.contact}
            </p>
          )}
          {item.note && (
            <p style={{ fontSize: 12, color: C.textMuted }}>{item.note}</p>
          )}
        </div>
        <span style={{ color: C.primary, fontSize: 18, flexShrink: 0 }}>↗</span>
      </div>
    </a>
  );
}
