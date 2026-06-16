"use client";

import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, Legend,
} from "recharts";

interface Props {
  data: any[];
  fullWidth?: boolean;
  comfortMin?: number;
  comfortMax?: number;
}

const STATUS_DOT: Record<string, string> = {
  within_range: "#10b981",
  warning: "#f59e0b",
  unsafe: "#f97316",
  infeasible: "#ef4444",
};

export function ComfortChart({ data, fullWidth, comfortMin = 22, comfortMax = 26 }: Props) {
  const formatted = data.map((d, i) => ({
    t: i,
    label: d.timestamp_local
      ? new Date(d.timestamp_local).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
      : `T${i}`,
    indoor: d.estimated_indoor_temp_c ?? null,
    outdoor: null as null | number,
    status: d.comfort_status ?? "within_range",
    color: STATUS_DOT[d.comfort_status ?? "within_range"],
  }));

  // comfortMin/Max come from the profile — already passed as props

  const statusCounts = data.reduce((acc: Record<string, number>, d) => {
    const s = d.comfort_status || "within_range";
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className={`rounded-xl border border-white/10 bg-white/[0.03] p-6 ${fullWidth ? "" : ""}`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-white font-semibold">Indoor Temperature & Comfort</h3>
          <p className="text-slate-400 text-xs mt-1">
            Comfort zone: {comfortMin}°C – {comfortMax}°C
          </p>
        </div>

        <div className="flex gap-3 text-xs">
          {Object.entries(statusCounts).map(([status, count]) => (
            <span
              key={status}
              className="flex items-center gap-1.5"
              style={{ color: STATUS_DOT[status] ?? "#94a3b8" }}
            >
              <span
                className="w-2 h-2 rounded-full inline-block"
                style={{ background: STATUS_DOT[status] ?? "#94a3b8" }}
              />
              {status.replace("_", " ")} ({count})
            </span>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={formatted} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="label"
            tick={{ fill: "#64748b", fontSize: 10 }}
            interval={Math.floor(formatted.length / 8)}
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 10 }}
            domain={["auto", "auto"]}
            width={35}
            unit="°C"
          />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#94a3b8" }}
            formatter={(v: unknown) => [`${(v as number)?.toFixed(1)}°C`, ""]}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
          <ReferenceLine y={comfortMin} stroke="#10b981" strokeDasharray="4 2" opacity={0.5} label={{ value: "Min", fill: "#10b981", fontSize: 10 }} />
          <ReferenceLine y={comfortMax} stroke="#f59e0b" strokeDasharray="4 2" opacity={0.5} label={{ value: "Max", fill: "#f59e0b", fontSize: 10 }} />
          <Line
            type="monotone"
            dataKey="indoor"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={false}
            name="Indoor Temp"
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
