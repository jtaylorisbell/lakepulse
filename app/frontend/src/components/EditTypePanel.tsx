import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { fetchEditTypes } from "../api";

const TYPE_COLORS: Record<string, string> = {
  edit: "#4fc3f7",
  new: "#81c784",
  log: "#ffb74d",
  categorize: "#ce93d8",
};

export default function EditTypePanel() {
  const { data } = useQuery({
    queryKey: ["edit-types"],
    queryFn: () => fetchEditTypes(5),
    refetchInterval: 5000,
  });

  if (!data) return <div className="panel analytics-panel skeleton" />;

  const pieData = [
    { name: "Edit", value: data.edit },
    { name: "New", value: data.new },
    { name: "Log", value: data.log },
    { name: "Categorize", value: data.categorize },
  ].filter((d) => d.value > 0);

  const total = data.edit + data.new + data.log + data.categorize;

  return (
    <div className="panel analytics-panel">
      <h3 className="panel-title">Edit Types</h3>
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
              {pieData.map((entry) => (
                <Cell key={entry.name} fill={TYPE_COLORS[entry.name.toLowerCase()] || "#888"} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: 6 }}
              itemStyle={{ color: "#e0e0e0" }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="type-legend">
          {pieData.map((d) => (
            <span key={d.name} className="type-legend-item">
              <span
                className="legend-dot"
                style={{ background: TYPE_COLORS[d.name.toLowerCase()] }}
              />
              {d.name}{" "}
              <span className="legend-pct">
                {total > 0 ? ((d.value / total) * 100).toFixed(0) : 0}%
              </span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
