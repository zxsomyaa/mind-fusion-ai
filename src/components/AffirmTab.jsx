import { useState } from 'react';
import { C, FONT, AFFIRMATIONS } from '../data';

function load(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } }

export default function AffirmTab() {
  const [idx,      setIdx]      = useState(0);
  const [favorites,setFavorites]= useState(() => load('mf_affirm_favs', []));
  const [liked,    setLiked]    = useState(false);

  const current = AFFIRMATIONS[idx];

  const next = () => {
    setLiked(false);
    setIdx(i => (i + 1) % AFFIRMATIONS.length);
  };

  const prev = () => {
    setLiked(false);
    setIdx(i => (i - 1 + AFFIRMATIONS.length) % AFFIRMATIONS.length);
  };

  const toggleFav = () => {
    setFavorites(prev => {
      const exists = prev.find(f => f.id === current.id);
      const updated = exists ? prev.filter(f => f.id !== current.id) : [...prev, current];
      localStorage.setItem('mf_affirm_favs', JSON.stringify(updated));
      return updated;
    });
    setLiked(l => !l);
  };

  const isFav = favorites.some(f => f.id === current.id);

  const removeFav = (id) => {
    setFavorites(prev => {
      const updated = prev.filter(f => f.id !== id);
      localStorage.setItem('mf_affirm_favs', JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h2 style={{ fontFamily: FONT.serif, color: C.primary, fontSize: 24, marginBottom: 6 }}>Affirmations</h2>
        <p style={{ color: C.textMuted, fontSize: 14 }}>Words worth sitting with. Take what feels true today.</p>
      </div>

      {/* Main affirmation card */}
      <div className="animate-in" style={{
        background: `linear-gradient(145deg, ${C.primaryPale} 0%, ${C.sagePale} 100%)`,
        borderRadius: 24, padding: '40px 32px', textAlign: 'center',
        boxShadow: C.shadowLg, border: `1px solid ${C.border}`,
        minHeight: 200, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 24,
      }}>
        <p style={{
          fontFamily: FONT.serif, fontSize: 22, lineHeight: 1.65,
          color: C.text, maxWidth: 400,
        }}>
          "{current.text}"
        </p>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button onClick={prev} style={{
            width: 40, height: 40, borderRadius: '50%', border: `2px solid ${C.border}`,
            background: C.surface, color: C.textMuted, cursor: 'pointer', fontSize: 16,
          }}>‹</button>
          <button onClick={toggleFav} style={{
            width: 44, height: 44, borderRadius: '50%', border: 'none',
            background: isFav ? '#FCEEE9' : C.surface,
            color: isFav ? '#E07A5F' : C.textMuted, cursor: 'pointer', fontSize: 22,
            boxShadow: C.shadow, transition: 'all 0.2s',
            animation: liked ? 'pulse 0.4s ease' : 'none',
          }}>
            {isFav ? '♥' : '♡'}
          </button>
          <button onClick={next} style={{
            width: 40, height: 40, borderRadius: '50%', border: `2px solid ${C.border}`,
            background: C.surface, color: C.textMuted, cursor: 'pointer', fontSize: 16,
          }}>›</button>
        </div>

        <p style={{ fontSize: 12, color: C.textMuted }}>
          {idx + 1} of {AFFIRMATIONS.length}
        </p>
      </div>

      {/* Favorites */}
      {favorites.length > 0 && (
        <div>
          <h3 style={{ fontFamily: FONT.serif, color: C.text, fontSize: 18, marginBottom: 14 }}>
            Saved ♥
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {favorites.map(fav => (
              <div key={fav.id} className="animate-in" style={{
                background: C.surface, borderRadius: 16, boxShadow: C.shadow,
                border: `1px solid ${C.border}`, padding: '16px 20px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
              }}>
                <p style={{ fontFamily: FONT.serif, fontSize: 15, color: C.text, lineHeight: 1.55, flex: 1 }}>
                  "{fav.text}"
                </p>
                <button onClick={() => removeFav(fav.id)} style={{
                  background: 'none', border: 'none', color: '#E07A5F',
                  cursor: 'pointer', fontSize: 16, flexShrink: 0,
                }}>♥</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
