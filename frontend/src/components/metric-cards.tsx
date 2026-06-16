"use client";

import { TrendingDown, Zap, Leaf, Thermometer, AlertTriangle, CheckCircle2 } from "lucide-react";
import { fmtPKR, fmtPct, fmt } from "@/lib/utils";

interface Props {
  summary: any;
  baseline: any;
}

export function MetricCards({ summary, baseline }: Props) {
  const saving = summary.cost_saving_pct ?? 0;
  const energySaving = summary.energy_saving_kwh ?? 0;
  const emissionReduction = summary.emission_reduction_pct ?? 0;
  const comfortPct = summary.comfort_compliance_pct ?? 0;
  const violations = summary.constraint_violations ?? 0;
  const unsafeIntervals = summary.unsafe_heat_intervals ?? 0;

  const cards = [
    {
      label: "Cost Saving",
      value: fmtPKR(summary.cost_saving_pkr),
      sub: `${saving.toFixed(1)}% vs baseline`,
      icon: TrendingDown,
      color: "from-emerald-500/20 to-emerald-600/5",
      border: "border-emerald-500/20",
      iconColor: "text-emerald-400",
      positive: saving > 0,
    },
    {
      label: "Energy Saved",
      value: `${fmt(energySaving, 2)} kWh`,
      sub: `Baseline: ${fmt(baseline.total_energy_kwh, 2)} kWh`,
      icon: Zap,
      color: "from-blue-500/20 to-blue-600/5",
      border: "border-blue-500/20",
      iconColor: "text-blue-400",
      positive: energySaving > 0,
    },
    {
      label: "CO₂ Reduced",
      value: `${fmt(summary.emission_reduction_kgco2e, 2)} kg`,
      sub: `${emissionReduction.toFixed(1)}% reduction`,
      icon: Leaf,
      color: "from-teal-500/20 to-teal-600/5",
      border: "border-teal-500/20",
      iconColor: "text-teal-400",
      positive: emissionReduction > 0,
    },
    {
      label: "Comfort Compliance",
      value: fmtPct(comfortPct),
      sub: `${unsafeIntervals} unsafe intervals`,
      icon: Thermometer,
      color: comfortPct >= 90
        ? "from-emerald-500/20 to-emerald-600/5"
        : "from-orange-500/20 to-orange-600/5",
      border: comfortPct >= 90 ? "border-emerald-500/20" : "border-orange-500/20",
      iconColor: comfortPct >= 90 ? "text-emerald-400" : "text-orange-400",
      positive: comfortPct >= 90,
    },
    {
      label: "Solar Utilization",
      value: fmtPct(summary.solar_utilization_pct),
      sub: "of available solar used",
      icon: Zap,
      color: "from-yellow-500/20 to-yellow-600/5",
      border: "border-yellow-500/20",
      iconColor: "text-yellow-400",
      positive: true,
    },
    {
      label: "Constraint Status",
      value: violations === 0 ? "All Pass" : `${violations} Violations`,
      sub: violations === 0 ? "A1–A12 all satisfied" : "Review constraint log",
      icon: violations === 0 ? CheckCircle2 : AlertTriangle,
      color: violations === 0
        ? "from-emerald-500/20 to-emerald-600/5"
        : "from-red-500/20 to-red-600/5",
      border: violations === 0 ? "border-emerald-500/20" : "border-red-500/20",
      iconColor: violations === 0 ? "text-emerald-400" : "text-red-400",
      positive: violations === 0,
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`rounded-xl border ${card.border} bg-gradient-to-br ${card.color} p-5 backdrop-blur-sm`}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-slate-400 text-sm font-medium">{card.label}</span>
            <card.icon className={`w-4 h-4 ${card.iconColor}`} />
          </div>
          <p className="text-white text-2xl font-bold leading-none mb-1">{card.value}</p>
          <p className="text-slate-400 text-xs">{card.sub}</p>
        </div>
      ))}
    </div>
  );
}
