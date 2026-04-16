import { useQuery } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { fetchMetricHistory } from "../api";

interface Props {
  category: string;
  metric: string;
  unit: string;
  onClose: () => void;
}

export default function MetricChart({ category, metric, unit, onClose }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["history", category, metric],
    queryFn: () => fetchMetricHistory(category, metric, 30),
    refetchInterval: 5000,
  });

  const chartData = (data ?? []).map((d) => ({
    time: new Date(d.ts).toLocaleTimeString(),
    value: d.value,
  }));

  return (
    <div className="chart-overlay">
      <div className="chart-container">
        <div className="chart-header">
          <h3>
            {category} / {metric}
          </h3>
          <button onClick={onClose}>&times;</button>
        </div>
        {isLoading ? (
          <p>Loading...</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis
                dataKey="time"
                tick={{ fontSize: 11, fill: "#999" }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#999" }}
                label={{ value: unit, angle: -90, position: "insideLeft", fill: "#999" }}
              />
              <Tooltip
                contentStyle={{ background: "#1a1a2e", border: "1px solid #444" }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#4fc3f7"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
