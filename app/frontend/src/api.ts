const BASE = "/api";

// ── Types ────────────────────────────────────────────────────────────────────

export interface WikiEvent {
  event_id: number;
  event_type: string;
  ts: string;
  wiki: string;
  server_name: string;
  title: string;
  title_url: string | null;
  user_name: string;
  is_bot: boolean;
  is_minor: boolean;
  is_new: boolean;
  namespace: number;
  comment: string | null;
  length_old: number | null;
  length_new: number | null;
  revision_old: number | null;
  revision_new: number | null;
  size_delta: number | null;
}

export interface LatencyStage {
  label: string;
  p50_ms: number;
  p95_ms: number;
}

export interface ThroughputStats {
  events_per_sec: number;
  writes_per_sec: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  total_events_today: number;
  stages: LatencyStage[];
}

export interface BotHumanSplit {
  total: number;
  bot_count: number;
  human_count: number;
  bot_percent: number;
  top_bots: Array<{ user_name: string; count: number }>;
  top_humans: Array<{ user_name: string; count: number }>;
}

export interface EditTypeBreakdown {
  edit: number;
  new: number;
  log: number;
  categorize: number;
}

export interface WikiActivity {
  wiki: string;
  server_name: string;
  count: number;
  events_per_sec: number;
}

export interface BiggestEdit {
  event_id: number;
  title: string;
  wiki: string;
  user_name: string;
  size_delta: number;
  ts: string;
}

export interface PipelineHealth {
  sse_connected: boolean;
  last_event_ts: string | null;
  last_heartbeat_ts: string | null;
  reconnect_count: number;
  insert_latency_avg_ms: number;
  events_in_last_minute: number;
}

export interface SearchResult {
  events: WikiEvent[];
  total_count: number;
}

// ── SSE helper ───────────────────────────────────────────────────────────────

export function subscribeToEvents(
  onEvent: (event: WikiEvent) => void,
  onError?: () => void,
): EventSource {
  const es = new EventSource(`${BASE}/events/stream`);
  es.onmessage = (msg) => onEvent(JSON.parse(msg.data));
  if (onError) es.onerror = onError;
  return es;
}

// ── REST fetchers ────────────────────────────────────────────────────────────

export async function fetchRecentEvents(limit = 50): Promise<WikiEvent[]> {
  const res = await fetch(`${BASE}/events/recent?limit=${limit}`);
  return res.json();
}

export async function fetchThroughput(windowSeconds = 60): Promise<ThroughputStats> {
  const res = await fetch(`${BASE}/stats/throughput?window_seconds=${windowSeconds}`);
  return res.json();
}

export async function fetchBotHuman(minutes = 5): Promise<BotHumanSplit> {
  const res = await fetch(`${BASE}/stats/bot-human?minutes=${minutes}`);
  return res.json();
}

export async function fetchEditTypes(minutes = 5): Promise<EditTypeBreakdown> {
  const res = await fetch(`${BASE}/stats/edit-types?minutes=${minutes}`);
  return res.json();
}

export async function fetchTopWikis(minutes = 5, limit = 15): Promise<WikiActivity[]> {
  const res = await fetch(`${BASE}/stats/top-wikis?minutes=${minutes}&limit=${limit}`);
  return res.json();
}

export async function fetchBiggestEdits(minutes = 5, limit = 20): Promise<BiggestEdit[]> {
  const res = await fetch(`${BASE}/stats/biggest-edits?minutes=${minutes}&limit=${limit}`);
  return res.json();
}

export async function fetchSearchEvents(params: Record<string, string>): Promise<SearchResult> {
  const qs = new URLSearchParams(params);
  const res = await fetch(`${BASE}/events/search?${qs}`);
  return res.json();
}

export async function fetchPipelineHealth(): Promise<PipelineHealth> {
  const res = await fetch(`${BASE}/health/pipeline`);
  return res.json();
}
