import type { MetricSummary } from "../api";

function formatValue(value: number, unit: string): string {
  if (unit === "bytes") {
    if (value >= 1e9) return `${(value / 1e9).toFixed(1)} GB`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(1)} MB`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(1)} KB`;
    return `${value} B`;
  }
  if (unit === "percent") return `${value.toFixed(1)}%`;
  if (unit === "mhz") return `${value.toFixed(0)} MHz`;
  if (unit === "rpm") return `${value.toFixed(0)} RPM`;
  if (unit === "watts") return `${value.toFixed(2)} W`;
  if (unit === "load") return value.toFixed(2);
  return String(value);
}

function friendlyName(metric: string): string {
  return metric
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

interface Props {
  metric: MetricSummary;
  onClick?: () => void;
}

export default function MetricCard({ metric, onClick }: Props) {
  return (
    <div className="metric-card" onClick={onClick}>
      <div className="metric-name">{friendlyName(metric.metric)}</div>
      <div className="metric-value">
        {formatValue(metric.latest_value, metric.unit)}
      </div>
      <div className="metric-time">
        {new Date(metric.ts).toLocaleTimeString()}
      </div>
    </div>
  );
}
