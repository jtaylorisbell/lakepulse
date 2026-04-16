const BASE = "/api";

export interface MetricSummary {
  category: string;
  metric: string;
  latest_value: number;
  unit: string;
  tags: string | null;
  ts: string;
}

export interface MetricRecord {
  ts: string;
  hostname: string;
  category: string;
  metric: string;
  value: number;
  unit: string;
  tags: string | null;
}

export async function fetchLatestMetrics(): Promise<MetricSummary[]> {
  const res = await fetch(`${BASE}/metrics/latest`);
  return res.json();
}

export async function fetchMetricHistory(
  category: string,
  metric: string,
  minutes = 30
): Promise<MetricRecord[]> {
  const params = new URLSearchParams({ category, metric, minutes: String(minutes) });
  const res = await fetch(`${BASE}/metrics/history?${params}`);
  return res.json();
}

export async function fetchCategories(): Promise<string[]> {
  const res = await fetch(`${BASE}/metrics/categories`);
  return res.json();
}
