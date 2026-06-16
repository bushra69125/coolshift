"use client";

import { comfortBadgeClass } from "@/lib/utils";

interface Props {
  data: any[];
}

export function ScheduleTable({ data }: Props) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] overflow-hidden">
      <div className="p-4 border-b border-white/10">
        <h3 className="text-white font-semibold">Interval Schedule</h3>
        <p className="text-slate-400 text-xs mt-0.5">Showing first {data.length} of total intervals</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-slate-400 text-xs uppercase tracking-wider">
              <th className="text-left px-4 py-3">Time</th>
              <th className="text-right px-4 py-3">AC On</th>
              <th className="text-right px-4 py-3">Setpoint</th>
              <th className="text-right px-4 py-3">Grid kWh</th>
              <th className="text-right px-4 py-3">Solar kWh</th>
              <th className="text-right px-4 py-3">Cost PKR</th>
              <th className="text-right px-4 py-3">Temp °C</th>
              <th className="px-4 py-3">Comfort</th>
              <th className="px-4 py-3">Reason</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr
                key={i}
                className="border-b border-white/[0.05] hover:bg-white/[0.02] transition-colors"
              >
                <td className="px-4 py-2.5 text-slate-300 font-mono text-xs">
                  {row.timestamp_local
                    ? new Date(row.timestamp_local).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
                    : `T${i}`}
                </td>
                <td className="px-4 py-2.5 text-right text-white">{row.recommended_ac_units_on}</td>
                <td className="px-4 py-2.5 text-right text-slate-300">
                  {row.recommended_ac_setpoint_c != null ? `${row.recommended_ac_setpoint_c}°C` : "—"}
                </td>
                <td className="px-4 py-2.5 text-right text-blue-300">
                  {(row.grid_energy_kwh ?? 0).toFixed(3)}
                </td>
                <td className="px-4 py-2.5 text-right text-yellow-300">
                  {(row.solar_energy_used_kwh ?? 0).toFixed(3)}
                </td>
                <td className="px-4 py-2.5 text-right text-emerald-300">
                  {(row.interval_cost_pkr ?? 0).toFixed(2)}
                </td>
                <td className="px-4 py-2.5 text-right text-slate-300">
                  {row.estimated_indoor_temp_c?.toFixed(1) ?? "—"}
                </td>
                <td className="px-4 py-2.5">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${comfortBadgeClass(row.comfort_status)}`}>
                    {(row.comfort_status ?? "—").replace("_", " ")}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-slate-400 text-xs max-w-[180px] truncate" title={row.explanation}>
                  {row.reason_code}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
