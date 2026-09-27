import { useState } from 'react';
import { C, FONT } from '../data';

const niceMax = (v) => {
  if (v <= 0) return 1;
  const mag = 10 ** Math.floor(Math.log10(v));
  for (const step of [1, 2, 2.5, 5, 10]) if (v <= step * mag) return step * mag;
  return 10 * mag;
};

/** A ring that fills to a fraction, with text in the middle. Mirrors the
 * desktop app's ui/charts.py RingGauge (an SVG stand-in for its QPainter arc). */
export function RingGauge({ fraction, text, sub, colour, size = 124, thickness = 12 }) {
  const r = (size - thickness) / 2;
  const c = size / 2;
  const circumference = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(1, fraction || 0));
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={c} cy={c} r={r} fill="none" stroke={C.border} strokeWidth={thickness} />
      {clamped > 0 && (
        <circle
          cx={c} cy={c} r={r} fill="none" stroke={colour || C.primary} strokeWidth={thickness}
          strokeLinecap="round" strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - clamped)}
          transform={`rotate(-90 ${c} ${c})`}
        />
      )}
      <text x="50%" y="46%" textAnchor="middle" dominantBaseline="middle" fill={C.text} fontFamily={FONT.sans} fontSize={size * 0.19} fontWeight={800}>{text}</text>
      {sub && <text x="50%" y="64%" textAnchor="middle" dominantBaseline="middle" fill={C.textMuted} fontFamily={FONT.sans} fontSize={size * 0.09}>{sub}</text>}
    </svg>
  );
}

/** A donut with a legend on its right. Segments are {label, value, colour}. */
export function DonutChart({ segments, centre, sub, legend = true }) {
  const total = segments.reduce((s, seg) => s + seg.value, 0);
  const size = 150, thickness = size * 0.2, r = (size - thickness) / 2, c = size / 2;
  const circumference = 2 * Math.PI * r;
  // Cumulative fraction *before* each segment, starting at 12 o'clock, clockwise.
  const cursors = segments.reduce((acc, seg) => {
    const prev = acc.length ? acc[acc.length - 1] : 0;
    acc.push(prev + (total > 0 ? seg.value / total : 0));
    return acc;
  }, []).map((c, i) => c - (total > 0 ? segments[i].value / total : 0));

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ flexShrink: 0 }}>
        {total <= 0 ? (
          <>
            <circle cx={c} cy={c} r={r} fill="none" stroke={C.border} strokeWidth={thickness} />
            <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" fill={C.textMuted} fontFamily={FONT.sans} fontSize={13}>No data</text>
          </>
        ) : (
          <>
            {segments.map((seg, i) => {
              const frac = seg.value / total;
              const gap = segments.length > 1 ? 0.006 : 0;
              const dash = Math.max(frac - gap, frac * 0.02) * circumference;
              const offset = circumference * (1 - cursors[i]) + circumference * 0.25; // start at 12 o'clock
              return (
                <circle key={i} cx={c} cy={c} r={r} fill="none" stroke={seg.colour} strokeWidth={thickness}
                  strokeDasharray={`${dash} ${circumference - dash}`} strokeDashoffset={offset}
                  transform={`rotate(-90 ${c} ${c})`} />
              );
            })}
            <text x="50%" y="46%" textAnchor="middle" dominantBaseline="middle" fill={C.text} fontFamily={FONT.sans} fontSize={20} fontWeight={800}>{centre}</text>
            {sub && <text x="50%" y="60%" textAnchor="middle" dominantBaseline="middle" fill={C.textMuted} fontFamily={FONT.sans} fontSize={11}>{sub}</text>}
          </>
        )}
      </svg>
      {legend && total > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {segments.map((seg, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: seg.colour, flexShrink: 0 }} />
              <span style={{ color: C.text, flex: 1 }}>{seg.label}</span>
              <span style={{ color: C.textMuted }}>{Math.round((seg.value / total) * 100)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** A simple bar chart with optional y-axis gridlines and a highlighted target
 * band (used for the sleep chart's 7-9h zone). `bars`: [{label, value, colour?, tooltip?}]. */
export function BarChart({ bars, yMax, band, emptyText = 'Nothing to show yet', colour, height = 160 }) {
  if (!bars || bars.length === 0) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.textMuted, fontSize: 13, textAlign: 'center' }}>
        {emptyText}
      </div>
    );
  }
  const max = yMax || niceMax(Math.max(...bars.map(b => b.value)) * 1.05);
  const LEFT = 38;
  const width = 600;
  const plotW = width - LEFT, plotH = height - 20;
  const yOf = (v) => plotH - (v / max) * plotH;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height, display: 'block' }} preserveAspectRatio="none">
      {band && (
        <rect x={LEFT} y={yOf(band[1])} width={plotW} height={yOf(band[0]) - yOf(band[1])} fill={C.sageLight} opacity={0.35} />
      )}
      {[0, 0.5, 1].map(frac => (
        <g key={frac}>
          <line x1={LEFT} x2={width} y1={yOf(max * frac)} y2={yOf(max * frac)} stroke={C.border} strokeWidth={1} strokeDasharray={frac ? '2 3' : undefined} />
          <text x={LEFT - 6} y={yOf(max * frac) + 3} textAnchor="end" fontFamily={FONT.sans} fontSize={9} fill={C.textMuted}>
            {Math.round(max * frac * 10) / 10}
          </text>
        </g>
      ))}
      {bars.map((b, i) => {
        const slot = plotW / bars.length;
        const barW = Math.min(30, slot * 0.62);
        const x = LEFT + slot * i + (slot - barW) / 2;
        const top = yOf(Math.min(b.value, max));
        const showLabel = bars.length <= 14 || i % Math.ceil(bars.length / 12) === 0;
        return (
          <g key={i}>
            <title>{b.tooltip || `${b.label}: ${b.value}`}</title>
            <rect x={x} y={top} width={barW} height={Math.max(0, plotH - top)} rx={3} fill={b.colour || colour || C.primary} />
            {showLabel && (
              <text x={x + barW / 2} y={height - 4} textAnchor="middle" fontFamily={FONT.sans} fontSize={9} fill={C.textMuted}>{b.label}</text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

/** Daily mood-trend line: points are [{x label, y: -1..1, tooltip}]. Straight
 * segments between points (a simplified stand-in for the desktop app's
 * Catmull-Rom curve) over a positive/mixed/heavy band background. */
export function LineChart({ points, height = 170 }) {
  if (!points || points.length < 2) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.textMuted, fontSize: 13, textAlign: 'center' }}>
        Check in on a couple of different days to see a trend
      </div>
    );
  }
  const LEFT = 54, width = 600;
  const plotW = width - LEFT - 8, plotH = height - 22;
  const yOf = (v) => plotH / 2 - (v / 1) * (plotH / 2);
  const xOf = (i) => LEFT + (points.length === 1 ? plotW / 2 : (plotW * i) / (points.length - 1));
  const coords = points.map((p, i) => [xOf(i), yOf(p.y)]);
  const linePath = coords.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join(' ');
  const areaPath = `${linePath} L${coords[coords.length - 1][0]},${yOf(0)} L${coords[0][0]},${yOf(0)} Z`;
  const everyNth = Math.ceil(points.length / 6);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height, display: 'block' }} preserveAspectRatio="none">
      {[[1, 'positive'], [0, 'mixed'], [-1, 'heavy']].map(([v, label]) => (
        <g key={label}>
          <line x1={LEFT} x2={width} y1={yOf(v)} y2={yOf(v)} stroke={C.border} strokeWidth={1} strokeDasharray={v ? '2 3' : undefined} />
          <text x={LEFT - 6} y={yOf(v) + 3} textAnchor="end" fontFamily={FONT.sans} fontSize={9} fill={C.textMuted}>{label}</text>
        </g>
      ))}
      <path d={areaPath} fill={C.sageLight} opacity={0.35} stroke="none" />
      <path d={linePath} fill="none" stroke={C.primary} strokeWidth={2} />
      {coords.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={3} fill={C.primary}>
          <title>{points[i].tooltip}</title>
        </circle>
      ))}
      {points.map((p, i) => (i % everyNth === 0 || i === points.length - 1) && (
        <text key={i} x={xOf(i)} y={height - 4} textAnchor="middle" fontFamily={FONT.sans} fontSize={9} fill={C.textMuted}>{p.label}</text>
      ))}
    </svg>
  );
}

/** 12-week mood calendar heatmap: `grid` is columns of 7 days (Monday first),
 * each {date, score, count} or null, as produced by insightsLogic.calendarGrid. */
export function MoodCalendar({ grid }) {
  const [hover, setHover] = useState(null);
  const CELL = 13, GAP = 3, LEFT = 16, TOP = 16;
  const step = CELL + GAP;
  const width = LEFT + grid.length * step;
  const height = TOP + 7 * step;
  const colourFor = (day) => {
    if (!day || day.count === 0) return C.border;
    if (day.score > 0.15) return C.sage;
    if (day.score < -0.15) return '#E07A5F';
    return '#D9B26F';
  };

  let lastMonth = null;
  const monthLabels = [];
  grid.forEach((col, ci) => {
    const first = col.find(Boolean);
    if (first) {
      const m = new Date(first.date + 'T00:00:00').toLocaleDateString('en', { month: 'short' });
      if (m !== lastMonth) { lastMonth = m; monthLabels.push({ ci, m }); }
    }
  });

  return (
    <div style={{ position: 'relative' }}>
      <svg width={width} height={height} style={{ display: 'block', overflow: 'visible' }}>
        {monthLabels.map(({ ci, m }) => (
          <text key={ci} x={LEFT + ci * step} y={10} fontFamily={FONT.sans} fontSize={10} fill={C.textMuted}>{m}</text>
        ))}
        {['M', '', 'W', '', 'F', '', ''].map((label, ri) => label && (
          <text key={ri} x={0} y={TOP + ri * step + CELL - 2} fontFamily={FONT.sans} fontSize={10} fill={C.textMuted}>{label}</text>
        ))}
        {grid.map((col, ci) => col.map((day, ri) => (
          <rect
            key={`${ci}-${ri}`} x={LEFT + ci * step} y={TOP + ri * step} width={CELL} height={CELL} rx={3}
            fill={colourFor(day)}
            onMouseEnter={() => day && setHover({ x: LEFT + ci * step, y: TOP + ri * step, day })}
            onMouseLeave={() => setHover(null)}
          />
        )))}
      </svg>
      {hover && (
        <div style={{
          position: 'absolute', left: hover.x, top: hover.y - 30, background: C.text, color: C.surface,
          fontSize: 11, padding: '3px 8px', borderRadius: 6, whiteSpace: 'nowrap', pointerEvents: 'none', zIndex: 1,
        }}>
          {new Date(hover.day.date + 'T00:00:00').toLocaleDateString('en', { weekday: 'short', day: 'numeric', month: 'short' })}
          {hover.day.count ? ` · ${hover.day.count} check-in${hover.day.count !== 1 ? 's' : ''}` : ' · no check-in'}
        </div>
      )}
    </div>
  );
}
