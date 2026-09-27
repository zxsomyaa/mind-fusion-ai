import { useState, useRef, useEffect, useCallback } from 'react';
import { C, FONT, detectMood, MOOD_FALLBACKS, getPersonalizedRecs, LANGUAGES } from '../data';
import { chatAI } from '../ai';

function buildSystemPrompt(profile) {
  const condLabels = (profile.conditions || [])
    .map(c => (typeof c === 'string' ? c : c.label || c.id))
    .join(', ') || 'none mentioned';
  const goalLabels = (profile.goals || []).join(', ') || 'general wellbeing';
  const lang = LANGUAGES.find(l => l.code === (profile.language || 'en'));
  const langName = lang ? lang.name : 'English';

  return `You are a warm, caring wellbeing companion. You speak like a trusted, thoughtful friend — not a therapist, not a chatbot.

About the person you're talking with:
- Health conditions: ${condLabels}
- Wellbeing goals: ${goalLabels}
- Age group: ${profile.ageGroup || 'not specified'}

Your tone and style:
- Conversational and genuine, never scripted or clinical.
- Respond to the specific thing they said — not to a general category.
- 3–5 sentences. Never use bullet points.
- Never begin with "I hear you", "I understand", "That sounds", or any formulaic opener.
- Vary your openers. Ask a follow-up occasionally but not every single message.
- Reference actual details they've shared. Be present with them.
- If they seem distressed, gently acknowledge it before anything else.
${profile.language && profile.language !== 'en' ? `\nIMPORTANT: Respond entirely in ${langName}. The user has selected ${langName} as their language.` : ''}`;
}

function buildMessages(messages) {
  // Enforce alternating user/assistant, starting with user — only send {role, content}
  const filtered = messages
    .filter(m => m.role === 'user' || m.role === 'assistant')
    .map(m => ({ role: m.role, content: m.content }));
  const result = [];
  let expected = 'user';
  for (const msg of filtered) {
    if (msg.role === expected) {
      result.push(msg);
      expected = expected === 'user' ? 'assistant' : 'user';
    }
  }
  if (result.length && result[0].role !== 'user') result.shift();
  return result;
}

const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

export default function ChatTab({ userProfile, aiConfig, connected, addMoodEntry, onOpenSettings }) {
  const [messages,  setMessages]  = useState([]);
  const [input,     setInput]     = useState('');
  const [loading,   setLoading]   = useState(false);
  const [listening, setListening] = useState(false);
  const [interim,   setInterim]   = useState('');
  const [voiceErr,  setVoiceErr]  = useState('');
  const [lastMood,  setLastMood]  = useState(null);
  const [lastRecId, setLastRecId] = useState(null);
  const [recs,      setRecs]      = useState([]);
  const [showRecs,  setShowRecs]  = useState(false);
  const [expanded,  setExpanded]  = useState(null);
  const bottomRef  = useRef(null);
  const recRef     = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);

  const startVoice = useCallback(() => {
    if (!SpeechRec) { setVoiceErr('Voice input is not supported in this browser.'); return; }
    const lang = LANGUAGES.find(l => l.code === (userProfile?.language || 'en'));
    const r = new SpeechRec();
    r.continuous = true;
    r.interimResults = true;
    r.lang = lang?.locale || 'en-US';
    recRef.current = r;

    r.onresult = (e) => {
      let final = '', interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        e.results[i].isFinal ? (final += t) : (interim += t);
      }
      if (final) setInput(p => (p + ' ' + final).trim());
      setInterim(interim);
    };
    r.onerror = (e) => {
      if (e.error === 'not-allowed') setVoiceErr('Microphone access denied — please allow it in your browser.');
      else if (e.error !== 'no-speech') setVoiceErr('Voice recognition ran into an issue.');
      setListening(false);
    };
    r.onend = () => { setListening(false); setInterim(''); };

    try { r.start(); setListening(true); setVoiceErr(''); }
    catch { setVoiceErr('Could not start voice input.'); }
  }, [userProfile]);

  const stopVoice = useCallback(() => {
    recRef.current?.stop(); setListening(false); setInterim('');
  }, []);

  const send = useCallback(async (text) => {
    const content = text.trim();
    if (!content || loading) return;

    const detected = detectMood(content);
    setLastMood(detected);
    addMoodEntry(detected);

    const newRecs = getPersonalizedRecs(userProfile, detected.mood, lastRecId);
    setRecs(newRecs);
    setShowRecs(true);
    if (newRecs[0]) setLastRecId(newRecs[0].id);

    const userMsg = { id: Date.now(), role: 'user', content, mood: detected };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const apiMsgs = buildMessages([...messages, userMsg]);
      const reply = await chatAI(aiConfig, apiMsgs, buildSystemPrompt(userProfile));
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'assistant', content: reply }]);
    } catch {
      const fallback = MOOD_FALLBACKS[detected.mood] || MOOD_FALLBACKS.calm;
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'assistant', content: fallback, isOffline: true }]);
    } finally {
      setLoading(false);
    }
  }, [messages, loading, aiConfig, userProfile, lastRecId, addMoodEntry]);

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); }
  };

  return (
    <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 0 }}>

        {/* Not-connected banner */}
        {connected === false && (
          <div style={{
            background: '#FEF3E6', border: '1px solid #F4C97A', borderRadius: 14,
            padding: '12px 16px', marginBottom: 16,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
          }}>
            <div>
              <p style={{ fontSize: 13, color: '#9B6000', fontWeight: 600, marginBottom: 2 }}>
                Local AI not detected
              </p>
              <p style={{ fontSize: 12, color: '#C77B2A' }}>
                Start Ollama or LM Studio on your machine, then check your settings.
              </p>
            </div>
            <button onClick={onOpenSettings} style={{
              background: '#C77B2A', color: '#FFF', border: 'none', borderRadius: 8,
              padding: '7px 14px', fontSize: 12, cursor: 'pointer', fontFamily: FONT.sans,
              flexShrink: 0,
            }}>
              Settings
            </button>
          </div>
        )}

        {/* Greeting */}
        {messages.length === 0 && (
          <div className="animate-in" style={{
            textAlign: 'center', padding: '48px 24px',
            background: C.surface, borderRadius: 20, boxShadow: C.shadow, marginBottom: 16,
          }}>
            <div style={{ fontSize: 42, marginBottom: 12 }}>🌿</div>
            <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 22, marginBottom: 8 }}>
              Hello, {userProfile?.name || 'friend'}
            </h2>
            <p style={{ color: C.textMuted, fontSize: 15, lineHeight: 1.6 }}>
              How are you feeling today? Share anything on your mind —
              I'm here to listen and offer support.
            </p>
          </div>
        )}

        {/* Messages */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 16 }}>
          {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div style={{
          background: C.surface, borderRadius: 18, boxShadow: C.shadow,
          border: `1px solid ${C.border}`, overflow: 'hidden', position: 'sticky', bottom: 0,
        }}>
          {(interim || voiceErr) && (
            <div style={{
              padding: '8px 16px', fontSize: 13,
              color: voiceErr ? '#E07A5F' : C.textMuted,
              borderBottom: `1px solid ${C.border}`,
              fontStyle: voiceErr ? 'normal' : 'italic',
            }}>
              {voiceErr || `🎤 ${interim}`}
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Share what's on your mind…"
              rows={2}
              style={{
                flex: 1, border: 'none', outline: 'none', resize: 'none',
                padding: '14px 16px', fontSize: 14, fontFamily: FONT.sans,
                background: 'transparent', color: C.text, lineHeight: 1.5,
              }}
            />
            <div style={{ display: 'flex', alignItems: 'center', padding: '10px 12px', gap: 8 }}>
              {SpeechRec && (
                <button onClick={listening ? stopVoice : startVoice} title={listening ? 'Stop' : 'Voice input'} style={{
                  width: 36, height: 36, borderRadius: '50%', border: 'none', cursor: 'pointer',
                  background: listening ? '#FCEEE9' : C.primaryPale,
                  color: listening ? '#E07A5F' : C.primary,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
                  animation: listening ? 'pulse 1.4s ease infinite' : 'none',
                }}>
                  {listening ? '⏹' : '🎤'}
                </button>
              )}
              <button onClick={() => send(input)} disabled={!input.trim() || loading} style={{
                width: 36, height: 36, borderRadius: '50%', border: 'none', cursor: 'pointer',
                background: input.trim() ? C.primary : C.border,
                color: '#FFF', display: 'flex', alignItems: 'center',
                justifyContent: 'center', fontSize: 16, transition: 'background 0.15s',
              }}>↑</button>
            </div>
          </div>
        </div>

        {lastMood && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, marginTop: 10,
            padding: '7px 14px', background: lastMood.bg,
            borderRadius: 100, alignSelf: 'flex-start',
            fontSize: 12, color: lastMood.color, fontWeight: 500,
          }}>
            <span>{lastMood.emoji}</span>
            <span>Mood: <strong>{lastMood.label}</strong></span>
          </div>
        )}
      </div>

      {/* Recommendation sidebar */}
      {showRecs && recs.length > 0 && (
        <div className="animate-in" style={{ width: 260, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: C.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              For you right now
            </p>
            <button onClick={() => setShowRecs(false)} style={{
              background: 'none', border: 'none', color: C.textMuted, cursor: 'pointer', fontSize: 16,
            }}>×</button>
          </div>
          {recs.map(rec => (
            <RecCard key={rec.id} rec={rec}
              expanded={expanded === rec.id}
              onToggle={() => setExpanded(expanded === rec.id ? null : rec.id)} />
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div className="animate-in" style={{
      display: 'flex', gap: 10,
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      alignItems: 'flex-end',
    }}>
      {!isUser && (
        <div style={{
          width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
          background: C.sagePale, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 17,
        }}>🌿</div>
      )}
      <div style={{
        maxWidth: '72%',
        padding: isUser ? '11px 16px' : '13px 18px',
        borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
        background: isUser ? C.primary : C.surface,
        color: isUser ? '#FFF' : C.text,
        boxShadow: isUser ? 'none' : C.shadow,
        fontSize: 14, lineHeight: 1.65,
        fontFamily: isUser ? FONT.sans : FONT.serif,
        border: isUser ? 'none' : `1px solid ${C.border}`,
      }}>
        {msg.content}
        {msg.isOffline && (
          <span style={{ fontSize: 11, color: isUser ? 'rgba(255,255,255,0.6)' : C.textMuted, display: 'block', marginTop: 4 }}>
            (offline response)
          </span>
        )}
      </div>
      {isUser && msg.mood && (
        <div style={{
          width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
          background: msg.mood.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
        }}>
          {msg.mood.emoji}
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
      <div style={{ width: 34, height: 34, borderRadius: '50%', background: C.sagePale, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 17 }}>🌿</div>
      <div style={{ padding: '13px 18px', borderRadius: '18px 18px 18px 4px', background: C.surface, boxShadow: C.shadow, border: `1px solid ${C.border}` }}>
        <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
          {[0, 1, 2].map(i => (
            <div key={i} style={{ width: 7, height: 7, borderRadius: '50%', background: C.sageLight, animation: `pulse 1.4s ease ${i * 0.2}s infinite` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

function RecCard({ rec, expanded, onToggle }) {
  return (
    <div style={{ background: C.surface, borderRadius: 16, boxShadow: C.shadow, border: `1px solid ${C.border}`, overflow: 'hidden' }}>
      <button onClick={onToggle} style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 10, textAlign: 'left' }}>
        <span style={{ fontSize: 22, flexShrink: 0 }}>{rec.emoji}</span>
        <p style={{ flex: 1, fontSize: 13, fontWeight: 600, color: C.text, margin: 0 }}>{rec.title}</p>
        <span style={{ color: C.textMuted, fontSize: 14, transform: expanded ? 'rotate(90deg)' : 'rotate(0)', transition: 'transform 0.2s' }}>›</span>
      </button>
      {expanded && (
        <div style={{ padding: '0 14px 14px', fontSize: 12, color: C.textMuted, lineHeight: 1.6, borderTop: `1px solid ${C.border}`, paddingTop: 10 }}>
          {rec.body}
        </div>
      )}
    </div>
  );
}
