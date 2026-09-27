import { useState } from 'react';
import { C, FONT } from '../data';

const COMMON_ACTIVITIES = [
  'Walking', 'Running', 'Cycling', 'Swimming', 'Yoga', 'Gym workout', 'Dancing', 'Stretching',
  'Hiking', 'Sports', 'Pilates', 'Strength training',
];

export default function AddExerciseModal({ onSave, onClose }) {
  const [name, setName] = useState('');
  const [when, setWhen] = useState(() => new Date().toISOString().slice(0, 16));
  const [minutes, setMinutes] = useState(30);
  const [error, setError] = useState('');

  const save = () => {
    const trimmed = name.trim();
    if (!trimmed) { setError('Enter what you did, e.g. Walking.'); return; }
    onSave({ name: trimmed.slice(0, 60), when: new Date(when).getTime(), minutes });
  };

  const inputStyle = { width: '100%', padding: '9px 12px', borderRadius: 10, border: `1.5px solid ${C.border}`, fontSize: 13, fontFamily: FONT.sans, color: C.text, background: C.surface };
  const labelStyle = { fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 5, display: 'block' };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(61,44,30,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200, padding: 20 }}>
      <div className="animate-in" style={{ background: C.bg, borderRadius: 20, padding: 24, width: '100%', maxWidth: 400, boxShadow: C.shadowLg }}>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 18, marginBottom: 6 }}>Log an exercise</h2>
        <p style={{ color: C.textMuted, fontSize: 12, marginBottom: 18 }}>Add something you did outside the app — a walk, a workout, a class. It counts towards your insights.</p>

        <div style={{ marginBottom: 12 }}>
          <label style={labelStyle}>What did you do?</label>
          <input list="mf-activities" value={name} onChange={e => setName(e.target.value)} placeholder="Choose or type, e.g. Evening walk" style={inputStyle} />
          <datalist id="mf-activities">
            {[...COMMON_ACTIVITIES].map(a => <option key={a} value={a} />)}
          </datalist>
        </div>
        <div style={{ marginBottom: 12 }}>
          <label style={labelStyle}>When?</label>
          <input type="datetime-local" value={when} max={new Date().toISOString().slice(0, 16)} onChange={e => setWhen(e.target.value)} style={inputStyle} />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label style={labelStyle}>How long? (minutes)</label>
          <input type="number" min={1} max={600} value={minutes} onChange={e => setMinutes(Number(e.target.value))} style={inputStyle} />
        </div>
        {error && <p style={{ color: '#E07A5F', fontSize: 12, marginBottom: 10 }}>{error}</p>}

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
          <button onClick={onClose} style={{ padding: '9px 18px', borderRadius: 12, border: `1.5px solid ${C.border}`, background: 'none', color: C.textMuted, cursor: 'pointer', fontFamily: FONT.sans, fontSize: 13 }}>Cancel</button>
          <button onClick={save} style={{ padding: '9px 18px', borderRadius: 12, border: 'none', background: C.primary, color: '#FFF', cursor: 'pointer', fontFamily: FONT.sans, fontSize: 13, fontWeight: 600 }}>Save exercise</button>
        </div>
      </div>
    </div>
  );
}
