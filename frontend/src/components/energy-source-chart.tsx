"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface Props {
  data: any[];
  fullWidth?: boolean;
}

const COLORS = ["#3b82f6", "#f59e0b", "#10b981"];

export function EnergySourceChart({ data, fullWidth }: Props) {
  const grid = data.reduce((s, d) => s + (d.grid_energy_kwh ?? 0), 0);
  const solar = data.reduce((s, d) => s + (d.solar_energy_used_kwh ?? 0), 0);
  const battery = data.reduce((s, d) => s + (d.battery_discharge_kwh ?? 0), 0);

  const chartData = [
    { name: "Grid", value: parseFloat(grid.toFixed(3)) },
    { name: "Solar", value: parseFloat(solar.toFixed(3)) },
    { name: "Battery", value: parseFloat(battery.toFixed(3)) },
  ].filter((d) => d.value > 0);

  const total = grid + solar + battery;

  return (
    <div className={`rounded-xl border border-white/10 bg-white/[0.03] p-6 ${fullWidth ? "col-span-2" : ""}`}>
      <div className="mb-4">
        <h3 className="text-white font-semibold">Energy Source Mix</h3>
        <p className="text-slate-400 text-xs mt-1">Distribution of energy supply over the period</p>
      </div>

      <div className="flex items-center gap-6">
        <ResponsiveContainer width={180} height={180}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={80}
              paddingAngle={3}
              dataKey="value"
            >
              {chartData.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }}
              formatter={(v: unknown) => [`${(v as number).toFixed(3)} kWh`, ""]}
            />
          </PieChart>
        </ResponsiveContainer>

        <div className="flex-1 space-y-3">
          {[
            { label: "Grid", value: grid, color: "#3b82f6" },
            { label: "Solar", value: solar, color: "#f59e0b" },
            { label: "Battery", value: battery, color: "#10b981" },
          ].map((item) => (
            <div key={item.label}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-400 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full inline-block" style={{ background: item.color }} />
                  {item.label}
                </span>
                <span className="text-white font-medium">{item.value.toFixed(2)} kWh</span>
              </div>
              <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${total > 0 ? (item.value / total) * 100 : 0}%`,
                    background: item.color,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
