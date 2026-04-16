import type { MetricSummary } from "../api";
import { getDescription } from "../metricDescriptions";

export function formatValue(value: number, unit: string): string {
  if (unit === "bytes") {
    if (value >= 1e12) return `${(value / 1e12).toFixed(1)} TB`;
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
  if (unit === "boolean") return value === 1 ? "Yes" : "No";
  return String(value);
}

export function friendlyName(metric: string): string {
  return metric
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

interface Props {
  metric: MetricSummary;
}

export default function MetricCard({ metric }: Props) {
  const description = getDescription(metric.metric);

  return (
    <div className="metric-card">
      <div className="metric-name">
        {friendlyName(metric.metric)}
        {description && <span className="tooltip-icon" title={description}>?</span>}
      </div>
      <div className="metric-value">
        {formatValue(metric.latest_value, metric.unit)}
      </div>
    </div>
  );
}
