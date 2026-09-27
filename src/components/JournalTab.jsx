import { useState, useEffect } from 'react';
import { C, FONT, JOURNAL_PROMPTS, detectMood } from '../data';

function load(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } }

export default function JournalTab({ addMoodEntry, onGoToChat }) {
  const [promptIdx, setPromptIdx] = useState(() => Math.floor(Math.random() * JOURNAL_PROMPTS.length));
  const [text,      setText]      = useState('');
  const [liveMood,  setLiveMood]  = useState(null);
  const [entries,   setEntries]   = useState(() => load('mf_journal', []));
  const [saved,     setSaved]     = useState(false);
  const [shareText, setShareText] = useState('');

  useEffect(() => {
    if (text.trim().length > 10) setLiveMood(detectMood(text));
    else setLiveMood(null);
  }, [text]);

  const nextPrompt = () => setPromptIdx(i => (i + 1) % JOURNAL_PROMPTS.length);

  const saveEntry = () => {
    if (!text.trim()) return;
    const mood = liveMood || detectMood(text);
    const entry = {
      id: Date.now(), text, mood: mood.mood, moodEmoji: mood.emoji,
      moodColor: mood.color, timestamp: Date.now(),
      prompt: JOURNAL_PROMPTS[promptIdx],
    };
    const updated = [entry, ...entries].slice(0, 50);
    setEntries(updated);
    localStorage.setItem('mf_journal', JSON.stringify(updated));
    addMoodEntry(mood);
    setSaved(true);
    setText('');
    setTimeout(() => setSaved(false), 2800);
  };

  const shareWithAI = () => {
    setShareText(text);
    onGoToChat();
  };

  const deleteEntry = (id) => {
    const updated = entries.filter(e => e.id !== id);
    setEntries(updated);
    localStorage.setItem('mf_journal', JSON.stringify(updated));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 24, marginBottom: 6 }}>Journal</h2>
        <p style={{ color: C.textMuted, fontSize: 14 }}>A quiet space to write without judgment.</p>
      </div>

      {/* Prompt card */}
      <div style={{
        background: `linear-gradient(135deg, ${C.primaryPale}, ${C.sagePale})`,
        borderRadius: 20, padding: '22px 24px', border: `1px solid ${C.border}`,
      }}>
        <p style={{ fontSize: 12, color: C.primary, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 }}>
          Today's prompt
        </p>
        <p style={{ fontFamily: FONT.serif, fontSize: 18, color: C.text, lineHeight: 1.6, marginBottom: 14 }}>
          "{JOURNAL_PROMPTS[promptIdx]}"
        </p>
        <button onClick={nextPrompt} style={{
          background: 'none', border: `1px solid ${C.primary}`,
          borderRadius: 20, padding: '5px 14px', color: C.primary,
          fontSize: 12, cursor: 'pointer', fontFamily: FONT.sans,
        }}>
          Show another ↺
        </button>
      </div>

      {/* Writing area */}
      <div style={{
        background: C.surface, borderRadius: 20, boxShadow: C.shadow,
        border: `1px solid ${C.border}`, overflow: 'hidden',
      }}>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Start writing here… no pressure, no judgment."
          style={{
            width: '100%', minHeight: 180, padding: '20px',
            border: 'none', outline: 'none', resize: 'vertical',
            fontSize: 15, lineHeight: 1.7, color: C.text,
            fontFamily: FONT.sans, background: 'transparent',
          }}
        />
        {liveMood && (
          <div style={{
            padding: '10px 20px', borderTop: `1px solid ${C.border}`,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ fontSize: 14 }}>{liveMood.emoji}</span>
            <span style={{
              fontSize: 12, padding: '3px 12px', borderRadius: 100,
              background: liveMood.bg, color: liveMood.color, fontWeight: 500,
            }}>
              {liveMood.label}
            </span>
            <span style={{ fontSize: 12, color: C.textMuted }}>detected as you write</span>
          </div>
        )}
        <div style={{
          padding: '12px 20px', borderTop: `1px solid ${C.border}`,
          display: 'flex', gap: 10, justifyContent: 'flex-end', alignItems: 'center',
        }}>
          {saved && <span style={{ fontSize: 13, color: C.sage }}>✓ Entry saved</span>}
          <button onClick={shareWithAI} disabled={!text.trim()} style={{
            padding: '9px 18px', borderRadius: 10,
            border: `2px solid ${C.sage}`, background: 'none',
            color: C.sage, cursor: text.trim() ? 'pointer' : 'not-allowed',
            fontSize: 13, fontFamily: FONT.sans, opacity: text.trim() ? 1 : 0.5,
          }}>
            Share with companion →
          </button>
          <button onClick={saveEntry} disabled={!text.trim()} style={{
            padding: '9px 18px', borderRadius: 10, border: 'none',
            background: text.trim() ? C.primary : C.border,
            color: '#FFF', cursor: text.trim() ? 'pointer' : 'not-allowed',
            fontSize: 13, fontFamily: FONT.sans, fontWeight: 600,
          }}>
            Save entry
          </button>
        </div>
      </div>

      {/* Past entries */}
      {entries.length > 0 && (
        <div>
          <h3 style={{ fontFamily: FONT.serif, color: C.text, fontSize: 18, marginBottom: 14 }}>
            Past entries
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {entries.map(entry => (
              <div key={entry.id} className="animate-in" style={{
                background: C.surface, borderRadius: 16, boxShadow: C.shadow,
                border: `1px solid ${C.border}`, padding: '16px 20px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      padding: '3px 10px', borderRadius: 100, fontSize: 12, fontWeight: 500,
                      background: entry.moodColor + '22', color: entry.moodColor,
                    }}>
                      {entry.moodEmoji} {entry.mood}
                    </span>
                    <span style={{ fontSize: 11, color: C.textMuted }}>
                      {new Date(entry.timestamp).toLocaleDateString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <button onClick={() => deleteEntry(entry.id)} style={{
                    background: 'none', border: 'none', color: C.textMuted,
                    cursor: 'pointer', fontSize: 16, lineHeight: 1,
                  }}>×</button>
                </div>
                {entry.prompt && (
                  <p style={{ fontSize: 12, color: C.textMuted, fontStyle: 'italic', marginBottom: 6 }}>
                    "{entry.prompt}"
                  </p>
                )}
                <p style={{ fontSize: 14, color: C.text, lineHeight: 1.65 }}>
                  {entry.text.length > 200 ? entry.text.slice(0, 200) + '…' : entry.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
