import { useQuery } from "@tanstack/react-query";
import { fetchSearchEvents } from "../api";

function formatTime(ts: string): string {
  return new Date(ts).toLocaleString();
}

interface EventTimelineProps {
  title: string;
  wiki: string;
}

export default function EventTimeline({ title, wiki }: EventTimelineProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["timeline", title, wiki],
    queryFn: () =>
      fetchSearchEvents({ q: title, wiki, minutes: "1440", page_size: "20" }),
  });

  if (isLoading) return <div className="timeline-loading">Loading timeline...</div>;

  return (
    <div className="timeline">
      <h4 className="timeline-title">Edit Timeline: {title}</h4>
      {data?.events.map((e) => (
        <div key={e.event_id} className="timeline-entry">
          <span className="timeline-ts">{formatTime(e.ts)}</span>
          <span className="timeline-user">{e.user_name}</span>
          <span className="timeline-comment">{e.comment || "(no summary)"}</span>
          {e.size_delta != null && (
            <span className={e.size_delta >= 0 ? "delta-positive" : "delta-negative"}>
              {e.size_delta >= 0 ? "+" : ""}{e.size_delta}
            </span>
          )}
        </div>
      ))}
      {data?.events.length === 0 && <div className="feed-empty">No edit history found</div>}
    </div>
  );
}
