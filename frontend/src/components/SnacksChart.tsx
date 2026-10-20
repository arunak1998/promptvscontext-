import { useMemo, useState } from "react";
import type { DatasetResponse } from "../api/types";

const W = 820;
const H = 280;
const PAD = { top: 34, right: 16, bottom: 30, left: 44 };
const DAY = 86_400_000;

const toTime = (iso: string) => new Date(`${iso}T00:00:00`).getTime();
const fmt = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

/** Snacks units per day, with promo periods and the before/after windows marked. One series, so no legend box. */
export function SnacksChart({ data }: { data: DatasetResponse }) {
  const [hover, setHover] = useState<number | null>(null);
  const { series, promos, pivot_date, window_days } = data;

  const scale = useMemo(() => {
    const t0 = toTime(series[0].date);
    const t1 = toTime(series[series.length - 1].date);
    const yMax = Math.ceil((Math.max(...series.map((p) => p.units)) * 1.1) / 100) * 100;
    const x = (t: number) => PAD.left + ((t - t0) / (t1 - t0)) * (W - PAD.left - PAD.right);
    const y = (u: number) => H - PAD.bottom - (u / yMax) * (H - PAD.top - PAD.bottom);
    return { t0, t1, yMax, x, y };
  }, [series]);

  const path = series.map((p, i) => `${i ? "L" : "M"}${scale.x(toTime(p.date)).toFixed(1)},${scale.y(p.units).toFixed(1)}`).join("");
  const pivot = toTime(pivot_date);
  const before = { from: scale.x(pivot - (window_days - 1) * DAY), to: scale.x(pivot) };
  const after = { from: scale.x(pivot + DAY), to: scale.x(Math.min(pivot + window_days * DAY, scale.t1)) };
  const yTicks = [0, 1, 2, 3].map((i) => (scale.yMax / 3) * i);
  const months = Array.from({ length: 10 }, (_, m) => new Date(2026, m, 1).getTime()).filter((t) => t >= scale.t0 && t <= scale.t1);

  function onMove(e: React.PointerEvent<SVGRectElement>) {
    const box = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - box.left) / box.width;
    setHover(Math.max(0, Math.min(series.length - 1, Math.round(ratio * (series.length - 1)))));
  }

  const hp = hover !== null ? series[hover] : null;
  const hx = hp ? scale.x(toTime(hp.date)) : 0;

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label={`${data.category} units per day, ${series[0].date} to ${series[series.length - 1].date}`}>
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={W - PAD.right} y1={scale.y(v)} y2={scale.y(v)} className="grid" />
            <text x={PAD.left - 8} y={scale.y(v) + 4} className="axis" textAnchor="end">
              {Math.round(v)}
            </text>
          </g>
        ))}
        {months.map((t) => (
          <text key={t} x={scale.x(t)} y={H - 8} className="axis">
            {new Date(t).toLocaleDateString("en-GB", { month: "short" })}
          </text>
        ))}

        {promos.map((p) => {
          const x1 = scale.x(toTime(p.start_date));
          const x2 = scale.x(Math.min(toTime(p.end_date), scale.t1));
          return (
            <g key={p.promo_name}>
              <rect x={x1} y={PAD.top} width={x2 - x1} height={H - PAD.top - PAD.bottom} className="band promo" />
              <text x={x1 + 6} y={PAD.top - 18} className="band-label">{p.promo_name}</text>
              <text x={x1 + 6} y={PAD.top - 6} className="band-sub">{p.discount_pct}% off</text>
            </g>
          );
        })}

        <rect x={before.from} y={PAD.top} width={before.to - before.from} height={H - PAD.top - PAD.bottom} className="band before" />
        <rect x={after.from} y={PAD.top} width={after.to - after.from} height={H - PAD.top - PAD.bottom} className="band after" />
        <line x1={scale.x(pivot)} x2={scale.x(pivot)} y1={PAD.top} y2={H - PAD.bottom} className="pivot" />

        <path d={path} className="line" />

        {hp && (
          <g pointerEvents="none">
            <line x1={hx} x2={hx} y1={PAD.top} y2={H - PAD.bottom} className="crosshair" />
            <circle cx={hx} cy={scale.y(hp.units)} r={5} className="hover-dot" />
          </g>
        )}
        <rect
          x={PAD.left}
          y={PAD.top}
          width={W - PAD.left - PAD.right}
          height={H - PAD.top - PAD.bottom}
          fill="transparent"
          onPointerMove={onMove}
          onPointerLeave={() => setHover(null)}
        />
      </svg>
      {hp && (
        <div className="tooltip" style={{ left: `${(hx / W) * 100}%` }}>
          <span>{fmt(hp.date)}</span>
          <b>{hp.units} units</b>
        </div>
      )}
      <div className="chart-key">
        <span><i className="key promo" /> promo running</span>
        <span><i className="key before" /> {window_days} days before {fmt(pivot_date)}</span>
        <span><i className="key after" /> after (data ends {fmt(series[series.length - 1].date)})</span>
      </div>
    </div>
  );
}
