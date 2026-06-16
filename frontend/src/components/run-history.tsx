"use client";

import { useEffect, useState } from "react";
import { getRuns } from "@/lib/supabase";
import { Clock, TrendingDown, Zap, Leaf } from "lucide-react";

interface Run {
  run_id: string;
  scenario_id: string;
  cost_saving_pct: number;
  cost_saving_pkr: number;
  comfort_compliance_pct: number;
  emission_reduction_pct: number;
  days_optimized: number;
  created_at: string;
  algorithm_version: string;
}

export function RunHistory() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRuns()
      .then(({ data }) => {
        if (data) setRuns(data as Run[]);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6 animate-pulse">
        <div className="h-4 bg-white/10 rounded w-32 mb-4" />
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-10 bg-white/5 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (!runs.length) return null;

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6">
      <div className="flex items-center gap-2 mb-4">
        <Clock className="w-4 h-4 text-slate-400" />
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Recent Optimization Runs
        </h3>
      </div>

      <div className="space-y-2">
        {runs.slice(0, 8).map((run) => (
          <div
            key={run.run_id}
            className="flex items-center justify-between px-4 py-3 rounded-lg bg-white/[0.03] border border-white/5 hover:border-white/10 transition-colors"
          >
            <div className="flex items-center gap-3 min-w-0">
              <span className="px-2 py-0.5 rounded text-xs font-mono bg-emerald-900/40 text-emerald-400 border border-emerald-800/50">
                {run.scenario_id}
              </span>
              <span className="text-xs text-slate-500 font-mono hidden sm:block">
                {run.run_id.slice(0, 8)}
              </span>
              <span className="text-xs text-slate-500">
                {run.days_optimized ?? 7}d
              </span>
            </div>

            <div className="flex items-center gap-4 text-xs shrink-0">
              <span className="flex items-center gap-1 text-emerald-400">
                <TrendingDown className="w-3 h-3" />
                {run.cost_saving_pct?.toFixed(1) ?? "—"}% cost
              </span>
              <span className="flex items-center gap-1 text-blue-400 hidden md:flex">
                <Zap className="w-3 h-3" />
                {run.comfort_compliance_pct?.toFixed(0) ?? "—"}% comfort
              </span>
              <span className="flex items-center gap-1 text-purple-400 hidden lg:flex">
                <Leaf className="w-3 h-3" />
                {run.emission_reduction_pct?.toFixed(1) ?? "—"}% CO₂
              </span>
              <span className="text-slate-600 hidden sm:block">
                {run.created_at ? new Date(run.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}
              </span>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-slate-600 mt-3 text-center">
        Showing last {Math.min(runs.length, 8)} of {runs.length} runs · Stored in Supabase
      </p>
    </div>
  );
}
