import { useState, useRef, useEffect } from 'react';
import { C, FONT } from '../data';
import { visionAI, checkConnection, pullModel } from '../ai';
import { parseAnalysis, balanceTone, balanceLabel, mealsOn, summariseMeals } from '../nutritionLogic';
import { RingGauge, DonutChart } from './charts';

const NUTRITION_PROMPT = `Look at this meal photo and respond with ONLY a raw JSON object — no markdown, no code fences, no explanation. Use exactly this structure:
{"foods":["item1"],"calories_estimate":450,"nutrients":{"protein":22,"carbs":55,"fat":14,"fibre":6},"mood_impact":"one sentence about energy/mood","recommendation":"one practical suggestion","balance_score":7}
Estimate realistically. balance_score is 1-10.`;

const MAX_DIMENSION = 768;
const DAY_CALORIES = 2000;
const TONE_COLOURS = { high: C.sage, mid: '#D4A017', low: '#E07A5F' };
const MACRO_COLOURS = { protein: '#E07A5F', carbs: '#D4A017', fat: '#748CAB', fibre: '#52B788' };
const MACRO_NAMES = { protein: 'Protein', carbs: 'Carbs', fat: 'Fat', fibre: 'Fibre' };

function load(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } }
function save(k, v) { localStorage.setItem(k, JSON.stringify(v)); }

function Card({ children, style, center }) {
  return (
    <div style={{
      background: C.surface, borderRadius: 16, border: `1px solid ${C.border}`,
      padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 10,
      ...(center ? { alignItems: 'center', textAlign: 'center' } : {}), ...style,
    }}>
      {children}
    </div>
  );
}

function Heading({ children }) { return <div style={{ fontSize: 15, fontWeight: 700, color: C.text }}>{children}</div>; }
function Muted({ children, size = 12 }) { return <p style={{ color: C.textMuted, fontSize: size, lineHeight: 1.5 }}>{children}</p>; }

function StatCard({ label, value }) {
  return (
    <Card style={{ flex: 1, padding: '14px 18px', gap: 2 }}>
      <span style={{ color: C.textMuted, fontSize: 12, fontWeight: 600 }}>{label}</span>
      <span style={{ color: C.text, fontSize: 26, fontWeight: 800 }}>{value}</span>
    </Card>
  );
}

function ScoreBadge({ score }) {
  const tone = balanceTone(score);
  const colour = TONE_COLOURS[tone];
  return (
    <div style={{
      width: 44, height: 44, borderRadius: 22, flexShrink: 0,
      background: `${colour}2E`, color: colour, border: `2px solid ${colour}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontWeight: 800, fontSize: 15,
    }}>
      {score != null ? score : '?'}
    </div>
  );
}

export default function NutritionTab({ aiConfig, connected, onOpenSettings }) {
  const [image,     setImage]     = useState(null); // { url, base64, mimeType }
  const [analysing, setAnalysing] = useState(false);
  const [result,    setResult]    = useState(null);
  const [error,     setError]     = useState('');
  const [modelReady, setModelReady] = useState(null);
  const [pulling,    setPulling]    = useState(false);
  const [pullPct,    setPullPct]    = useState(null);
  const [meals,      setMeals]      = useState(() => load('mf_nutrition_history', []));
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
        const scale = Math.min(1, MAX_DIMENSION / Math.max(img.width, img.height));
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
      const timeout = setTimeout(() => controller.abort(), 180000);
      let raw;
      try {
        raw = await visionAI(aiConfig, image.base64, image.mimeType, NUTRITION_PROMPT, controller.signal);
      } finally {
        clearTimeout(timeout);
      }
      const analysis = parseAnalysis(raw);
      setResult(analysis);
      const entry = {
        id: Date.now(),
        foods: analysis.foods.join(', '),
        caloriesEstimate: analysis.caloriesEstimate,
        balanceScore: analysis.balanceScore,
        moodImpact: analysis.moodImpact,
        recommendation: analysis.recommendation,
        ...analysis.nutrients,
        timestamp: Date.now(),
      };
      setMeals(prev => { const updated = [entry, ...prev]; save('mf_nutrition_history', updated); return updated; });
    } catch (e) {
      if (e.name === 'AbortError') {
        setError('Analysis timed out (3 min). Try a smaller or clearer photo.');
      } else if (e.message?.includes('fetch') || e.message?.includes('Failed') || e.message?.includes('NetworkError') || e.message?.includes('Connection')) {
        setError("Couldn't reach the vision model — is Ollama running? Check settings.");
      } else {
        setError(`Analysis failed: ${e.message}`);
      }
    } finally {
      setAnalysing(false);
    }
  };

  const deleteMeal = (id) => {
    setMeals(prev => { const updated = prev.filter(m => m.id !== id); save('mf_nutrition_history', updated); return updated; });
  };

  const today = summariseMeals(mealsOn(meals, new Date()));
  const ghostBtn = { padding: '11px 20px', borderRadius: 12, border: `2px solid ${C.border}`, background: 'none', color: C.textMuted, cursor: 'pointer', fontFamily: FONT.sans, fontSize: 14 };
  const primaryBtn = { padding: '11px 20px', borderRadius: 12, border: 'none', background: C.primary, color: '#FFF', cursor: 'pointer', fontFamily: FONT.sans, fontSize: 14, fontWeight: 600 };

  return (
    <div className="animate-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h1 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 24, fontWeight: 800, marginBottom: 6 }}>Meal analysis</h1>
        <Muted size={13}>Snap or drop a photo of your meal for an instant nutrition estimate and a note on how it might affect your energy. Analysed on your computer.</Muted>
      </div>

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

      {/* Today */}
      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
        <StatCard label="Calories today" value={today.calories != null ? today.calories.toLocaleString() : '—'} />
        <StatCard label="Meals logged today" value={today.count} />
        <StatCard label="Avg balance today" value={today.avgBalance != null ? `${today.avgBalance}/10` : '—'} />
      </div>

      {/* Upload + results */}
      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <Card style={{ flex: '1 1 280px', minWidth: 260 }}>
          <Heading>Your meal</Heading>
          <div
            onDrop={handleDrop}
            onDragOver={e => e.preventDefault()}
            onClick={() => fileRef.current?.click()}
            style={{
              border: `2px dashed ${C.border}`, borderRadius: 16, minHeight: 220,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              textAlign: 'center', cursor: 'pointer', overflow: 'hidden', padding: image ? 0 : 24,
            }}
          >
            {image ? (
              <img src={image.url} alt="Meal" style={{ width: '100%', height: '100%', maxHeight: 260, objectFit: 'cover' }} />
            ) : (
              <div>
                <div style={{ fontSize: 38, marginBottom: 8 }}>🍽️</div>
                <p style={{ fontSize: 15, fontWeight: 700, color: C.text }}>Drop a meal photo here</p>
                <p style={{ color: C.textMuted, fontSize: 13 }}>or click to choose one</p>
              </div>
            )}
            <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => handleFile(e.target.files[0])} />
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button onClick={() => fileRef.current?.click()} style={ghostBtn}>Choose photo…</button>
            <button onClick={analyse} disabled={!image || analysing} style={{ ...primaryBtn, flex: 1, opacity: !image || analysing ? 0.5 : 1 }}>
              {analysing ? 'Analysing…' : 'Analyse meal  →'}
            </button>
          </div>
          {error && <p style={{ color: '#E07A5F', fontSize: 12 }}>{error}</p>}
          <Muted size={11}>PNG, JPEG, HEIC, WebP and more. The photo is resized on your computer and never leaves it.</Muted>
        </Card>

        <div style={{ flex: '1 1 420px', minWidth: 300, display: 'flex', flexDirection: 'column', gap: 14 }}>
          {analysing ? (
            <Card center style={{ minHeight: 220, justifyContent: 'center' }}>
              <div style={{ fontSize: 40 }}>🔍</div>
              <p style={{ fontSize: 16, fontWeight: 700 }}>Analysing your meal…</p>
              <div style={{ width: '80%', height: 8, borderRadius: 4, background: C.border, overflow: 'hidden' }}>
                <div style={{ width: '40%', height: '100%', background: C.primary, animation: 'mf-indeterminate 1.2s ease-in-out infinite' }} />
              </div>
              <Muted>A local model does this on your own computer, so it can take up to a minute.</Muted>
            </Card>
          ) : !result ? (
            <Card center style={{ minHeight: 220, justifyContent: 'center' }}>
              <div style={{ fontSize: 44 }}>🥗</div>
              <p style={{ fontSize: 16, fontWeight: 700 }}>Your analysis will appear here</p>
              <Muted>You'll see estimated calories, how balanced the meal is, its macros, and a suggestion — and it's saved to your meal log.</Muted>
            </Card>
          ) : (
            <div className="animate-in" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
                <Card style={{ flex: 1, minWidth: 160 }}>
                  <Heading>Estimated calories</Heading>
                  {result.caloriesEstimate == null ? (
                    <Muted>The model didn't give a calorie estimate for this photo.</Muted>
                  ) : (
                    <>
                      <div><span style={{ fontSize: 34, fontWeight: 800, color: C.text }}>{result.caloriesEstimate}</span> <span style={{ fontSize: 14, fontWeight: 600, color: C.textMuted }}>kcal</span></div>
                      <div style={{ height: 8, borderRadius: 4, background: C.border, overflow: 'hidden' }}>
                        <div style={{ width: `${Math.min(100, Math.round(result.caloriesEstimate / DAY_CALORIES * 100))}%`, height: '100%', background: C.primary }} />
                      </div>
                      <Muted>about {Math.round(result.caloriesEstimate / DAY_CALORIES * 100)}% of a {DAY_CALORIES.toLocaleString()} kcal day</Muted>
                    </>
                  )}
                </Card>
                <Card center style={{ flex: 1, minWidth: 160, justifyContent: 'center' }}>
                  <Heading>Meal balance</Heading>
                  <RingGauge fraction={(result.balanceScore || 0) / 10} text={result.balanceScore != null ? `${result.balanceScore}/10` : '—'} sub={balanceLabel(result.balanceScore)} colour={TONE_COLOURS[balanceTone(result.balanceScore)]} />
                </Card>
              </div>

              {Object.keys(result.nutrients).length > 0 && (
                <Card>
                  <Heading>Macros (by weight)</Heading>
                  <DonutChart
                    segments={Object.entries(result.nutrients).map(([k, v]) => ({ label: MACRO_NAMES[k], value: v, colour: MACRO_COLOURS[k] }))}
                    centre={`${Object.values(result.nutrients).reduce((a, b) => a + b, 0)}g`} sub="total"
                  />
                </Card>
              )}

              {result.foods.length > 0 && (
                <Card>
                  <Heading>What I can see</Heading>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {result.foods.map((f, i) => (
                      <span key={i} style={{ padding: '4px 12px', borderRadius: 12, background: C.primaryPale, color: C.primary, fontSize: 12, fontWeight: 600 }}>{f}</span>
                    ))}
                  </div>
                </Card>
              )}

              {(result.moodImpact || result.recommendation) && (
                <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
                  {result.moodImpact && (
                    <Card style={{ flex: 1, minWidth: 200 }}>
                      <Heading>⚡ Energy &amp; mood</Heading>
                      <p style={{ fontSize: 13, color: C.text }}>{result.moodImpact}</p>
                    </Card>
                  )}
                  {result.recommendation && (
                    <Card style={{ flex: 1, minWidth: 200 }}>
                      <Heading>💡 Try this next</Heading>
                      <p style={{ fontSize: 13, color: C.text }}>{result.recommendation}</p>
                    </Card>
                  )}
                </div>
              )}
              <p style={{ color: C.sage, fontSize: 12, fontWeight: 600 }}>✓ Saved to your meal log</p>
            </div>
          )}
        </div>
      </div>

      {/* Recent meals */}
      <Heading>Recent meals</Heading>
      {meals.length === 0 ? (
        <Muted size={13}>No meals yet — analyse your first one above and it will show up here.</Muted>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {meals.slice(0, 8).map(meal => {
            const when = new Date(meal.timestamp).toLocaleString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
            const macros = [['P', meal.protein], ['C', meal.carbs], ['F', meal.fat]].filter(([, v]) => v != null).map(([l, v]) => `${l} ${v}g`).join(' · ');
            const bits = [when, meal.caloriesEstimate != null ? `${meal.caloriesEstimate} kcal` : null, macros || null].filter(Boolean).join(' · ');
            return (
              <Card key={meal.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 14, padding: '14px 18px' }}>
                <ScoreBadge score={meal.balanceScore} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 14, fontWeight: 700, color: C.text }}>{meal.foods || 'Meal'}</p>
                  <p style={{ color: C.textMuted, fontSize: 12 }}>{bits}</p>
                  {meal.moodImpact && <p style={{ color: C.textMuted, fontSize: 12, fontStyle: 'italic' }}>{meal.moodImpact}</p>}
                </div>
                <button onClick={() => deleteMeal(meal.id)} title="Remove this meal from your log" style={{
                  width: 28, height: 28, borderRadius: 8, border: `1px solid ${C.border}`, background: 'none',
                  color: C.textMuted, cursor: 'pointer', flexShrink: 0, alignSelf: 'flex-start',
                }}>×</button>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
