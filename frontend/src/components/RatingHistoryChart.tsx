import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ScoreEvent } from "@/api/types";

export default function RatingHistoryChart({
  history,
}: {
  history: ScoreEvent[];
}) {
  return (
    <div className="history-chart">
      <ResponsiveContainer width="100%" height={100}>
        <AreaChart data={history}>
          <defs>
            <linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--green)" stopOpacity={0.3} />
              <stop offset="100%" stopColor="var(--green)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis hide dataKey="created_at" />
          <YAxis hide domain={[0, 100]} />
          <Tooltip
            labelFormatter={() => "Изменение готовности"}
            formatter={(value) => [`${value} баллов`, "Рейтинг"]}
          />
          <Area
            type="monotone"
            dataKey="score"
            stroke="var(--green)"
            fill="url(#scoreFill)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
