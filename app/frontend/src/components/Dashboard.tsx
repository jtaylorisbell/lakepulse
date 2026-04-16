import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchLatestMetrics, type MetricSummary } from "../api";
import MetricCard from "./MetricCard";
import MetricChart from "./MetricChart";

const CATEGORY_ORDER = ["cpu", "memory", "disk", "network", "battery", "thermal", "fan", "gpu"];

function groupByCategory(metrics: MetricSummary[]) {
  const groups = new Map<string, MetricSummary[]>();
  for (const m of metrics) {
    const list = groups.get(m.category) ?? [];
    list.push(m);
    groups.set(m.category, list);
  }
  return [...groups.entries()].sort(
    (a, b) => CATEGORY_ORDER.indexOf(a[0]) - CATEGORY_ORDER.indexOf(b[0])
  );
}

export default function Dashboard() {
  const [selected, setSelected] = useState<MetricSummary | null>(null);

  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ["latest"],
    queryFn: fetchLatestMetrics,
    refetchInterval: 5000,
  });

  if (isLoading) return <div className="loading">Connecting to LakePulse...</div>;
  if (error) return <div className="error">Failed to load metrics</div>;

  const groups = groupByCategory(metrics ?? []);

  return (
    <div className="dashboard">
      <header>
        <h1>LakePulse</h1>
        <p className="subtitle">Real-time Mac hardware metrics</p>
      </header>

      {groups.map(([category, items]) => (
        <section key={category}>
          <h2 className="category-title">{category.toUpperCase()}</h2>
          <div className="metric-grid">
            {items.map((m) => (
              <MetricCard
                key={`${m.category}-${m.metric}-${m.tags}`}
                metric={m}
                onClick={() => setSelected(m)}
              />
            ))}
          </div>
        </section>
      ))}

      {selected && (
        <MetricChart
          category={selected.category}
          metric={selected.metric}
          unit={selected.unit}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
