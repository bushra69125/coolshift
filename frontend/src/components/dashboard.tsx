"use client";

import { useState } from "react";
import { MetricCards } from "./metric-cards";
import { ScheduleChart } from "./schedule-chart";
import { EnergySourceChart } from "./energy-source-chart";
import { ComfortChart } from "./comfort-chart";
import { ScheduleTable } from "./schedule-table";
import { ExportPanel } from "./export-panel";
import { ArrowLeft, Download, RefreshCw } from "lucide-react";
import { downloadCSV, downloadExcel } from "@/lib/api";

interface Props {
  result: any;
  uploadedFile: File;
  onReset: () => void;
}

const TABS = ["Overview", "Schedule", "Energy", "Comfort", "Export"] as const;
type Tab = typeof TABS[number];

export function Dashboard({ result, uploadedFile, onReset }: Props) {
  const [tab, setTab] = useState<Tab>("Overview");
  const [exporting, setExporting] = useState(false);

  const schedule = result.schedule || [];
  const summary = result.summary || {};
  const baseline = result.baseline_summary || {};
  const cMin: number = result.comfort_min ?? 22;
  const cMax: number = result.comfort_max ?? 26;

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      await downloadCSV(uploadedFile, result.scenario_id, 7);
    } finally {
      setExporting(false);
    }
  };

  const handleExportExcel = async () => {
    setExporting(true);
    try {
      await downloadExcel(uploadedFile, 7);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onReset}
            className="p-2 rounded-lg border border-white/10 hover:bg-white/5 text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h2 className="text-xl font-bold text-white">
              Scenario {result.scenario_id}
            </h2>
            <p className="text-slate-400 text-sm">
              {result.intervals_optimized} intervals optimized · Run {result.run_id?.slice(0, 8)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-sm text-slate-300 hover:text-white transition-colors disabled:opacity-40"
          >
            <Download className="w-4 h-4" />
            CSV
          </button>
          <button
            onClick={handleExportExcel}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-sm text-white font-medium transition-colors disabled:opacity-40"
          >
            <Download className="w-4 h-4" />
            Excel
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/5 border border-white/10 rounded-xl p-1">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
              tab === t
                ? "bg-white/10 text-white"
                : "text-slate-400 hover:text-white"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === "Overview" && (
        <div className="space-y-6">
          {result.ai_summary && (
            <div className="rounded-xl border border-emerald-800/40 bg-emerald-950/20 px-5 py-4">
              <p className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-1">
                AI Analysis · Groq Llama 3.1
              </p>
              <p className="text-sm text-slate-300 leading-relaxed">{result.ai_summary}</p>
            </div>
          )}
          <MetricCards summary={summary} baseline={baseline} />
          <div className="grid lg:grid-cols-2 gap-6">
            <ScheduleChart data={schedule.slice(0, 96)} />
            <EnergySourceChart data={schedule.slice(0, 96)} />
          </div>
          <ComfortChart data={schedule.slice(0, 96)} comfortMin={cMin} comfortMax={cMax} />
        </div>
      )}

      {tab === "Schedule" && (
        <div className="space-y-6">
          <ScheduleChart data={schedule} fullWidth />
          <ScheduleTable data={schedule.slice(0, 200)} />
        </div>
      )}

      {tab === "Energy" && (
        <div className="space-y-6">
          <EnergySourceChart data={schedule} fullWidth />
          <BatteryChart data={schedule} />
        </div>
      )}

      {tab === "Comfort" && (
        <ComfortChart data={schedule} fullWidth comfortMin={cMin} comfortMax={cMax} />
      )}

      {tab === "Export" && (
        <ExportPanel
          result={result}
          uploadedFile={uploadedFile}
          onExportCSV={handleExportCSV}
          onExportExcel={handleExportExcel}
          exporting={exporting}
        />
      )}
    </div>
  );
}

function BatteryChart({ data }: { data: any[] }) {
  const hasData = data.some((d) => d.battery_soc_kwh > 0);
  if (!hasData) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6 text-center text-slate-500">
        No battery data in this scenario (PUB-A has no solar/battery).
      </div>
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } = require("recharts");

  const formatted = data.map((d, i) => ({
    t: i,
    soc: d.battery_soc_kwh,
    charge: d.battery_charge_kwh,
    discharge: d.battery_discharge_kwh,
  }));

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6">
      <h3 className="text-white font-semibold mb-4">Battery State of Charge</h3>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={formatted}>
          <XAxis dataKey="t" tick={false} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8 }}
            labelFormatter={(v: unknown) => `Interval ${v}`}
          />
          <Area type="monotone" dataKey="soc" stroke="#3b82f6" fill="#3b82f620" name="SOC (kWh)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
