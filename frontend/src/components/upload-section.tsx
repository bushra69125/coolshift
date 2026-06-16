"use client";

import { useState, useCallback } from "react";
import { Upload, FileSpreadsheet, AlertCircle, CheckCircle2, Loader2, Zap, Globe } from "lucide-react";
import { runOptimization, uploadAndValidate } from "@/lib/api";

interface Props {
  onResult: (result: any, file: File) => void;
}

export function UploadSection({ onResult }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [scenarioId, setScenarioId] = useState("PUB-A");
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback(async (f: File) => {
    setFile(f);
    setError(null);
    setValidation(null);
    setValidating(true);
    try {
      const v = await uploadAndValidate(f);
      setValidation(v);
      if (v.scenario_ids?.length > 0) setScenarioId(v.scenario_ids[0]);
    } catch (e: any) {
      setError(`Validation failed: ${e.message}`);
    } finally {
      setValidating(false);
    }
  }, []);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleRun = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const result = await runOptimization(file, scenarioId, days);
      onResult(result, file);
    } catch (e: any) {
      setError(`Optimization failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto pt-12">
      {/* Hero */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-2 rounded-full text-sm mb-6">
          <Globe className="w-4 h-4" />
          Rapid Forge Buildathon — SDG 7 & 13
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4 leading-tight">
          Smarter Cooling.{" "}
          <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
            Lower Bills.
          </span>{" "}
          Cleaner Air.
        </h1>
        <p className="text-slate-400 text-lg max-w-xl mx-auto">
          Upload your building scenario and get an AI-optimized 24-hour cooling
          schedule that reduces cost, peak demand and carbon emissions.
        </p>
      </div>

      {/* Upload Card */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-8">
        {/* Drop Zone */}
        <div
          className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer ${
            isDragging
              ? "border-emerald-400 bg-emerald-400/5"
              : "border-white/15 hover:border-white/30 hover:bg-white/[0.02]"
          }`}
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onClick={() => document.getElementById("file-input")?.click()}
        >
          <input
            id="file-input"
            type="file"
            accept=".xlsx,.xls,.csv"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />
          {validating ? (
            <Loader2 className="w-10 h-10 mx-auto text-blue-400 animate-spin mb-3" />
          ) : file ? (
            <FileSpreadsheet className="w-10 h-10 mx-auto text-emerald-400 mb-3" />
          ) : (
            <Upload className="w-10 h-10 mx-auto text-slate-500 mb-3" />
          )}
          <p className="text-white font-medium mb-1">
            {validating ? "Validating..." : file ? file.name : "Drop your workbook here"}
          </p>
          <p className="text-slate-500 text-sm">
            {file ? "Click to change file" : "04_CoolShift_Public_Dataset_and_Templates.xlsx"}
          </p>
        </div>

        {/* Validation Result */}
        {validation && (
          <div className={`mt-4 rounded-xl p-4 flex items-start gap-3 ${
            validation.status === "ok"
              ? "bg-emerald-500/10 border border-emerald-500/20"
              : "bg-yellow-500/10 border border-yellow-500/20"
          }`}>
            {validation.status === "ok" ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-yellow-400 mt-0.5 shrink-0" />
            )}
            <div>
              <p className={`font-medium text-sm ${validation.status === "ok" ? "text-emerald-300" : "text-yellow-300"}`}>
                {validation.status === "ok" ? "Dataset valid" : "Warnings detected"}
              </p>
              <p className="text-slate-400 text-sm">
                {validation.total_interval_records?.toLocaleString()} records · Scenarios:{" "}
                {validation.scenario_ids?.join(", ")}
              </p>
              {validation.validation?.warnings?.length > 0 && (
                <ul className="mt-2 text-xs text-yellow-400 space-y-0.5">
                  {validation.validation.warnings.slice(0, 3).map((w: any, i: number) => (
                    <li key={i}>⚠ {w.message}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {/* Config */}
        <div className="mt-6 grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-2">Scenario</label>
            <select
              value={scenarioId}
              onChange={(e) => setScenarioId(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500"
            >
              {(validation?.scenario_ids || ["PUB-A", "PUB-B", "PUB-C"]).map((id: string) => (
                <option key={id} value={id} className="bg-slate-900">{id}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-2">Days to optimize</label>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-emerald-500"
            >
              {[1, 3, 7, 14, 30].map((d) => (
                <option key={d} value={d} className="bg-slate-900">{d} day{d > 1 ? "s" : ""}</option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-xl p-4 bg-red-500/10 border border-red-500/20 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <p className="text-red-300 text-sm">{error}</p>
          </div>
        )}

        <button
          onClick={handleRun}
          disabled={!file || loading}
          className="mt-6 w-full py-3.5 rounded-xl bg-gradient-to-r from-emerald-500 to-blue-500 text-white font-semibold text-base hover:from-emerald-400 hover:to-blue-400 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <><Loader2 className="w-5 h-5 animate-spin" /> Optimizing with LP solver…</>
          ) : (
            <><Zap className="w-5 h-5" /> Run Optimization</>
          )}
        </button>

        <p className="text-center text-xs text-slate-500 mt-4">
          Uses PuLP linear programming · All 9 hard constraints enforced · 96 intervals per day
        </p>
      </div>
    </div>
  );
}
