import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { fetchTopWikis } from "../api";

function wikiLabel(wiki: string): string {
  return wiki.replace("wiki", "").replace(/wik[a-z]+$/, "") || wiki;
}

export default function TopWikisPanel() {
  const { data } = useQuery({
    queryKey: ["top-wikis"],
    queryFn: () => fetchTopWikis(5, 12),
    refetchInterval: 5000,
  });

  if (!data) return <div className="panel analytics-panel skeleton" />;

  const chartData = data.map((w) => ({
    wiki: wikiLabel(w.wiki),
    count: w.count,
    full: w.server_name,
  }));

  return (
    <div className="panel analytics-panel analytics-panel--fill">
      <h3 className="panel-title">Top Wikis (5 min)</h3>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ left: 60, right: 12 }}>
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="wiki"
            tick={{ fill: "#888", fontSize: 11 }}
            width={55}
          />
          <Tooltip
            contentStyle={{ background: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: 6 }}
            itemStyle={{ color: "#e0e0e0" }}
            labelStyle={{ color: "#888" }}
            formatter={(value: unknown) => [Number(value).toLocaleString(), "events"]}
            labelFormatter={(label: unknown, payload: readonly unknown[]) => {
              const entry = payload?.[0] as { payload?: { full?: string } } | undefined;
              return entry?.payload?.full || String(label);
            }}
          />
          <Bar dataKey="count" fill="#4fc3f7" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
