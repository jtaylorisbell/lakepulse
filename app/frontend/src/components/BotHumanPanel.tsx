import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { fetchBotHuman } from "../api";

const COLORS = { bot: "#ffb74d", human: "#4fc3f7" };

export default function BotHumanPanel() {
  const { data } = useQuery({
    queryKey: ["bot-human"],
    queryFn: () => fetchBotHuman(5),
    refetchInterval: 5000,
  });

  if (!data) return <div className="panel analytics-panel skeleton" />;

  const pieData = [
    { name: "Bot", value: data.bot_count },
    { name: "Human", value: data.human_count },
  ];

  return (
    <div className="panel analytics-panel">
      <h3 className="panel-title">Bot vs Human</h3>
      <div className="bot-human-content">
        <div className="donut-container">
          <ResponsiveContainer width="100%" height={140}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={35}
                outerRadius={55}
                dataKey="value"
                stroke="none"
              >
                <Cell fill={COLORS.bot} />
                <Cell fill={COLORS.human} />
              </Pie>
              <Tooltip
                contentStyle={{ background: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: 6 }}
                itemStyle={{ color: "#e0e0e0" }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="donut-legend">
            <span style={{ color: COLORS.bot }}>Bot {data.bot_percent.toFixed(0)}%</span>
            <span style={{ color: COLORS.human }}>Human {(100 - data.bot_percent).toFixed(0)}%</span>
          </div>
        </div>
        <div className="top-editors">
          <div className="editor-list">
            <h4>Top Bots</h4>
            {data.top_bots.slice(0, 5).map((b) => (
              <div key={b.user_name} className="editor-row">
                <span className="editor-name" title={b.user_name}>{b.user_name}</span>
                <span className="editor-count">{b.count}</span>
              </div>
            ))}
          </div>
          <div className="editor-list">
            <h4>Top Humans</h4>
            {data.top_humans.slice(0, 5).map((h) => (
              <div key={h.user_name} className="editor-row">
                <span className="editor-name" title={h.user_name}>{h.user_name}</span>
                <span className="editor-count">{h.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
