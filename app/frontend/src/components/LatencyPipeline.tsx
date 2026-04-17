import type { LatencyStage } from "../api";

const STAGE_COLORS = ["#4fc3f7", "#ffb74d", "#ce93d8"];

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms.toFixed(0)}ms`;
}

interface LatencyPipelineProps {
  stages: LatencyStage[];
  totalP50: number;
  totalP95: number;
}

export default function LatencyPipeline({ stages, totalP50, totalP95 }: LatencyPipelineProps) {
  if (stages.length === 0) return null;

  const total = stages.reduce((sum, s) => sum + s.p50_ms, 0);

  // Node labels: collector → ZeroBus → Delta → Lakebase
  const nodes = ["C", "ZB", "PG"];

  return (
    <div className="latency-pipeline">
      <div className="lp-header">
        <span className="lp-title">Pipeline Latency</span>
        <span className="lp-total">
          <span className="lp-total-value">{formatMs(totalP50)}</span>
          <span className="lp-total-label">p50</span>
          <span className="lp-total-sep">/</span>
          <span className="lp-total-value">{formatMs(totalP95)}</span>
          <span className="lp-total-label">p95</span>
        </span>
      </div>

      <div className="lp-flow">
        <div className="lp-node lp-node-source">{nodes[0]}</div>

        {stages.map((stage, i) => {
          const pct = total > 0 ? Math.max((stage.p50_ms / total) * 100, 8) : 33;
          return (
            <div key={stage.label} className="lp-segment-wrap" style={{ flex: `${pct} 0 0%` }}>
              <div className="lp-connector" />
              <div className="lp-segment" style={{ background: STAGE_COLORS[i % STAGE_COLORS.length] }}>
                <span className="lp-seg-time">{formatMs(stage.p50_ms)}</span>
              </div>
              <div className="lp-connector" />
              <div className={`lp-node ${i < stages.length - 1 ? "lp-node-mid" : "lp-node-dest"}`}>
                {nodes[i + 1]}
              </div>
            </div>
          );
        })}
      </div>

      <div className="lp-labels">
        <span className="lp-label-edge">Collector</span>
        {stages.map((stage, i) => (
          <span key={stage.label} className="lp-label-stage" style={{ color: STAGE_COLORS[i % STAGE_COLORS.length] }}>
            {stage.label}
            <span className="lp-label-p95">p95: {formatMs(stage.p95_ms)}</span>
          </span>
        ))}
        <span className="lp-label-edge">Lakebase</span>
      </div>
    </div>
  );
}
