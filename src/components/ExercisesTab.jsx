import { useState, useEffect, useRef, useCallback } from 'react';
import { C, FONT, EXERCISES } from '../data';

export default function ExercisesTab() {
  const [active, setActive] = useState(null);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 24, marginBottom: 6 }}>Guided exercises</h2>
        <p style={{ color: C.textMuted, fontSize: 14 }}>Breathing and grounding practices for real moments.</p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
        {EXERCISES.map(ex => (
          <ExCard key={ex.id} exercise={ex} onStart={() => setActive(ex)} />
        ))}
      </div>
      {active && <ExModal exercise={active} onClose={() => setActive(null)} />}
    </div>
  );
}

function ExCard({ exercise, onStart }) {
  return (
    <div className="animate-in" style={{
      background: C.surface, borderRadius: 20, boxShadow: C.shadow,
      border: `1px solid ${C.border}`, padding: '22px 22px', cursor: 'default',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 12 }}>
        <span style={{ fontSize: 30, lineHeight: 1 }}>{exercise.emoji}</span>
        <div>
          <h3 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 16, marginBottom: 2 }}>{exercise.name}</h3>
          <p style={{ fontSize: 12, color: C.sage, fontWeight: 500 }}>{exercise.tagline}</p>
        </div>
      </div>
      <p style={{ fontSize: 13, color: C.textMuted, lineHeight: 1.6, marginBottom: 14 }}>{exercise.description}</p>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{
          fontSize: 12, padding: '4px 10px', borderRadius: 100,
          background: C.primaryPale, color: C.primary,
        }}>⏱ {exercise.durationLabel}</span>
        <button onClick={onStart} style={{
          padding: '9px 20px', borderRadius: 12, border: 'none',
          background: C.primary, color: '#FFF', cursor: 'pointer',
          fontFamily: FONT.sans, fontSize: 13, fontWeight: 600,
        }}>
          Begin
        </button>
      </div>
    </div>
  );
}

function ExModal({ exercise, onClose }) {
  const [phase,    setPhase]    = useState('ready'); // ready | running | complete
  const [cycleNum, setCycleNum] = useState(1);
  const [stepIdx,  setStepIdx]  = useState(0);
  const [timeLeft, setTimeLeft] = useState(exercise.steps[0]?.duration || 4);
  const [paused,   setPaused]   = useState(false);

  const timerRef   = useRef(null);
  const pausedRef  = useRef(false);
  pausedRef.current = paused;

  const totalCycles = exercise.cycles;
  const steps = exercise.steps;
  const step  = steps[stepIdx];

  const clearTimer = () => { clearInterval(timerRef.current); timerRef.current = null; };

  const start = useCallback(() => {
    setPhase('running');
    setStepIdx(0);
    setCycleNum(1);
    setTimeLeft(steps[0].duration);
  }, [steps]);

  useEffect(() => {
    if (phase !== 'running') return;
    clearTimer();

    timerRef.current = setInterval(() => {
      if (pausedRef.current) return;
      setTimeLeft(prev => {
        if (prev <= 1) {
          // advance
          const nextStep = stepIdx + 1;
          if (nextStep < steps.length) {
            setStepIdx(nextStep);
            return steps[nextStep].duration;
          } else {
            // next cycle or done
            const nextCycle = cycleNum + 1;
            if (nextCycle <= totalCycles) {
              setCycleNum(nextCycle);
              setStepIdx(0);
              return steps[0].duration;
            } else {
              clearTimer();
              setPhase('complete');
              return 0;
            }
          }
        }
        return prev - 1;
      });
    }, 1000);

    return clearTimer;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, stepIdx, cycleNum, paused]);

  const R = 54;
  const circ = 2 * Math.PI * R;
  const stepDur = step?.duration || 1;
  const dashOffset = circ * (1 - timeLeft / stepDur);

  const bg = {
    ready:    C.primaryPale,
    running:  '#EAF7F0',
    complete: '#EBF7F2',
  }[phase];

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(61,44,30,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 200, padding: 20,
    }}>
      <div className="animate-in" style={{
        background: bg, borderRadius: 28, padding: '36px 32px',
        width: '100%', maxWidth: 400, boxShadow: C.shadowLg, textAlign: 'center',
        position: 'relative',
      }}>
        <button onClick={onClose} style={{
          position: 'absolute', right: 18, top: 14,
          background: 'none', border: 'none', color: C.textMuted, cursor: 'pointer', fontSize: 22, lineHeight: 1,
        }}>×</button>

        {/* Header */}
        <div style={{ marginBottom: 8 }}>
          <span style={{ fontSize: 34 }}>{exercise.emoji}</span>
          <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 20, marginTop: 6 }}>{exercise.name}</h2>
        </div>

        {phase === 'ready' && (
          <>
            <p style={{ color: C.textMuted, fontSize: 14, lineHeight: 1.6, marginBottom: 28 }}>
              {exercise.description}
            </p>
            <p style={{ fontSize: 13, color: C.text, marginBottom: 28 }}>
              {totalCycles} cycle{totalCycles > 1 ? 's' : ''} · {exercise.durationLabel}
            </p>
            <button onClick={start} style={{
              padding: '14px 40px', borderRadius: 14, border: 'none',
              background: C.primary, color: '#FFF', cursor: 'pointer',
              fontFamily: FONT.sans, fontSize: 16, fontWeight: 600,
            }}>
              Begin
            </button>
          </>
        )}

        {phase === 'running' && (
          <>
            <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20 }}>
              <svg width="130" height="130" style={{ transform: 'rotate(-90deg)' }}>
                <circle cx="65" cy="65" r={R} fill="none" stroke={C.border} strokeWidth="8" />
                <circle
                  cx="65" cy="65" r={R} fill="none"
                  stroke={C.primary} strokeWidth="8"
                  strokeDasharray={circ}
                  strokeDashoffset={dashOffset}
                  strokeLinecap="round"
                  style={{ transition: 'stroke-dashoffset 0.9s linear' }}
                />
              </svg>
              <div style={{ position: 'absolute', textAlign: 'center' }}>
                <p style={{ fontFamily: FONT.serif, fontSize: 30, fontWeight: 700, color: C.primary, lineHeight: 1 }}>{timeLeft}</p>
                <p style={{ fontSize: 10, color: C.textMuted }}>seconds</p>
              </div>
            </div>

            <p style={{ fontFamily: FONT.serif, fontSize: 19, color: C.text, marginBottom: 6 }}>{step?.label}</p>
            <p style={{ fontSize: 13, color: C.textMuted, lineHeight: 1.6, marginBottom: 20 }}>{step?.hint}</p>

            {totalCycles > 1 && (
              <p style={{ fontSize: 12, color: C.textMuted, marginBottom: 16 }}>
                Cycle {cycleNum} of {totalCycles}
              </p>
            )}

            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button onClick={() => setPaused(p => !p)} style={{
                padding: '10px 24px', borderRadius: 12,
                border: `2px solid ${C.primary}`, background: 'none',
                color: C.primary, cursor: 'pointer', fontFamily: FONT.sans, fontSize: 14,
              }}>
                {paused ? '▶ Resume' : '⏸ Pause'}
              </button>
              <button onClick={onClose} style={{
                padding: '10px 24px', borderRadius: 12,
                border: `2px solid ${C.border}`, background: 'none',
                color: C.textMuted, cursor: 'pointer', fontFamily: FONT.sans, fontSize: 14,
              }}>
                Stop
              </button>
            </div>
          </>
        )}

        {phase === 'complete' && (
          <>
            <div style={{ fontSize: 52, marginBottom: 16, animation: 'pulse 1s ease' }}>🌿</div>
            <h3 style={{ fontFamily: FONT.serif, color: C.sage, fontSize: 22, marginBottom: 10 }}>Well done</h3>
            <p style={{ color: C.textMuted, fontSize: 15, lineHeight: 1.65, marginBottom: 28 }}>
              You just gave your nervous system a real gift. Take a moment to notice how you feel.
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button onClick={start} style={{
                padding: '12px 24px', borderRadius: 12, border: 'none',
                background: C.sagePale, color: C.sage, cursor: 'pointer',
                fontFamily: FONT.sans, fontSize: 14, fontWeight: 600,
              }}>
                Do it again
              </button>
              <button onClick={onClose} style={{
                padding: '12px 28px', borderRadius: 12, border: 'none',
                background: C.primary, color: '#FFF', cursor: 'pointer',
                fontFamily: FONT.sans, fontSize: 14, fontWeight: 600,
              }}>
                Done ✓
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
