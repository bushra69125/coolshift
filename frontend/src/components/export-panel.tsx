"use client";

import { Download, FileSpreadsheet, FileText, Globe, CheckCircle2 } from "lucide-react";
import { fetchCustomScenario } from "@/lib/api";
import { useState } from "react";

interface Props {
  result: any;
  uploadedFile: File;
  onExportCSV: () => void;
  onExportExcel: () => void;
  exporting: boolean;
}

export function ExportPanel({ result, uploadedFile, onExportCSV, onExportExcel, exporting }: Props) {
  const [customScenario, setCustomScenario] = useState<any>(null);
  const [fetchingWeather, setFetchingWeather] = useState(false);
  const [weatherError, setWeatherError] = useState<string | null>(null);

  const summary = result.summary ?? {};

  const handleFetchCustom = async () => {
    setFetchingWeather(true);
    setWeatherError(null);
    try {
      const data = await fetchCustomScenario({
        scenario_id: "CUSTOM-KHI-2024",
        lat: 24.8607,
        lon: 67.0011,
        start_date: "2024-06-01",
        end_date: "2024-06-07",
        has_outage: true,
      });
      setCustomScenario(data);
    } catch (e: any) {
      setWeatherError(e.message);
    } finally {
      setFetchingWeather(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Submission Checklist */}
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6">
        <h3 className="text-white font-semibold mb-4">Competition Submission Checklist</h3>
        <div className="space-y-3">
          {[
            { label: "All public interval records processable", done: true },
            { label: `${result.intervals_optimized} rows this run · Export All Scenarios = 2,016+ total rows`, done: result.intervals_optimized >= 672 },
            { label: "Baseline and optimized outputs available", done: !!summary.baseline_total_cost_pkr },
            { label: "Comfort compliance calculated", done: !!summary.comfort_compliance_pct },
            { label: `Zero hard constraint violations`, done: (summary.constraint_violations ?? 0) === 0 },
            { label: "Custom 7-day scenario (fetch below)", done: !!customScenario },
            { label: "CSV export ready", done: true },
            { label: "Excel export ready", done: true },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-3">
              <CheckCircle2 className={`w-4 h-4 shrink-0 ${item.done ? "text-emerald-400" : "text-slate-600"}`} />
              <span className={`text-sm ${item.done ? "text-slate-300" : "text-slate-500"}`}>
                {item.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Export Buttons */}
      <div className="grid sm:grid-cols-2 gap-4">
        <button
          onClick={onExportCSV}
          disabled={exporting}
          className="flex items-center gap-3 p-5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-colors text-left disabled:opacity-40"
        >
          <FileText className="w-8 h-8 text-blue-400 shrink-0" />
          <div>
            <p className="text-white font-semibold">Export Interval CSV</p>
            <p className="text-slate-400 text-sm">Required output format for submission</p>
          </div>
          <Download className="w-4 h-4 text-slate-400 ml-auto" />
        </button>

        <button
          onClick={onExportExcel}
          disabled={exporting}
          className="flex items-center gap-3 p-5 rounded-xl border border-emerald-500/30 bg-emerald-500/5 hover:bg-emerald-500/10 transition-colors text-left disabled:opacity-40"
        >
          <FileSpreadsheet className="w-8 h-8 text-emerald-400 shrink-0" />
          <div>
            <p className="text-white font-semibold">Export All Scenarios Excel</p>
            <p className="text-slate-400 text-sm">Multi-sheet with summary metrics</p>
          </div>
          <Download className="w-4 h-4 text-slate-400 ml-auto" />
        </button>
      </div>

      {/* Custom Scenario */}
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-white font-semibold">Custom Scenario (Karachi, Pakistan)</h3>
            <p className="text-slate-400 text-sm mt-1">
              Live weather via Open-Meteo + Pakistan NEPRA tariff + synthetic occupancy
            </p>
          </div>
          <button
            onClick={handleFetchCustom}
            disabled={fetchingWeather || !!customScenario}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm text-white font-medium transition-colors disabled:opacity-40"
          >
            <Globe className="w-4 h-4" />
            {fetchingWeather ? "Fetching..." : customScenario ? "Generated ✓" : "Generate Custom Scenario"}
          </button>
        </div>

        {weatherError && (
          <p className="text-red-400 text-sm">{weatherError}</p>
        )}

        {customScenario && (
          <div className="space-y-4">
            <div className="grid sm:grid-cols-3 gap-4">
              <div className="rounded-lg bg-white/5 border border-white/10 p-3">
                <p className="text-slate-400 text-xs mb-1">Records</p>
                <p className="text-white font-bold">{customScenario.records?.toLocaleString()}</p>
              </div>
              <div className="rounded-lg bg-white/5 border border-white/10 p-3">
                <p className="text-slate-400 text-xs mb-1">Date Range</p>
                <p className="text-white font-bold text-sm">{customScenario.date_range}</p>
              </div>
              <div className="rounded-lg bg-white/5 border border-white/10 p-3">
                <p className="text-slate-400 text-xs mb-1">Source</p>
                <p className="text-white font-bold text-sm">Open-Meteo ERA5</p>
              </div>
            </div>

            <div className="rounded-lg bg-blue-500/10 border border-blue-500/20 p-4">
              <p className="text-blue-300 text-sm font-semibold mb-2">Data Provenance</p>
              <ul className="space-y-1 text-slate-300 text-xs">
                {Object.entries(customScenario.provenance ?? {}).map(([k, v]) => (
                  <li key={k}><span className="text-slate-500">{k.replace(/_/g, " ")}:</span> {String(v)}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* Summary Metrics Table */}
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6">
        <h3 className="text-white font-semibold mb-4">Run Summary</h3>
        <div className="grid sm:grid-cols-2 gap-3 text-sm">
          {[
            ["Run ID", result.run_id?.slice(0, 16) + "..."],
            ["Algorithm", summary.algorithm_version],
            ["Baseline Energy", `${summary.baseline_total_energy_kwh?.toFixed(2)} kWh`],
            ["Optimized Energy", `${summary.optimized_total_energy_kwh?.toFixed(2)} kWh`],
            ["Baseline Cost", `PKR ${summary.baseline_total_cost_pkr?.toFixed(2)}`],
            ["Optimized Cost", `PKR ${summary.optimized_total_cost_pkr?.toFixed(2)}`],
            ["Cost Saving", `PKR ${summary.cost_saving_pkr?.toFixed(2)} (${summary.cost_saving_pct?.toFixed(1)}%)`],
            ["Emission Reduction", `${summary.emission_reduction_kgco2e?.toFixed(2)} kg (${summary.emission_reduction_pct?.toFixed(1)}%)`],
            ["Comfort Compliance", `${summary.comfort_compliance_pct?.toFixed(1)}%`],
            ["Constraint Violations", `${summary.constraint_violations ?? 0}`],
          ].map(([label, value]) => (
            <div key={label} className="flex justify-between py-2 border-b border-white/5">
              <span className="text-slate-400">{label}</span>
              <span className="text-white font-medium">{value ?? "—"}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
