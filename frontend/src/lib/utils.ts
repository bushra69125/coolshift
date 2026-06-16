import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function fmt(n: number | null | undefined, decimals = 1): string {
  if (n == null) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: decimals });
}

export function fmtPct(n: number | null | undefined): string {
  if (n == null) return "—";
  return `${n.toFixed(1)}%`;
}

export function fmtPKR(n: number | null | undefined): string {
  if (n == null) return "—";
  return `PKR ${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

export function comfortBadgeClass(status: string): string {
  switch (status) {
    case "within_range": return "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
    case "warning": return "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30";
    case "unsafe": return "bg-orange-500/20 text-orange-300 border border-orange-500/30";
    case "infeasible": return "bg-red-500/20 text-red-300 border border-red-500/30";
    default: return "bg-slate-700 text-slate-300";
  }
}
