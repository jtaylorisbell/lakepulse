import { useQuery } from "@tanstack/react-query";
import { fetchLatestMetrics, type MetricSummary } from "../api";
import MetricCard from "./MetricCard";
import InlineChart from "./InlineChart";

/** Metrics that should be displayed as time-series charts. */
const CHARTED_METRICS: Record<string, { label: string; color: string; domain?: [number, number] }> = {
  cpu_percent_total: { label: "CPU Usage", color: "#4fc3f7", domain: [0, 100] },
  memory_percent: { label: "Memory Usage", color: "#ce93d8", domain: [0, 100] },
  battery_percent: { label: "Battery", color: "#81c784", domain: [0, 100] },
  swap_percent: { label: "Swap Usage", color: "#ffb74d", domain: [0, 100] },
};

/** Metrics to exclude from stat cards (already shown as charts or not useful standalone). */
const HIDDEN_FROM_CARDS = new Set([
  ...Object.keys(CHARTED_METRICS),
  "cpu_percent", // per-core; not useful without tags in the PK
]);

function getMetric(metrics: MetricSummary[], name: string): MetricSummary | undefined {
  return metrics.find((m) => m.metric === name);
}

function getCategory(metrics: MetricSummary[], category: string): MetricSummary[] {
  return metrics.filter((m) => m.category === category && !HIDDEN_FROM_CARDS.has(m.metric));
}

export default function Dashboard() {
  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ["latest"],
    queryFn: fetchLatestMetrics,
    refetchInterval: 5000,
  });

  if (isLoading) return <div className="loading">Connecting to LakePulse...</div>;
  if (error) return <div className="error">Failed to load metrics</div>;

  const all = metrics ?? [];
  const cpuTotal = getMetric(all, "cpu_percent_total");
  const memPct = getMetric(all, "memory_percent");
  const battPct = getMetric(all, "battery_percent");
  const swapPct = getMetric(all, "swap_percent");

  const cpuCards = getCategory(all, "cpu");
  const memCards = getCategory(all, "memory");
  const diskCards = getCategory(all, "disk");
  const netCards = getCategory(all, "network");
  const battCards = getCategory(all, "battery");


  return (
    <div className="dashboard">
      <header>
        <div className="header-row">
          <div>
            <h1>LakePulse</h1>
            <p className="subtitle">Real-time Mac hardware metrics</p>
          </div>
          <div className="live-indicator"><span className="live-dot" />LIVE</div>
        </div>
      </header>

      {/* Primary charts row */}
      <div className="charts-row">
        {cpuTotal && (
          <InlineChart
            category="cpu" metric="cpu_percent_total" unit="percent"
            label={CHARTED_METRICS.cpu_percent_total.label}
            latestValue={cpuTotal.latest_value}
            color={CHARTED_METRICS.cpu_percent_total.color}
            domain={CHARTED_METRICS.cpu_percent_total.domain}
          />
        )}
        {memPct && (
          <InlineChart
            category="memory" metric="memory_percent" unit="percent"
            label={CHARTED_METRICS.memory_percent.label}
            latestValue={memPct.latest_value}
            color={CHARTED_METRICS.memory_percent.color}
            domain={CHARTED_METRICS.memory_percent.domain}
          />
        )}
      </div>

      <div className="charts-row">
        {battPct && (
          <InlineChart
            category="battery" metric="battery_percent" unit="percent"
            label={CHARTED_METRICS.battery_percent.label}
            latestValue={battPct.latest_value}
            color={CHARTED_METRICS.battery_percent.color}
            domain={CHARTED_METRICS.battery_percent.domain}
          />
        )}
        {swapPct && (
          <InlineChart
            category="memory" metric="swap_percent" unit="percent"
            label={CHARTED_METRICS.swap_percent.label}
            latestValue={swapPct.latest_value}
            color={CHARTED_METRICS.swap_percent.color}
            domain={CHARTED_METRICS.swap_percent.domain}
          />
        )}
      </div>

      {/* Stat cards by category */}
      {cpuCards.length > 0 && (
        <section>
          <h2 className="category-title">CPU</h2>
          <div className="metric-grid">
            {cpuCards.map((m) => <MetricCard key={m.metric} metric={m} />)}
          </div>
        </section>
      )}

      {memCards.length > 0 && (
        <section>
          <h2 className="category-title">MEMORY</h2>
          <div className="metric-grid">
            {memCards.map((m) => <MetricCard key={m.metric} metric={m} />)}
          </div>
        </section>
      )}

      {diskCards.length > 0 && (
        <section>
          <h2 className="category-title">DISK</h2>
          <div className="metric-grid">
            {diskCards.map((m) => <MetricCard key={m.metric} metric={m} />)}
          </div>
        </section>
      )}

      {netCards.length > 0 && (
        <section>
          <h2 className="category-title">NETWORK</h2>
          <div className="metric-grid">
            {netCards.map((m) => <MetricCard key={m.metric} metric={m} />)}
          </div>
        </section>
      )}

      {battCards.length > 0 && (
        <section>
          <h2 className="category-title">BATTERY</h2>
          <div className="metric-grid">
            {battCards.map((m) => <MetricCard key={m.metric} metric={m} />)}
          </div>
        </section>
      )}
    </div>
  );
}
