import { useEffect, useRef, useState, useCallback } from "react";
import { subscribeToEvents, fetchRecentEvents, type WikiEvent } from "../api";

export function useEventStream(maxEvents = 100) {
  const [events, setEvents] = useState<WikiEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const seenIds = useRef(new Set<number>());

  const mergeEvents = useCallback((incoming: WikiEvent[]) => {
    setEvents((prev) => {
      const newEvents = incoming.filter((e) => !seenIds.current.has(e.event_id));
      if (newEvents.length === 0) return prev;
      for (const e of newEvents) seenIds.current.add(e.event_id);
      const merged = [...newEvents, ...prev];
      merged.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());
      // Keep seenIds bounded
      const kept = merged.slice(0, maxEvents);
      seenIds.current = new Set(kept.map((e) => e.event_id));
      return kept;
    });
  }, [maxEvents]);

  useEffect(() => {
    // Initial load + polling fallback every 3s
    const poll = () => {
      fetchRecentEvents(maxEvents).then(mergeEvents).catch(() => {});
    };
    poll();
    const interval = setInterval(poll, 3000);

    // SSE for real-time push when available
    const es = subscribeToEvents(
      (event) => {
        setConnected(true);
        mergeEvents([event]);
      },
      () => setConnected(false),
    );
    es.addEventListener("open", () => setConnected(true));

    return () => {
      clearInterval(interval);
      es.close();
    };
  }, [maxEvents, mergeEvents]);

  return { events, connected };
}
