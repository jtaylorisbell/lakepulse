import type { WikiEvent } from "../api";
import EventRow from "./EventRow";

interface LiveFeedProps {
  events: WikiEvent[];
}

export default function LiveFeed({ events }: LiveFeedProps) {
  return (
    <div className="panel live-feed">
      <h3 className="panel-title">Live Firehose</h3>
      <div className="feed-header">
        <span>Time</span>
        <span>Wiki</span>
        <span>Page</span>
        <span>User</span>
        <span>Type</span>
        <span>Agent</span>
        <span>Delta</span>
      </div>
      <div className="feed-scroll">
        {events.map((e) => (
          <EventRow key={e.event_id} event={e} />
        ))}
        {events.length === 0 && (
          <div className="feed-empty">Waiting for events...</div>
        )}
      </div>
    </div>
  );
}
