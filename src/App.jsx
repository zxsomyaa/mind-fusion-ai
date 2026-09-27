import { useState, useCallback, useEffect } from 'react';
import { C, FONT, applyTheme } from './data';
import { DEFAULT_CONFIG, PRESETS, checkConnection } from './ai';
import Onboarding from './components/Onboarding';
import HomeTab from './components/HomeTab';
import ChatTab from './components/ChatTab';
import HealthTab from './components/HealthTab';
import NutritionTab from './components/NutritionTab';
import JournalTab from './components/JournalTab';
import InsightsTab from './components/InsightsTab';
import ExercisesTab from './components/ExercisesTab';
import AffirmTab from './components/AffirmTab';
import SupportTab from './components/SupportTab';

const TABS = [
  { id: 'today',     label: 'Today',     emoji: '🏠' },
  { id: 'chat',      label: 'Chat',      emoji: '💬' },
  { id: 'health',    label: 'Health',    emoji: '🌿' },
  { id: 'nutrition', label: 'Nutrition', emoji: '🥗' },
  { id: 'journal',   label: 'Journal',   emoji: '📓' },
  { id: 'insights',  label: 'Insights',  emoji: '✨' },
  { id: 'exercises', label: 'Exercises', emoji: '🧘' },
  { id: 'affirm',    label: 'Affirm',    emoji: '💕' },
  { id: 'support',   label: 'Support',   emoji: '🤝' },
];

function load(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
  catch { return fallback; }
}

/** Everything this browser has stored for the signed-in user, as one file -
 * the web equivalent of the desktop app's "Export all your data" button. */
function exportData(user, profile) {
  const payload = {
    user, profile,
    moodHistory: load('mf_mood_history', []),
    journal: load('mf_journal', []),
    habitLog: load('mf_habit_log', {}),
    sleepLog: load('mf_sleep_log', {}),
    affirmFavorites: load('mf_affirm_favs', []),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `mind_fusion_export_${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function App() {
  const [user,        setUser]        = useState(() => load('mf_user', null));
  const [userProfile, setUserProfile] = useState(() => load('mf_profile', null));
  const [aiConfig,    setAiConfig]    = useState(() => load('mf_ai_config', DEFAULT_CONFIG));
  const [activeTab,   setActiveTab]   = useState(() => location.hash.slice(1) || 'today');
  const [moodHistory, setMoodHistory] = useState(() => load('mf_mood_history', []));
  const [showSettings, setShowSettings] = useState(false);
  const [theme,       setTheme]       = useState(() => load('mf_theme', 'light'));
  // null = unknown, true = connected, false = disconnected
  const [connected,   setConnected]   = useState(null);

  // Ping the local server on mount and whenever config changes
  useEffect(() => {
    setConnected(null);
    checkConnection(aiConfig)
      .then(() => setConnected(true))
      .catch(() => setConnected(false));
  }, [aiConfig]);

  // Applying a theme mutates the shared `C` colour object in place (see
  // data.js) rather than replacing it, so this effect also updates the one
  // thing React doesn't re-render for us - the page background behind
  // everything - and the signed-in shell below is fully remounted (via
  // `key={theme}`) so every component picks up the new values, the same way
  // the desktop app rebuilds its whole window on a theme switch.
  useEffect(() => {
    applyTheme(theme);
    document.body.style.background = C.bg;
    document.body.style.color = C.text;
    localStorage.setItem('mf_theme', JSON.stringify(theme));
  }, [theme]);

  const toggleTheme = () => setTheme(t => (t === 'dark' ? 'light' : 'dark'));

  const addMoodEntry = useCallback((moodObj) => {
    setMoodHistory(prev => {
      const updated = [...prev, { ...moodObj, timestamp: Date.now() }].slice(-100);
      localStorage.setItem('mf_mood_history', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const handleSignup = (userData) => {
    localStorage.setItem('mf_user', JSON.stringify(userData));
    setUser(userData);
  };

  const handleProfileComplete = (profile) => {
    localStorage.setItem('mf_profile', JSON.stringify(profile));
    setUserProfile(profile);
  };

  const handleSignOut = () => {
    localStorage.removeItem('mf_user');
    setUser(null);
  };

  const saveConfig = (cfg) => {
    localStorage.setItem('mf_ai_config', JSON.stringify(cfg));
    setAiConfig(cfg);
    setShowSettings(false);
  };

  if (!user || !userProfile) {
    return <Onboarding onSignup={handleSignup} onProfileComplete={handleProfileComplete} existingUser={user} />;
  }

  const statusDot = connected === true  ? { color: C.sage,    label: 'Local AI connected' }
                  : connected === false ? { color: '#E07A5F', label: 'Local AI not connected' }
                  : { color: '#D4A017', label: 'Checking…' };

  const navBtnStyle = (active) => ({
    display: 'flex', alignItems: 'center', gap: 10, width: '100%',
    background: active ? C.primaryPale : 'none', border: 'none', borderRadius: 10,
    padding: '9px 12px', textAlign: 'left', cursor: 'pointer',
    color: active ? C.primary : C.text, fontWeight: active ? 600 : 400,
    fontSize: 14, fontFamily: FONT.sans,
  });

  const iconBtnStyle = { width: 30, height: 30, borderRadius: 8, border: `1px solid ${C.border}`, background: 'none', cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center' };

  return (
    // Keyed by theme: a light<->dark switch fully remounts the signed-in shell,
    // the same way the desktop app rebuilds its whole window on a theme change.
    <div key={theme} className="mf-shell" style={{ minHeight: '100vh', background: C.bg, fontFamily: FONT.sans }}>
      {/* Sidebar */}
      <aside className="mf-sidebar" style={{
        width: 232, flexShrink: 0, borderRight: `1px solid ${C.border}`,
        padding: '20px 16px 16px', display: 'flex', flexDirection: 'column', gap: 4,
        background: C.surface,
      }}>
        <div className="mf-sidebar-brand">
          <div style={{ fontSize: 19, fontWeight: 700, color: C.primary }}>🌿 Mind Fusion</div>
          <div style={{ color: C.textMuted, fontSize: 11, paddingBottom: 14 }}>your wellbeing companion</div>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={navBtnStyle(activeTab === tab.id)}>
              <span style={{ fontSize: 16 }}>{tab.emoji}</span>{tab.label}
            </button>
          ))}
        </nav>

        <div className="mf-sidebar-spacer" style={{ flex: 1 }} />

        <div className="mf-sidebar-footer" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: statusDot.color }}>
            ● {statusDot.label}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
              background: C.primaryPale, display: 'flex', alignItems: 'center',
              justifyContent: 'center', fontSize: 14, fontWeight: 700, color: C.primary,
            }}>
              {(user.name || '?').charAt(0).toUpperCase()}
            </div>
            <span style={{ fontWeight: 600, fontSize: 13, color: C.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user.name}</span>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setShowSettings(true)} title="Local AI settings" style={iconBtnStyle}>⚙</button>
            <button onClick={toggleTheme} title="Switch light / dark theme" style={iconBtnStyle}>{theme === 'dark' ? '☀️' : '🌙'}</button>
            <button onClick={() => exportData(user, userProfile)} title="Export all your data as JSON" style={iconBtnStyle}>⬇</button>
          </div>

          <button onClick={handleSignOut} style={{ ...navBtnStyle(false), justifyContent: 'center', border: `1.5px solid ${C.border}` }}>
            Sign out
          </button>
        </div>
      </aside>

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <main style={{ flex: 1, maxWidth: 920, margin: '0 auto', width: '100%', padding: '24px 20px 32px' }}>
        {activeTab === 'today'     && <HomeTab      userName={user.name} userProfile={userProfile} moodHistory={moodHistory} addMoodEntry={addMoodEntry} onNavigate={setActiveTab} />}
        {activeTab === 'chat'      && <ChatTab      userProfile={userProfile} aiConfig={aiConfig} connected={connected} addMoodEntry={addMoodEntry} onOpenSettings={() => setShowSettings(true)} />}
        {activeTab === 'health'    && <HealthTab    userProfile={userProfile} />}
        {activeTab === 'nutrition' && <NutritionTab aiConfig={aiConfig} connected={connected} onOpenSettings={() => setShowSettings(true)} />}
        {activeTab === 'journal'   && <JournalTab   addMoodEntry={addMoodEntry} onGoToChat={() => setActiveTab('chat')} />}
        {activeTab === 'insights'  && <InsightsTab  moodHistory={moodHistory} />}
        {activeTab === 'exercises' && <ExercisesTab />}
        {activeTab === 'affirm'    && <AffirmTab />}
        {activeTab === 'support'   && <SupportTab   userProfile={userProfile} />}
      </main>

      {/* Footer */}
      <footer style={{
        textAlign: 'center', padding: '14px 20px',
        fontSize: 11, color: C.textMuted, fontStyle: 'italic',
        background: C.surface, borderTop: `1px solid ${C.border}`,
      }}>
        Mind Fusion supports your wellbeing but does not replace professional medical or mental health care.
      </footer>
      </div>

      {showSettings && (
        <AISettingsModal
          config={aiConfig}
          onSave={saveConfig}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
}

// ─── AI Settings Modal ────────────────────────────────────────
function AISettingsModal({ config, onSave, onClose }) {
  const [form,      setForm]      = useState({ ...config });
  const [testing,   setTesting]   = useState(false);
  const [testResult, setTestResult] = useState(null); // null | { ok, message, models }

  const applyPreset = (key) => {
    const p = PRESETS[key];
    setForm(f => ({ ...f, provider: key === 'custom' ? 'openai' : key, baseUrl: p.baseUrl, chatModel: p.chatModel, visionModel: p.visionModel }));
    setTestResult(null);
  };

  const test = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const models = await checkConnection(form);
      setTestResult({ ok: true, message: `Connected! ${models.length} model${models.length !== 1 ? 's' : ''} available.`, models });
    } catch (e) {
      setTestResult({ ok: false, message: e.message || 'Could not reach the server.' });
    } finally {
      setTesting(false);
    }
  };

  const inp = (hasErr) => ({
    width: '100%', padding: '10px 14px', borderRadius: 10,
    border: `1.5px solid ${hasErr ? '#E07A5F' : C.border}`,
    background: C.surface, fontSize: 13, color: C.text,
    outline: 'none', fontFamily: FONT.sans,
    onFocus: e => (e.target.style.borderColor = C.primary),
    onBlur:  e => (e.target.style.borderColor = C.border),
  });

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(61,44,30,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000, padding: 20,
    }}>
      <div className="animate-in" style={{
        background: C.bg, borderRadius: 24, padding: 28,
        width: '100%', maxWidth: 480, boxShadow: C.shadowLg,
        maxHeight: '90vh', overflowY: 'auto',
      }}>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, marginBottom: 4, fontSize: 22 }}>
          Local AI settings
        </h2>
        <p style={{ color: C.textMuted, fontSize: 13, lineHeight: 1.6, marginBottom: 20 }}>
          Connect to a local AI server running on your machine. No data leaves your device.
        </p>

        {/* Preset buttons */}
        <p style={{ fontSize: 12, fontWeight: 600, color: C.textMuted, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 }}>
          Quick setup
        </p>
        <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
          {Object.entries(PRESETS).map(([key, p]) => (
            <button key={key} onClick={() => applyPreset(key)} style={{
              padding: '7px 16px', borderRadius: 20,
              border: `1.5px solid ${C.border}`, background: C.surface,
              color: C.text, fontSize: 12, cursor: 'pointer', fontFamily: FONT.sans,
              transition: 'border-color 0.15s',
            }}
              onMouseEnter={e => (e.target.style.borderColor = C.primary)}
              onMouseLeave={e => (e.target.style.borderColor = C.border)}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Hint */}
        {PRESETS[form.provider]?.hint && (
          <div style={{
            background: C.sagePale, borderRadius: 10, padding: '10px 14px',
            fontSize: 12, color: C.sage, marginBottom: 18, lineHeight: 1.55,
          }}>
            💡 {PRESETS[form.provider]?.hint || PRESETS.custom.hint}
          </div>
        )}

        {/* Fields */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={labelStyle}>Server URL</label>
            <input {...inp(false)} value={form.baseUrl} onChange={e => setForm(f => ({ ...f, baseUrl: e.target.value }))} placeholder="http://localhost:11434" />
          </div>
          <div>
            <label style={labelStyle}>Chat model</label>
            <input {...inp(false)} value={form.chatModel} onChange={e => setForm(f => ({ ...f, chatModel: e.target.value }))} placeholder="llama3.2" />
            {testResult?.models?.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 8 }}>
                {testResult.models.slice(0, 8).map(m => (
                  <button key={m} onClick={() => setForm(f => ({ ...f, chatModel: m }))} style={{
                    padding: '3px 10px', borderRadius: 20, fontSize: 11, cursor: 'pointer',
                    border: `1px solid ${form.chatModel === m ? C.primary : C.border}`,
                    background: form.chatModel === m ? C.primaryPale : C.surface,
                    color: form.chatModel === m ? C.primary : C.textMuted,
                    fontFamily: FONT.sans,
                  }}>{m}</button>
                ))}
              </div>
            )}
          </div>
          <div>
            <label style={labelStyle}>Vision model <span style={{ fontWeight: 400 }}>(for meal analysis)</span></label>
            <input {...inp(false)} value={form.visionModel} onChange={e => setForm(f => ({ ...f, visionModel: e.target.value }))} placeholder="llava" />
            <p style={{ fontSize: 11, color: C.textMuted, marginTop: 4 }}>
              Ollama: try <code style={{ background: C.border, padding: '1px 5px', borderRadius: 4 }}>llava</code>, <code style={{ background: C.border, padding: '1px 5px', borderRadius: 4 }}>moondream</code>, or <code style={{ background: C.border, padding: '1px 5px', borderRadius: 4 }}>llava-phi3</code>
            </p>
          </div>
        </div>

        {/* Test result */}
        {testResult && (
          <div style={{
            marginTop: 16, padding: '10px 14px', borderRadius: 10, fontSize: 13,
            background: testResult.ok ? C.sagePale : '#FCEEE9',
            color: testResult.ok ? C.sage : '#C0392B',
            border: `1px solid ${testResult.ok ? C.sageLight : '#F4B8AA'}`,
          }}>
            {testResult.ok ? '✓ ' : '✗ '}{testResult.message}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: 10, marginTop: 22 }}>
          <button onClick={test} disabled={testing} style={{
            flex: 1, padding: '11px', borderRadius: 12,
            border: `2px solid ${C.border}`, background: 'none',
            color: testing ? C.textMuted : C.text,
            cursor: testing ? 'wait' : 'pointer', fontFamily: FONT.sans, fontSize: 13,
          }}>
            {testing ? 'Testing…' : 'Test connection'}
          </button>
          <button onClick={onClose} style={{
            padding: '11px 18px', borderRadius: 12,
            border: `2px solid ${C.border}`, background: 'none',
            color: C.textMuted, cursor: 'pointer', fontFamily: FONT.sans, fontSize: 13,
          }}>
            Cancel
          </button>
          <button onClick={() => onSave(form)} style={{
            flex: 2, padding: '11px', borderRadius: 12, border: 'none',
            background: C.primary, color: '#FFF', cursor: 'pointer',
            fontFamily: FONT.sans, fontSize: 13, fontWeight: 600,
          }}>
            Save settings
          </button>
        </div>
      </div>
    </div>
  );
}

const labelStyle = {
  display: 'block', fontSize: 12, fontWeight: 600,
  color: C.text, marginBottom: 6,
};
