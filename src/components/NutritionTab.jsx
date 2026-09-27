import { useState, useRef, useEffect } from 'react';
import { C, FONT } from '../data';
import { visionAI, checkConnection, pullModel } from '../ai';

const NUTRITION_PROMPT = `Look at this meal photo and respond with ONLY a raw JSON object — no markdown, no code fences, no explanation. Use exactly this structure:
{"foods":["item1"],"calories_estimate":450,"nutrients":{"protein":22,"carbs":55,"fat":14,"fibre":6},"mood_impact":"one sentence about energy/mood","recommendation":"one practical suggestion","balance_score":7}
Estimate realistically. balance_score is 1-10.`;

export default function NutritionTab({ aiConfig, connected, onOpenSettings }) {
  const [image,     setImage]     = useState(null); // { url, base64, mimeType }
  const [analysing, setAnalysing] = useState(false);
  const [result,    setResult]    = useState(null);
  const [error,     setError]     = useState('');
  const [modelReady, setModelReady] = useState(null); // null unknown, true available, false missing
  const [pulling,    setPulling]    = useState(false);
  const [pullPct,    setPullPct]    = useState(null);
  const fileRef = useRef(null);

  useEffect(() => {
    if (aiConfig.provider !== 'ollama' || connected !== true) { setModelReady(null); return; }
    let cancelled = false;
    checkConnection(aiConfig)
      .then(models => {
        if (cancelled) return;
        const base = aiConfig.visionModel.split(':')[0];
        setModelReady(models.some(m => m.split(':')[0] === base));
      })
      .catch(() => { if (!cancelled) setModelReady(null); });
    return () => { cancelled = true; };
  }, [aiConfig, connected]);

  // Auto-pull the vision model in the background as soon as we know it's missing.
  useEffect(() => {
    if (modelReady !== false || pulling) return;
    let cancelled = false;
    setPulling(true); setPullPct(null);
    pullModel(aiConfig, aiConfig.visionModel, (p) => {
      if (!cancelled) setPullPct(p.total && p.completed ? Math.round((p.completed / p.total) * 100) : null);
    })
      .then(() => { if (!cancelled) setModelReady(true); })
      .catch((e) => { if (!cancelled) setError(`Couldn't prepare the vision model: ${e.message}`); })
      .finally(() => { if (!cancelled) setPulling(false); });
    return () => { cancelled = true; };
  }, [modelReady]);

  const handleFile = (file) => {
    if (!file || !file.type.startsWith('image/')) { setError('Please select an image file.'); return; }
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        // Resize to max 768px — keeps base64 small enough for local models
        const MAX = 768;
        const scale = Math.min(1, MAX / Math.max(img.width, img.height));
        const w = Math.round(img.width * scale);
        const h = Math.round(img.height * scale);
        const canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        canvas.getContext('2d').drawImage(img, 0, 0, w, h);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
        const base64 = dataUrl.split(',')[1];
        setImage({ url: dataUrl, base64, mimeType: 'image/jpeg' });
        setResult(null); setError('');
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  };

  const handleDrop = (e) => { e.preventDefault(); handleFile(e.dataTransfer.files[0]); };

  const analyse = async () => {
    if (!image) return;
    setAnalysing(true); setError('');

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 180000); // 3 min timeout
      let raw;
      try {
        raw = await visionAI(aiConfig, image.base64, image.mimeType, NUTRITION_PROMPT, controller.signal);
      } finally {
        clearTimeout(timeout);
      }

      // Strip markdown code fences if present, then extract JSON object
      const cleaned = raw.replace(/```(?:json)?/gi, '').trim();
      const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
      if (!jsonMatch) throw new Error(`Model returned non-JSON: ${raw.slice(0, 120)}`);
      setResult(JSON.parse(jsonMatch[0]));
    } catch (e) {
      if (e.name === 'AbortError') {
        setError('Analysis timed out (3 min). Try a smaller or clearer photo.');
      } else if (e.message?.includes('fetch') || e.message?.includes('Failed') || e.message?.includes('NetworkError')) {
        setError("Couldn't reach the vision model — is Ollama running? Check settings.");
      } else {
        setError(`Analysis failed: ${e.message}`);
      }
    } finally {
      setAnalysing(false);
    }
  };

  const reset = () => { setImage(null); setResult(null); setError(''); };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 24, marginBottom: 6 }}>Meal analysis</h2>
        <p style={{ color: C.textMuted, fontSize: 14 }}>
          Upload a photo of your meal to get a nutrition breakdown and wellbeing insights.
        </p>
      </div>

      {/* Vision model status — only shown while preparing, or if disconnected */}
      {(pulling || connected === false) && (
        <div style={{
          background: pulling ? '#FDF6E3' : C.sagePale, borderRadius: 12, padding: '10px 16px',
          fontSize: 12, color: pulling ? '#8A6D1D' : C.sage, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap',
        }}>
          <span style={{ flexShrink: 0 }}>{pulling ? '⏳' : '💡'}</span>
          {pulling ? (
            <span>Getting things ready{pullPct != null ? ` (${pullPct}%)` : '…'} — this only happens once.</span>
          ) : (
            <span>
              Not connected to your local AI server.{' '}
              <button onClick={onOpenSettings} style={{ background: 'none', border: 'none', color: C.sage, textDecoration: 'underline', cursor: 'pointer', fontSize: 12, fontFamily: FONT.sans }}>Check settings</button>
            </span>
          )}
        </div>
      )}

      {!result ? (
        <div style={{ background: C.surface, borderRadius: 20, boxShadow: C.shadow, border: `1px solid ${C.border}`, padding: 28 }}>
          {!image ? (
            <div
              onDrop={handleDrop}
              onDragOver={e => e.preventDefault()}
              onClick={() => fileRef.current?.click()}
              style={{
                border: `2px dashed ${C.border}`, borderRadius: 16,
                padding: '48px 24px', textAlign: 'center', cursor: 'pointer',
                transition: 'border-color 0.2s, background 0.2s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = C.primary; e.currentTarget.style.background = C.primaryPale; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = C.border;  e.currentTarget.style.background = 'transparent'; }}
            >
              <div style={{ fontSize: 44, marginBottom: 14 }}>📸</div>
              <p style={{ color: C.primary, fontWeight: 600, fontSize: 16, marginBottom: 6 }}>Upload a meal photo</p>
              <p style={{ color: C.textMuted, fontSize: 13 }}>Click to browse or drag & drop · JPG, PNG, WebP</p>
              <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => handleFile(e.target.files[0])} />
            </div>
          ) : (
            <div>
              <img src={image.url} alt="Meal" style={{ width: '100%', maxHeight: 320, objectFit: 'cover', borderRadius: 14, marginBottom: 20 }} />
              {error && (
                <div style={{ padding: '10px 14px', background: '#FCEEE9', borderRadius: 10, marginBottom: 16, color: '#C0392B', fontSize: 13 }}>
                  {error}
                </div>
              )}
              <div style={{ display: 'flex', gap: 12 }}>
                <button onClick={reset} style={{
                  flex: 1, padding: '12px', borderRadius: 12,
                  border: `2px solid ${C.border}`, background: 'none',
                  color: C.textMuted, cursor: 'pointer', fontFamily: FONT.sans, fontSize: 14,
                }}>Upload different photo</button>
                <button onClick={analyse} disabled={analysing} style={{
                  flex: 2, padding: '12px', borderRadius: 12, border: 'none',
                  background: analysing ? C.border : C.primary,
                  color: '#FFF', cursor: analysing ? 'wait' : 'pointer',
                  fontFamily: FONT.sans, fontSize: 14, fontWeight: 600,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}>
                  {analysing
                    ? <><span style={{ animation: 'spin 0.8s linear infinite', display: 'inline-block' }}>⏳</span> Analysing… (may take 1–2 min)</>
                    : '🔍 Analyse meal'}
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="animate-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <img src={image.url} alt="Meal" style={{ width: 180, height: 140, objectFit: 'cover', borderRadius: 16, flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 200, background: C.surface, borderRadius: 16, boxShadow: C.shadow, border: `1px solid ${C.border}`, padding: 20 }}>
              <p style={{ fontSize: 12, color: C.textMuted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 }}>Foods detected</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {(result.foods || []).map((f, i) => (
                  <span key={i} style={{ padding: '4px 12px', borderRadius: 100, background: C.primaryPale, color: C.primary, fontSize: 13 }}>{f}</span>
                ))}
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12 }}>
            {[
              { label: 'Calories', value: result.calories_estimate, unit: 'kcal', color: C.primary },
              { label: 'Protein',  value: result.nutrients?.protein, unit: 'g',  color: C.sage },
              { label: 'Carbs',    value: result.nutrients?.carbs,   unit: 'g',  color: '#E97D3F' },
              { label: 'Fat',      value: result.nutrients?.fat,     unit: 'g',  color: '#B5838D' },
              { label: 'Fibre',    value: result.nutrients?.fibre,   unit: 'g',  color: '#74C69D' },
            ].map(item => (
              <div key={item.label} style={{
                background: C.surface, borderRadius: 14, padding: '16px 14px',
                boxShadow: C.shadow, border: `1px solid ${C.border}`, textAlign: 'center',
              }}>
                <p style={{ fontSize: 22, fontWeight: 700, color: item.color, fontFamily: FONT.serif }}>{item.value ?? '—'}</p>
                <p style={{ fontSize: 11, color: C.textMuted }}>{item.unit}</p>
                <p style={{ fontSize: 12, color: C.text, fontWeight: 500 }}>{item.label}</p>
              </div>
            ))}
          </div>

          <div style={{ background: C.surface, borderRadius: 16, boxShadow: C.shadow, border: `1px solid ${C.border}`, padding: '18px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <p style={{ fontSize: 14, fontWeight: 600, color: C.text }}>Wellness score</p>
              <p style={{ fontSize: 18, fontWeight: 700, color: C.primary, fontFamily: FONT.serif }}>{result.balance_score}/10</p>
            </div>
            <div style={{ height: 10, background: C.border, borderRadius: 10, overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: 10,
                width: `${(result.balance_score / 10) * 100}%`,
                background: `linear-gradient(90deg, ${C.sage}, ${C.primary})`,
                transition: 'width 0.8s ease',
              }} />
            </div>
          </div>

          {[
            { label: 'Mood & energy impact', text: result.mood_impact,       emoji: '🧠' },
            { label: 'A small suggestion',   text: result.recommendation,    emoji: '💡' },
          ].map(({ label, text, emoji }) => (
            <div key={label} style={{
              background: C.surface, borderRadius: 16, boxShadow: C.shadow,
              border: `1px solid ${C.border}`, padding: '16px 20px',
              display: 'flex', gap: 14, alignItems: 'flex-start',
            }}>
              <span style={{ fontSize: 24, flexShrink: 0 }}>{emoji}</span>
              <div>
                <p style={{ fontSize: 12, color: C.textMuted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 5 }}>{label}</p>
                <p style={{ fontSize: 14, color: C.text, lineHeight: 1.65 }}>{text}</p>
              </div>
            </div>
          ))}

          <button onClick={reset} style={{
            alignSelf: 'flex-start', padding: '10px 22px', borderRadius: 12,
            border: `2px solid ${C.border}`, background: 'none',
            color: C.textMuted, cursor: 'pointer', fontFamily: FONT.sans, fontSize: 13,
          }}>← Analyse another meal</button>
        </div>
      )}
    </div>
  );
}
