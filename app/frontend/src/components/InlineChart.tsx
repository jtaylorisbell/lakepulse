import { useQuery } from "@tanstack/react-query";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { fetchMetricHistory } from "../api";
import { getDescription } from "../metricDescriptions";

interface Props {
  category: string;
  metric: string;
  unit: string;
  label: string;
  latestValue: number;
  color?: string;
  domain?: [number, number];
}

function formatValue(value: number, unit: string): string {
  if (unit === "bytes") {
    if (value >= 1e9) return `${(value / 1e9).toFixed(1)} GB`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(1)} MB`;
    return `${(value / 1e3).toFixed(1)} KB`;
  }
  if (unit === "percent") return `${value.toFixed(1)}%`;
  if (unit === "mhz") return `${value.toFixed(0)} MHz`;
  if (unit === "load") return value.toFixed(2);
  return value.toFixed(1);
}

export default function InlineChart({
  category,
  metric,
  unit,
  label,
  latestValue,
  color = "#4fc3f7",
  domain,
}: Props) {
  const { data } = useQuery({
    queryKey: ["history", category, metric],
    queryFn: () => fetchMetricHistory(category, metric, 10),
    refetchInterval: 5000,
  });

  const chartData = (data ?? []).map((d) => ({
    time: new Date(d.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    value: d.value,
  }));

  const description = getDescription(metric);

  return (
    <div className="inline-chart">
      <div className="inline-chart-header">
        <div>
          <span className="inline-chart-label">{label}</span>
          {description && <span className="tooltip-icon" title={description}>?</span>}
        </div>
        <span className="inline-chart-value" style={{ color }}>
          {formatValue(latestValue, unit)}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id={`grad-${metric}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3a" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 10, fill: "#666" }}
            interval="preserveStartEnd"
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#666" }}
            domain={domain ?? ["auto", "auto"]}
            axisLine={false}
            tickLine={false}
            width={40}
            tickFormatter={(v) => formatValue(v, unit)}
          />
          <Tooltip
            contentStyle={{
              background: "#1a1a2e",
              border: "1px solid #333",
              borderRadius: 6,
              fontSize: 12,
            }}
            formatter={(v: number) => [formatValue(v, unit), label]}
            labelStyle={{ color: "#888" }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            fill={`url(#grad-${metric})`}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
