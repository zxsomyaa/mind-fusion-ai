import { useState } from 'react';
import { C, FONT, COUNTRIES, LANGUAGES, AGE_GROUPS, HEALTH_CONDITIONS, HABITS, GOALS } from '../data';

const TOTAL = 5;

const btn = (extra = {}) => ({
  padding: '13px 28px', borderRadius: 14, border: 'none',
  cursor: 'pointer', fontFamily: FONT.sans, fontSize: 15, fontWeight: 600,
  transition: 'opacity 0.15s, transform 0.1s',
  ...extra,
});

const primary = (disabled) => btn({
  background: disabled ? '#D9CEC6' : C.primary,
  color: '#FFF', cursor: disabled ? 'not-allowed' : 'pointer',
});

const ghost = () => btn({
  background: 'none', border: `2px solid ${C.border}`,
  color: C.textMuted,
});

const card = {
  background: C.surface, borderRadius: 20,
  boxShadow: C.shadow, padding: '32px 28px',
  width: '100%', maxWidth: 480,
};

function Chip({ label, emoji, selected, onClick }) {
  return (
    <button onClick={onClick} style={{
      padding: '8px 14px', borderRadius: 100,
      border: `2px solid ${selected ? C.primary : C.border}`,
      background: selected ? C.primaryPale : C.surface,
      color: selected ? C.primary : C.text,
      cursor: 'pointer', fontSize: 13, fontWeight: selected ? 600 : 400,
      display: 'flex', alignItems: 'center', gap: 6,
      transition: 'all 0.15s', fontFamily: FONT.sans,
    }}>
      {emoji && <span>{emoji}</span>}
      {label}
    </button>
  );
}

export default function Onboarding({ onSignup, onProfileComplete, existingUser }) {
  const [screen, setScreen]   = useState(existingUser ? 'step' : 'welcome');
  const [form, setForm]       = useState({ name: '', email: '', password: '' });
  const [formErr, setFormErr] = useState({});
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
    if (!form.name.trim())          errs.name     = 'Please enter your name';
    if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = 'Enter a valid email';
    if (form.password.length < 6)   errs.password = 'At least 6 characters';
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

  const wrap = {
    minHeight: '100vh', background: C.bg,
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    padding: 20, fontFamily: FONT.sans,
  };

  const fadeStyle = {
    opacity: anim ? 1 : 0,
    transform: anim ? 'translateY(0)' : 'translateY(10px)',
    transition: 'opacity 0.22s ease, transform 0.22s ease',
    width: '100%', maxWidth: 480,
  };

  // ── Welcome ─────────────────────────────────────────────────
  if (screen === 'welcome') return (
    <div style={wrap}>
      <div style={{ ...fadeStyle, textAlign: 'center' }}>
        <div style={{ fontSize: 56, marginBottom: 12 }}>🌿</div>
        <h1 style={{ fontFamily: FONT.serif, fontSize: 34, color: C.primary, marginBottom: 8 }}>
          Mind Fusion
        </h1>
        <p style={{ color: C.textMuted, fontSize: 16, lineHeight: 1.6, marginBottom: 36 }}>
          A warm, thoughtful companion for your mental<br />and physical wellbeing journey.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center' }}>
          <button onClick={() => transition(() => setScreen('signup'))} style={primary(false)}>
            Get started
          </button>
          <button onClick={() => transition(() => setScreen('signin'))} style={ghost()}>
            I already have an account
          </button>
        </div>
        <p style={{ marginTop: 32, fontSize: 11, color: C.textMuted, fontStyle: 'italic' }}>
          Supports your wellbeing · Does not replace professional care
        </p>
      </div>
    </div>
  );

  // ── Sign In ──────────────────────────────────────────────────
  if (screen === 'signin') return (
    <div style={wrap}>
      <div style={{ ...fadeStyle, ...card }}>
        <button onClick={() => transition(() => setScreen('welcome'))}
          style={{ background: 'none', border: 'none', color: C.textMuted, cursor: 'pointer', marginBottom: 16, fontSize: 13 }}>
          ← Back
        </button>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, marginBottom: 6 }}>Welcome back</h2>
        <p style={{ color: C.textMuted, fontSize: 14, marginBottom: 24 }}>Sign in to continue your journey.</p>
        {['email', 'password'].map(f => (
          <div key={f} style={{ marginBottom: 16 }}>
            <input
              type={f === 'password' ? 'password' : 'email'}
              placeholder={f.charAt(0).toUpperCase() + f.slice(1)}
              value={form[f]}
              onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))}
              style={inputStyle(!!formErr[f])}
            />
            {formErr[f] && <p style={errStyle}>{formErr[f]}</p>}
          </div>
        ))}
        <button onClick={() => {
          if (!form.email.trim() || !form.password) { setFormErr({ email: 'Please enter your details' }); return; }
          const nameFromEmail = form.email.split('@')[0].replace(/[._-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
          onSignup({ name: nameFromEmail, email: form.email });
          transition(() => setScreen('step'));
        }} style={{ ...primary(false), width: '100%', marginTop: 8 }}>
          Sign in
        </button>
      </div>
    </div>
  );

  // ── Sign Up ──────────────────────────────────────────────────
  if (screen === 'signup') return (
    <div style={wrap}>
      <div style={{ ...fadeStyle, ...card }}>
        <button onClick={() => transition(() => setScreen('welcome'))}
          style={{ background: 'none', border: 'none', color: C.textMuted, cursor: 'pointer', marginBottom: 16, fontSize: 13 }}>
          ← Back
        </button>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, marginBottom: 6 }}>Create your account</h2>
        <p style={{ color: C.textMuted, fontSize: 14, marginBottom: 24 }}>Just the basics — we'll personalise from here.</p>
        {[
          { key: 'name', placeholder: 'Your name', type: 'text' },
          { key: 'email', placeholder: 'Email', type: 'email' },
          { key: 'password', placeholder: 'Password (6+ characters)', type: 'password' },
        ].map(({ key, placeholder, type }) => (
          <div key={key} style={{ marginBottom: 14 }}>
            <input
              type={type}
              placeholder={placeholder}
              value={form[key]}
              onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
              style={inputStyle(!!formErr[key])}
            />
            {formErr[key] && <p style={errStyle}>{formErr[key]}</p>}
          </div>
        ))}
        <button onClick={handleSignup} style={{ ...primary(false), width: '100%', marginTop: 8 }}>
          Create account
        </button>
      </div>
    </div>
  );

  // ── Steps ────────────────────────────────────────────────────
  const progressPct = (step / TOTAL) * 100;

  const stepTitle = ['Where are you based?', 'How old are you?', 'Any health conditions?', 'Current habits?', 'Your goals'][step - 1];
  const stepSub   = [
    'We use this to personalise support resources.',
    'Different life stages have different needs.',
    'Select any that apply — including ones not listed.',
    'Which of these are already part of your routine?',
    'Pick up to 3 — we\'ll build around them.',
  ][step - 1];

  return (
    <div style={wrap}>
      <div style={{ ...fadeStyle }}>
        {/* Progress */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: C.textMuted }}>Step {step} of {TOTAL}</span>
            <span style={{ fontSize: 12, color: C.primary, fontWeight: 600 }}>{Math.round(progressPct)}%</span>
          </div>
          <div style={{ height: 5, background: C.border, borderRadius: 10 }}>
            <div style={{
              height: '100%', borderRadius: 10,
              background: `linear-gradient(90deg, ${C.primary}, ${C.primaryLight})`,
              width: `${progressPct}%`, transition: 'width 0.4s ease',
            }} />
          </div>
        </div>

        <div style={card}>
          <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 22, marginBottom: 6 }}>{stepTitle}</h2>
          <p style={{ color: C.textMuted, fontSize: 14, marginBottom: 22 }}>{stepSub}</p>

          {/* Step 1: Country + Language */}
          {step === 1 && (
            <div>
              <div style={{ position: 'relative', marginBottom: 14 }}>
                <input
                  placeholder="Search countries…"
                  value={countryQ}
                  onChange={e => setCountryQ(e.target.value)}
                  style={inputStyle(false)}
                />
              </div>
              <div style={{ maxHeight: 200, overflowY: 'auto', display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
                {filteredCountries.map(c => (
                  <Chip key={c.code} label={`${c.flag} ${c.name}`}
                    selected={profile.country === c.code}
                    onClick={() => setProfile(p => ({ ...p, country: c.code }))} />
                ))}
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

          {/* Step 2: Age Group */}
          {step === 2 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {AGE_GROUPS.map(ag => (
                <button key={ag.id} onClick={() => setProfile(p => ({ ...p, ageGroup: ag.id }))}
                  style={{
                    padding: '12px 20px', borderRadius: 12, cursor: 'pointer',
                    border: `2px solid ${profile.ageGroup === ag.id ? C.primary : C.border}`,
                    background: profile.ageGroup === ag.id ? C.primaryPale : C.surface,
                    color: profile.ageGroup === ag.id ? C.primary : C.text,
                    fontSize: 15, fontWeight: profile.ageGroup === ag.id ? 600 : 400,
                    fontFamily: FONT.sans, transition: 'all 0.15s',
                  }}>
                  {ag.label}
                </button>
              ))}
            </div>
          )}

          {/* Step 3: Health Conditions */}
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
                  placeholder="Add a condition not listed…"
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
                No conditions? That's perfectly fine — skip ahead.
              </p>
            </div>
          )}

          {/* Step 4: Habits */}
          {step === 4 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {HABITS.map(h => (
                <Chip key={h.id} label={h.label} emoji={h.emoji}
                  selected={profile.habits.includes(h.id)}
                  onClick={() => toggleArr('habits', h.id)} />
              ))}
            </div>
          )}

          {/* Step 5: Goals */}
          {step === 5 && (
            <div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {GOALS.map(g => {
                  const isSelected = profile.goals.includes(g.id);
                  const atMax = profile.goals.length >= 3 && !isSelected;
                  return (
                    <Chip key={g.id} label={g.label} emoji={g.emoji}
                      selected={isSelected}
                      onClick={() => { if (!atMax) toggleArr('goals', g.id); }} />
                  );
                })}
              </div>
              {profile.goals.length >= 3 && (
                <p style={{ marginTop: 10, fontSize: 12, color: C.primary }}>
                  Maximum 3 goals selected. Deselect one to change.
                </p>
              )}
            </div>
          )}

          {/* Navigation */}
          <div style={{ display: 'flex', gap: 12, marginTop: 28 }}>
            <button onClick={goBack} style={ghost()}>
              ← Back
            </button>
            <button onClick={goNext} disabled={!canProceed()} style={{ ...primary(!canProceed()), flex: 1 }}>
              {step === TOTAL ? 'Begin my journey →' : 'Continue →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const inputStyle = (hasErr) => ({
  width: '100%', padding: '12px 16px', borderRadius: 12,
  border: `2px solid ${hasErr ? '#E07A5F' : C.border}`,
  background: C.surface, fontSize: 14, color: C.text, outline: 'none',
  fontFamily: FONT.sans, transition: 'border-color 0.2s',
});

const errStyle = { fontSize: 12, color: '#E07A5F', marginTop: 4 };
