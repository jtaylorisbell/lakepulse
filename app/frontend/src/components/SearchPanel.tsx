import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchSearchEvents, type WikiEvent } from "../api";
import EventTimeline from "./EventTimeline";

function formatTime(ts: string): string {
  return new Date(ts).toLocaleTimeString();
}

function formatDelta(delta: number | null): string {
  if (delta == null) return "";
  const sign = delta >= 0 ? "+" : "";
  return `${sign}${delta.toLocaleString()}`;
}

export default function SearchPanel() {
  const [q, setQ] = useState("");
  const [wiki, setWiki] = useState("");
  const [user, setUser] = useState("");
  const [eventType, setEventType] = useState("");
  const [minutes, setMinutes] = useState("60");
  const [page, setPage] = useState(1);
  const [expandedTitle, setExpandedTitle] = useState<string | null>(null);

  const params: Record<string, string> = { page: String(page), page_size: "50", minutes };
  if (q) params.q = q;
  if (wiki) params.wiki = wiki;
  if (user) params.user = user;
  if (eventType) params.event_type = eventType;

  const { data, isFetching } = useQuery({
    queryKey: ["search", params],
    queryFn: () => fetchSearchEvents(params),
    enabled: !!(q || wiki || user || eventType),
    placeholderData: (prev) => prev,
  });

  const totalPages = data ? Math.ceil(data.total_count / 50) : 0;

  return (
    <div className="panel search-panel">
      <h3 className="panel-title">Search &amp; History</h3>

      <div className="search-controls">
        <input
          placeholder="Page title..."
          value={q}
          onChange={(e) => { setQ(e.target.value); setPage(1); }}
        />
        <input
          placeholder="Wiki (e.g. enwiki)"
          value={wiki}
          onChange={(e) => { setWiki(e.target.value); setPage(1); }}
        />
        <input
          placeholder="User..."
          value={user}
          onChange={(e) => { setUser(e.target.value); setPage(1); }}
        />
        <select value={eventType} onChange={(e) => { setEventType(e.target.value); setPage(1); }}>
          <option value="">All types</option>
          <option value="edit">Edit</option>
          <option value="new">New</option>
          <option value="log">Log</option>
          <option value="categorize">Categorize</option>
        </select>
        <select value={minutes} onChange={(e) => { setMinutes(e.target.value); setPage(1); }}>
          <option value="5">Last 5 min</option>
          <option value="15">Last 15 min</option>
          <option value="60">Last 1 hour</option>
          <option value="360">Last 6 hours</option>
          <option value="1440">Last 24 hours</option>
        </select>
      </div>

      {data && (
        <>
          <div className="search-info">
            {data.total_count.toLocaleString()} results
            {isFetching && <span className="search-loading"> (loading...)</span>}
          </div>

          <div className="search-table">
            <div className="search-table-header">
              <span>Time</span>
              <span>Wiki</span>
              <span>Title</span>
              <span>User</span>
              <span>Type</span>
              <span>Delta</span>
            </div>
            {data.events.map((e: WikiEvent) => (
              <div key={e.event_id}>
                <div
                  className="search-table-row"
                  onClick={() => setExpandedTitle(expandedTitle === e.title ? null : e.title)}
                >
                  <span>{formatTime(e.ts)}</span>
                  <span>{e.wiki}</span>
                  <span className="search-title">{e.title}</span>
                  <span>{e.user_name}</span>
                  <span>{e.event_type}</span>
                  <span className={e.size_delta != null ? (e.size_delta >= 0 ? "delta-positive" : "delta-negative") : ""}>
                    {formatDelta(e.size_delta)}
                  </span>
                </div>
                {expandedTitle === e.title && (
                  <EventTimeline title={e.title} wiki={e.wiki} />
                )}
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="search-pagination">
              <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button>
              <span>Page {page} of {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          )}
        </>
      )}

      {!data && !isFetching && (
        <div className="search-hint">Enter a search term to query historical events</div>
      )}
    </div>
  );
}
