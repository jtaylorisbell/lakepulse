import { useQuery } from "@tanstack/react-query";
import { fetchBiggestEdits } from "../api";

function formatDelta(delta: number): string {
  const sign = delta >= 0 ? "+" : "";
  return `${sign}${delta.toLocaleString()}`;
}

function formatTime(ts: string): string {
  return new Date(ts).toLocaleTimeString();
}

function wikiLabel(wiki: string): string {
  return wiki.replace("wiki", "").replace(/wik[a-z]+$/, "") || wiki;
}

export default function BiggestEditsPanel() {
  const { data } = useQuery({
    queryKey: ["biggest-edits"],
    queryFn: () => fetchBiggestEdits(5, 15),
    refetchInterval: 5000,
  });

  if (!data) return <div className="panel analytics-panel skeleton" />;

  const maxAbs = Math.max(...data.map((e) => Math.abs(e.size_delta)), 1);

  return (
    <div className="panel analytics-panel">
      <h3 className="panel-title">Biggest Edits (5 min)</h3>
      <div className="biggest-edits-list">
        {data.map((edit) => {
          const pct = (Math.abs(edit.size_delta) / maxAbs) * 100;
          const isPositive = edit.size_delta >= 0;
          return (
            <div key={edit.event_id} className="biggest-edit-row">
              <div className="be-info">
                <a className="be-title" href={edit.title_url || undefined} target="_blank" rel="noopener noreferrer" title={edit.title}>{edit.title}</a>
                <span className="be-meta">
                  {wikiLabel(edit.wiki)} &middot; {edit.user_name} &middot; {formatTime(edit.ts)}
                </span>
              </div>
              <div className="be-bar-wrap">
                <div
                  className={`be-bar ${isPositive ? "be-bar-pos" : "be-bar-neg"}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className={`be-delta ${isPositive ? "delta-positive" : "delta-negative"}`}>
                {formatDelta(edit.size_delta)}
              </span>
            </div>
          );
        })}
        {data.length === 0 && <div className="feed-empty">No edits with size data</div>}
      </div>
    </div>
  );
}
