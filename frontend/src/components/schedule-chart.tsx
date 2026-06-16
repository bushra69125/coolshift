"use client";

import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend,
} from "recharts";

interface Props {
  data: any[];
  fullWidth?: boolean;
}

export function ScheduleChart({ data, fullWidth }: Props) {
  const formatted = data.map((d, i) => ({
    t: i,
    label: d.timestamp_local ? new Date(d.timestamp_local).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }) : `T${i}`,
    grid: d.grid_energy_kwh ?? 0,
    solar: d.solar_energy_used_kwh ?? 0,
    battery: d.battery_discharge_kwh ?? 0,
    cost: d.interval_cost_pkr ?? 0,
  }));

  return (
    <div className={`rounded-xl border border-white/10 bg-white/[0.03] p-6 ${fullWidth ? "col-span-2" : ""}`}>
      <div className="mb-4">
        <h3 className="text-white font-semibold">Energy Schedule (kWh per interval)</h3>
        <p className="text-slate-400 text-xs mt-1">15-minute interval breakdown — grid vs solar vs battery</p>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={formatted} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="gridGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="solarGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="batGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 10 }} interval={Math.floor(formatted.length / 6)} />
          <YAxis tick={{ fill: "#64748b", fontSize: 10 }} width={35} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#94a3b8" }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
          <Area type="monotone" dataKey="grid" stackId="1" stroke="#3b82f6" fill="url(#gridGrad)" name="Grid (kWh)" strokeWidth={2} />
          <Area type="monotone" dataKey="solar" stackId="1" stroke="#f59e0b" fill="url(#solarGrad)" name="Solar (kWh)" strokeWidth={2} />
          <Area type="monotone" dataKey="battery" stackId="1" stroke="#10b981" fill="url(#batGrad)" name="Battery (kWh)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
