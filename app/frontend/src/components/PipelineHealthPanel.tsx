import { useQuery } from "@tanstack/react-query";
import { fetchPipelineHealth } from "../api";

function formatTs(ts: string | null): string {
  if (!ts) return "N/A";
  return new Date(ts).toLocaleTimeString();
}

export default function PipelineHealthPanel() {
  const { data } = useQuery({
    queryKey: ["pipeline-health"],
    queryFn: fetchPipelineHealth,
    refetchInterval: 5000,
  });

  if (!data) return null;

  return (
    <div className="panel health-panel">
      <h3 className="panel-title">Pipeline Health</h3>
      <div className="health-grid">
        <div className="health-item">
          <span className="health-label">SSE Connection</span>
          <span className={`health-status ${data.sse_connected ? "status-ok" : "status-warn"}`}>
            {data.sse_connected ? "Connected" : "Disconnected"}
          </span>
        </div>
        <div className="health-item">
          <span className="health-label">Reconnects</span>
          <span className="health-value">{data.reconnect_count}</span>
        </div>
        <div className="health-item">
          <span className="health-label">Last Event</span>
          <span className="health-value">{formatTs(data.last_event_ts)}</span>
        </div>
        <div className="health-item">
          <span className="health-label">Last Heartbeat</span>
          <span className="health-value">{formatTs(data.last_heartbeat_ts)}</span>
        </div>
        <div className="health-item">
          <span className="health-label">Avg Insert Latency</span>
          <span className="health-value">{data.insert_latency_avg_ms.toFixed(0)} ms</span>
        </div>
        <div className="health-item">
          <span className="health-label">Events (last 1 min)</span>
          <span className="health-value">{data.events_in_last_minute.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}
