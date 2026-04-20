import { useQuery } from "@tanstack/react-query";
import { fetchThroughput } from "../api";
import CounterCard from "./CounterCard";
import LatencyChart from "./LatencyChart";

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function ThroughputBar() {
  const { data } = useQuery({
    queryKey: ["throughput"],
    queryFn: () => fetchThroughput(60),
    refetchInterval: 2000,
  });

  if (!data) return null;

  // Use the first stage (Collector → Lakebase) for the chart
  const writeStage = data.stages[0];

  return (
    <div className="throughput-section">
      <div className="throughput-bar">
        <CounterCard label="Events / sec" value={data.events_per_sec.toFixed(1)} />
        <CounterCard label="Total Today" value={formatCount(data.total_events_today)} />
      </div>
      {writeStage && (
        <LatencyChart p50={writeStage.p50_ms} p95={writeStage.p95_ms} />
      )}
    </div>
  );
}
