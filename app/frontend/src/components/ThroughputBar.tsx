import { useQuery } from "@tanstack/react-query";
import { fetchThroughput } from "../api";
import CounterCard from "./CounterCard";
import LatencyPipeline from "./LatencyPipeline";

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

  return (
    <div className="throughput-section">
      <div className="throughput-bar">
        <CounterCard label="Events / sec" value={data.events_per_sec.toFixed(1)} />
        <CounterCard label="Writes / sec" value={data.writes_per_sec.toFixed(1)} />
        <CounterCard label="Total Today" value={formatCount(data.total_events_today)} />
      </div>
      <LatencyPipeline
        stages={data.stages}
        totalP50={data.latency_p50_ms}
        totalP95={data.latency_p95_ms}
      />
    </div>
  );
}
