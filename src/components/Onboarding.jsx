import { useState } from 'react';
import { C, FONT, COUNTRIES, LANGUAGES, AGE_GROUPS, HEALTH_CONDITIONS, HABITS, GOALS } from '../data';

const TOTAL = 5;
const STEP_LABELS = ['Location', 'Age', 'Health', 'Habits', 'Goals'];

const btn = (extra = {}) => ({
  padding: '13px 24px', borderRadius: 14, border: 'none',
  cursor: 'pointer', fontFamily: FONT.sans, fontSize: 15, fontWeight: 600,
  transition: 'opacity 0.15s, transform 0.1s',
  ...extra,
});

const primary = (disabled) => btn({
  background: disabled ? '#D9CEC6' : C.primary,
  color: '#FFF', cursor: disabled ? 'not-allowed' : 'pointer',
  width: '100%',
});

const ghost = () => btn({
  background: 'none', border: `2px solid ${C.border}`,
  color: C.textMuted, width: '100%',
});

const linkBtn = { background: 'none', border: 'none', color: C.textMuted, cursor: 'pointer', fontSize: 13, fontFamily: FONT.sans, padding: 0 };

function Chip({ label, emoji, selected, onClick, disabled }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: '8px 14px', borderRadius: 100,
      border: `2px solid ${selected ? C.primary : C.border}`,
      background: selected ? C.primaryPale : C.surface,
      color: disabled ? C.textMuted : (selected ? C.primary : C.text),
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      fontSize: 13, fontWeight: selected ? 600 : 400,
      display: 'flex', alignItems: 'center', gap: 6,
      transition: 'all 0.15s', fontFamily: FONT.sans,
    }}>
      {emoji && <span>{emoji}</span>}
      {label}
    </button>
  );
}

function Field({ label, error, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 5 }}>{label}</label>
      {children}
      {error && <p style={errStyle}>{error}</p>}
    </div>
  );
}

/** The branded left panel — persistent across every onboarding screen, hidden on narrow viewports. */
function Hero() {
  return (
    <div className="mf-onboarding-hero" style={{
      flex: '0 0 42%', minWidth: 380, maxWidth: 560,
      background: `linear-gradient(135deg, ${C.primary}, ${C.primaryLight})`,
      color: '#FFF', flexDirection: 'column',
      padding: '48px 52px 40px', fontFamily: FONT.sans,
    }}>
      <div style={{ fontSize: 19, fontWeight: 700 }}>🌿 &nbsp;Mind Fusion</div>
      <div style={{ flex: 1, minHeight: 40 }} />
      <h1 style={{ fontSize: 38, fontWeight: 800, lineHeight: 1.15, margin: 0 }}>
        Feel understood.<br />Feel lighter.
      </h1>
      <p style={{ fontSize: 15, opacity: 0.94, marginTop: 14, lineHeight: 1.5, maxWidth: 420 }}>
        A private, gentle companion for your mind and body — powered by AI that runs
        entirely on your own computer.
      </p>
      <div style={{ marginTop: 30, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {[
          ['💬', 'Talk things through, any time of day'],
          ['📓', 'Journal, and track your mood, habits and sleep'],
          ['🔒', 'Everything stays on your device'],
        ].map(([emoji, text]) => (
          <div key={text} style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{
              width: 38, height: 38, borderRadius: 19, flexShrink: 0,
              background: 'rgba(255,255,255,0.22)', display: 'flex',
              alignItems: 'center', justifyContent: 'center', fontSize: 17,
            }}>{emoji}</div>
            <span style={{ fontSize: 14, fontWeight: 600 }}>{text}</span>
          </div>
        ))}
      </div>
      <div style={{ flex: 1, minHeight: 40 }} />
      <div style={{ fontSize: 11, opacity: 0.85 }}>Supports your wellbeing · does not replace professional care</div>
    </div>
  );
}

/** Numbered-dot progress indicator for the profile wizard. */
function StepIndicator({ current }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 22 }}>
      {STEP_LABELS.map((label, i) => {
        const done = i < current, isCurrent = i === current;
        return (
          <div key={label} style={{ display: 'flex', alignItems: 'center', flex: i < STEP_LABELS.length - 1 ? 1 : undefined }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <div style={{
                width: 26, height: 26, borderRadius: 13, flexShrink: 0,
                border: `2px solid ${done || isCurrent ? C.primary : C.border}`,
                background: done ? C.primary : C.surface,
                color: done ? '#FFF' : (isCurrent ? C.primary : C.textMuted),
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 700,
              }}>{done ? '✓' : i + 1}</div>
              <span style={{ fontSize: 10, color: isCurrent ? C.primary : C.textMuted, fontWeight: isCurrent ? 700 : 400, whiteSpace: 'nowrap' }}>{label}</span>
            </div>
            {i < STEP_LABELS.length - 1 && (
              <div style={{ flex: 1, height: 3, marginBottom: 16, background: i < current ? C.primary : C.border }} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function Onboarding({ onSignup, onProfileComplete, existingUser }) {
  const [screen, setScreen]   = useState(existingUser ? 'step' : 'welcome');
  const [form, setForm]       = useState({ name: '', email: '', password: '' });
  const [formErr, setFormErr] = useState({});
  const [showPw, setShowPw]   = useState(false);
  const [step, setStep]       = useState(1);
  const [anim, setAnim]       = useState(true);

  const [profile, setProfile] = useState({
    country: null, language: 'en',
    ageGroup: null,
    conditions: [], customCondition: '',
    habits: [], goals: [],
  });
  const [countryQ, setCountryQ] = useState('');

  const transition = (fn) => {
    setAnim(false);
    setTimeout(() => { fn(); setAnim(true); }, 220);
  };

  const toggleArr = (key, id) => setProfile(p => ({
    ...p,
    [key]: p[key].includes(id) ? p[key].filter(x => x !== id) : [...p[key], id],
  }));

  const addCustomCondition = () => {
    const val = profile.customCondition.trim();
    if (!val || profile.conditions.includes(val)) return;
    setProfile(p => ({ ...p, conditions: [...p.conditions, val], customCondition: '' }));
  };

  const validateSignup = () => {
    const errs = {};
    if (!form.name.trim())          errs.name     = 'Please tell us your name.';
    if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = 'Enter a valid email address.';
    if (form.password.length < 6)   errs.password = 'Use at least 6 characters.';
    setFormErr(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSignup = () => {
    if (!validateSignup()) return;
    onSignup({ name: form.name, email: form.email });
    transition(() => setScreen('step'));
  };

  const handleFinish = () => {
    onProfileComplete({
      country: profile.country,
      language: profile.language,
      ageGroup: profile.ageGroup,
      conditions: profile.conditions,
      habits: profile.habits,
      goals: profile.goals,
    });
  };

  const goNext = () => {
    if (step < TOTAL) transition(() => setStep(s => s + 1));
    else handleFinish();
  };

  const goBack = () => {
    if (step > 1) transition(() => setStep(s => s - 1));
    else transition(() => setScreen('welcome'));
  };

  const canProceed = () => {
    if (step === 1) return !!profile.country;
    if (step === 2) return !!profile.ageGroup;
    return true;
  };

  const filteredCountries = COUNTRIES.filter(c =>
    c.name.toLowerCase().includes(countryQ.toLowerCase())
  );

  const fadeStyle = {
    opacity: anim ? 1 : 0,
    transform: anim ? 'translateY(0)' : 'translateY(10px)',
    transition: 'opacity 0.22s ease, transform 0.22s ease',
    width: '100%', maxWidth: 440,
  };

  let content;

  // ── Welcome ─────────────────────────────────────────────────
  if (screen === 'welcome') content = (
    <div style={{ ...fadeStyle, textAlign: 'center' }}>
      <div style={{
        width: 68, height: 68, borderRadius: 34, background: C.primaryPale,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 32, margin: '0 auto 18px',
      }}>🌿</div>
      <h1 style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: 30, color: C.primary, marginBottom: 10 }}>
        Welcome to Mind Fusion
      </h1>
      <p style={{ color: C.textMuted, fontSize: 15, lineHeight: 1.6, marginBottom: 26 }}>
        Let's set things up in about a minute, so everything you see is made for you.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <button onClick={() => transition(() => setScreen('signup'))} style={primary(false)}>
          Get started →
        </button>
        <button onClick={() => transition(() => setScreen('signin'))} style={ghost()}>
          I already have an account
        </button>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center', marginTop: 22 }}>
        {['🔒 Stays on your device', '🤖 Local AI', '🌙 Light & dark'].map(t => (
          <span key={t} style={{
            background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12,
            padding: '4px 12px', color: C.textMuted, fontSize: 12,
          }}>{t}</span>
        ))}
      </div>
      <p style={{ marginTop: 26, fontSize: 11, color: C.textMuted, fontStyle: 'italic' }}>
        Supports your wellbeing · does not replace professional care
      </p>
    </div>
  );

  // ── Sign in ──────────────────────────────────────────────────
  else if (screen === 'signin') content = (
    <div style={fadeStyle}>
      <button onClick={() => transition(() => setScreen('welcome'))} style={{ ...linkBtn, marginBottom: 18 }}>← Back</button>
      <h2 style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: 26, color: C.primary, marginBottom: 8 }}>Welcome back</h2>
      <p style={{ color: C.textMuted, fontSize: 14, marginBottom: 22 }}>Sign in to pick up where you left off.</p>

      <Field label="Email" error={formErr.email}>
        <input type="email" placeholder="you@example.com" value={form.email}
          onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
          style={inputStyle(!!formErr.email)} />
      </Field>
      <Field label="Password" error={formErr.password}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input type={showPw ? 'text' : 'password'} placeholder="Your password" value={form.password}
            onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
            style={{ ...inputStyle(!!formErr.password), flex: 1 }} />
          <button onClick={() => setShowPw(s => !s)} style={{ ...linkBtn, border: `2px solid ${C.border}`, borderRadius: 12, padding: '0 14px' }}>
            {showPw ? 'Hide' : 'Show'}
          </button>
        </div>
      </Field>

      <button onClick={() => {
        if (!form.email.trim() || !form.password) { setFormErr({ email: !form.email.trim() ? 'Enter the email you signed up with.' : undefined, password: !form.password ? 'Please enter your password.' : undefined }); return; }
        const nameFromEmail = form.email.split('@')[0].replace(/[._-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        onSignup({ name: nameFromEmail, email: form.email });
        transition(() => setScreen('step'));
      }} style={{ ...primary(false), marginTop: 6 }}>
        Sign in →
      </button>

      <p style={{ textAlign: 'center', marginTop: 18, fontSize: 13, color: C.textMuted }}>
        New here? <button onClick={() => transition(() => setScreen('signup'))} style={{ ...linkBtn, color: C.primary, fontWeight: 600 }}>Create an account</button>
      </p>
    </div>
  );

  // ── Sign up ──────────────────────────────────────────────────
  else if (screen === 'signup') content = (
    <div style={fadeStyle}>
      <button onClick={() => transition(() => setScreen('welcome'))} style={{ ...linkBtn, marginBottom: 18 }}>← Back</button>
      <h2 style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: 26, color: C.primary, marginBottom: 8 }}>Create your account</h2>
      <p style={{ color: C.textMuted, fontSize: 14, marginBottom: 22 }}>Just the basics — we'll personalise everything from here.</p>

      <Field label="Your name" error={formErr.name}>
        <input type="text" placeholder="e.g. Priya" value={form.name}
          onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
          style={inputStyle(!!formErr.name)} />
      </Field>
      <Field label="Email" error={formErr.email}>
        <input type="email" placeholder="you@example.com" value={form.email}
          onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
          style={inputStyle(!!formErr.email)} />
      </Field>
      <Field label="Password" error={formErr.password}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input type={showPw ? 'text' : 'password'} placeholder="At least 6 characters" value={form.password}
            onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
            style={{ ...inputStyle(!!formErr.password), flex: 1 }} />
          <button onClick={() => setShowPw(s => !s)} style={{ ...linkBtn, border: `2px solid ${C.border}`, borderRadius: 12, padding: '0 14px' }}>
            {showPw ? 'Hide' : 'Show'}
          </button>
        </div>
      </Field>

      <button onClick={handleSignup} style={{ ...primary(false), marginTop: 6 }}>
        Create account →
      </button>

      <p style={{ textAlign: 'center', marginTop: 18, fontSize: 13, color: C.textMuted }}>
        Already have an account? <button onClick={() => transition(() => setScreen('signin'))} style={{ ...linkBtn, color: C.primary, fontWeight: 600 }}>Sign in</button>
      </p>
    </div>
  );

  // ── Profile wizard steps ────────────────────────────────────
  else {
    const stepTitle = ['Where are you based?', 'How old are you?', 'Any health conditions?', 'Which habits do you already have?', 'What would you like to work on?'][step - 1];
    const stepSub   = [
      'We use this to show the right support resources for your country.',
      'Different stages of life come with different needs.',
      'Select any that apply, or add your own. Skip if none.',
      "We'll turn these into a daily checklist for you.",
      "Pick up to 3 — we'll build around them.",
    ][step - 1];
    const emoji = ['🌍', '🎂', '🩺', '🌱', '🎯'][step - 1];

    content = (
      <div style={{ ...fadeStyle, maxWidth: 460 }}>
        <StepIndicator current={step - 1} />
        <div style={{ display: 'flex', gap: 14, marginBottom: 18 }}>
          <span style={{ fontSize: 28 }}>{emoji}</span>
          <div>
            <h2 style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: 20, color: C.primary, marginBottom: 4 }}>{stepTitle}</h2>
            <p style={{ color: C.textMuted, fontSize: 13 }}>{stepSub}</p>
          </div>
        </div>

        <div style={{ minHeight: 220 }}>
          {step === 1 && (
            <div>
              <input placeholder="🔍  Search countries…" value={countryQ}
                onChange={e => setCountryQ(e.target.value)}
                style={{ ...inputStyle(false), marginBottom: 14 }} />
              <div style={{ maxHeight: 190, overflowY: 'auto', display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
                {filteredCountries.map(c => (
                  <Chip key={c.code} label={`${c.flag} ${c.name}`}
                    selected={profile.country === c.code}
                    onClick={() => setProfile(p => ({ ...p, country: c.code }))} />
                ))}
                {filteredCountries.length === 0 && <p style={{ fontSize: 13, color: C.textMuted }}>No country matches that search.</p>}
              </div>
              <p style={{ fontSize: 13, color: C.textMuted, marginBottom: 10, fontWeight: 500 }}>Preferred language</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {LANGUAGES.map(l => (
                  <Chip key={l.code} label={l.name}
                    selected={profile.language === l.code}
                    onClick={() => setProfile(p => ({ ...p, language: l.code }))} />
                ))}
              </div>
            </div>
          )}

          {step === 2 && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {AGE_GROUPS.map(ag => (
                <button key={ag.id} onClick={() => setProfile(p => ({ ...p, ageGroup: ag.id }))}
                  style={{
                    padding: '14px 16px', borderRadius: 12, cursor: 'pointer',
                    border: `2px solid ${profile.ageGroup === ag.id ? C.primary : C.border}`,
                    background: profile.ageGroup === ag.id ? C.primaryPale : C.surface,
                    color: profile.ageGroup === ag.id ? C.primary : C.text,
                    fontSize: 15, fontWeight: profile.ageGroup === ag.id ? 600 : 400,
                    fontFamily: FONT.sans, transition: 'all 0.15s', textAlign: 'left',
                  }}>
                  {ag.label}
                </button>
              ))}
            </div>
          )}

          {step === 3 && (
            <div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
                {HEALTH_CONDITIONS.map(hc => (
                  <Chip key={hc.id} label={hc.label} emoji={hc.emoji}
                    selected={profile.conditions.includes(hc.id)}
                    onClick={() => toggleArr('conditions', hc.id)} />
                ))}
                {profile.conditions.filter(c => !HEALTH_CONDITIONS.find(h => h.id === c)).map(custom => (
                  <Chip key={custom} label={custom}
                    selected={true}
                    onClick={() => setProfile(p => ({ ...p, conditions: p.conditions.filter(x => x !== custom) }))} />
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  placeholder="Add a condition that isn't listed…"
                  value={profile.customCondition}
                  onChange={e => setProfile(p => ({ ...p, customCondition: e.target.value }))}
                  onKeyDown={e => { if (e.key === 'Enter') addCustomCondition(); }}
                  style={{ ...inputStyle(false), flex: 1 }}
                />
                <button onClick={addCustomCondition} style={{
                  ...btn({ background: C.primaryPale, color: C.primary }),
                  padding: '10px 18px', fontSize: 13,
                }}>Add</button>
              </div>
              <p style={{ fontSize: 12, color: C.textMuted, marginTop: 8 }}>
                No conditions? That's perfectly fine - just continue.
              </p>
            </div>
          )}

          {step === 4 && (
            <div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {HABITS.map(h => (
                  <Chip key={h.id} label={h.label} emoji={h.emoji}
                    selected={profile.habits.includes(h.id)}
                    onClick={() => toggleArr('habits', h.id)} />
                ))}
              </div>
              <p style={{ fontSize: 12, color: C.textMuted, marginTop: 12 }}>
                Each one becomes a daily checkbox on your Today page, with its own streak.
              </p>
            </div>
          )}

          {step === 5 && (
            <div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {GOALS.map(g => {
                  const isSelected = profile.goals.includes(g.id);
                  const atMax = profile.goals.length >= 3 && !isSelected;
                  return (
                    <Chip key={g.id} label={g.label} emoji={g.emoji}
                      selected={isSelected} disabled={atMax}
                      onClick={() => { if (!atMax) toggleArr('goals', g.id); }} />
                  );
                })}
              </div>
              <p style={{ marginTop: 12, fontSize: 12, color: C.primary, fontWeight: 600 }}>
                {profile.goals.length} of 3 chosen{profile.goals.length === 3 ? ' — untick one to change' : ''}
              </p>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
          <button onClick={goBack} style={{ ...ghost(), width: 'auto', flex: '0 0 auto', padding: '13px 22px' }}>← Back</button>
          <button onClick={goNext} disabled={!canProceed()} style={{ ...primary(!canProceed()), flex: 1 }}>
            {step === TOTAL ? 'Begin my journey →' : 'Continue →'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mf-onboarding">
      <Hero />
      <div className="mf-onboarding-form" style={{ padding: '32px 24px' }}>
        {content}
      </div>
    </div>
  );
}

const inputStyle = (hasErr) => ({
  width: '100%', padding: '12px 16px', borderRadius: 12,
  border: `2px solid ${hasErr ? '#E07A5F' : C.border}`,
  background: C.surface, fontSize: 14, color: C.text, outline: 'none',
  fontFamily: FONT.sans, transition: 'border-color 0.2s', minHeight: 46,
});

const errStyle = { fontSize: 11, color: '#E07A5F', marginTop: 5 };
