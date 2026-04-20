import { useEffect, useRef, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface DataPoint {
  time: string;
  ts: number;
  p50: number;
  p95: number;
}

const MAX_POINTS = 300; // 10 min at 2s intervals

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms.toFixed(0)}ms`;
}

interface LatencyChartProps {
  p50: number;
  p95: number;
}

export default function LatencyChart({ p50, p95 }: LatencyChartProps) {
  const buffer = useRef<DataPoint[]>([]);
  const [data, setData] = useState<DataPoint[]>([]);

  useEffect(() => {
    const now = Date.now();
    const last = buffer.current[buffer.current.length - 1];
    if (last && now - last.ts < 1500) return;

    const point: DataPoint = {
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      ts: now,
      p50,
      p95,
    };
    const next = [...buffer.current, point].slice(-MAX_POINTS);
    buffer.current = next;
    setData(next);
  }, [p50, p95]);

  const latest = data[data.length - 1];
  const avg = data.length > 10 ? data.reduce((s, d) => s + d.p50, 0) / data.length : null;

  return (
    <div className="latency-chart">
      <div className="lc-header">
        <span className="lc-title">Write Latency</span>
        <span className="lc-current">
          <span className="lc-value">{formatMs(latest?.p50 ?? 0)}</span>
          <span className="lc-label">p50</span>
          <span className="lc-sep">/</span>
          <span className="lc-value">{formatMs(latest?.p95 ?? 0)}</span>
          <span className="lc-label">p95</span>
        </span>
      </div>
      <ResponsiveContainer width="100%" height={80}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
          <XAxis
            dataKey="time"
            tick={{ fontSize: 9, fill: "var(--text-muted)" }}
            interval="preserveStartEnd"
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 9, fill: "var(--text-muted)" }}
            tickFormatter={formatMs}
            tickLine={false}
            axisLine={false}
            domain={[0, "auto"]}
          />
          <Tooltip
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              fontSize: 11,
            }}
            formatter={(value: number, name: string) => [formatMs(value), name]}
          />
          {avg !== null && (
            <ReferenceLine
              y={avg}
              stroke="var(--text-muted)"
              strokeDasharray="3 3"
              strokeWidth={1}
            />
          )}
          <Line
            type="monotone"
            dataKey="p50"
            stroke="#4fc3f7"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="p95"
            stroke="#ffb74d"
            strokeWidth={1}
            dot={false}
            strokeDasharray="4 2"
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
