import type { WikiEvent } from "../api";

const TYPE_COLORS: Record<string, string> = {
  edit: "#4fc3f7",
  new: "#81c784",
  log: "#ffb74d",
  categorize: "#ce93d8",
};

function formatTime(ts: string): string {
  return new Date(ts).toLocaleTimeString();
}

function formatDelta(delta: number | null): string {
  if (delta == null) return "";
  const sign = delta >= 0 ? "+" : "";
  return `${sign}${delta.toLocaleString()}`;
}

function wikiLabel(wiki: string): string {
  return wiki.replace("wiki", "").replace(/wik[a-z]+$/, "") || wiki;
}

interface EventRowProps {
  event: WikiEvent;
}

export default function EventRow({ event }: EventRowProps) {
  const deltaClass =
    event.size_delta != null
      ? event.size_delta >= 0
        ? "delta-positive"
        : "delta-negative"
      : "";

  return (
    <div className="event-row">
      <span className="event-time">{formatTime(event.ts)}</span>
      <span className="event-wiki" title={event.server_name}>
        {wikiLabel(event.wiki)}
      </span>
      <a className="event-title" href={event.title_url || undefined} target="_blank" rel="noopener noreferrer" title={event.comment || undefined}>
        {event.title}
      </a>
      <span className="event-user">{event.user_name}</span>
      <span
        className="event-type"
        style={{ color: TYPE_COLORS[event.event_type] || "#888" }}
      >
        {event.event_type}
      </span>
      <span className={`event-bot ${event.is_bot ? "bot" : "human"}`}>
        {event.is_bot ? "BOT" : "HUMAN"}
      </span>
      <span className={`event-delta ${deltaClass}`}>
        {formatDelta(event.size_delta)}
      </span>
    </div>
  );
}
