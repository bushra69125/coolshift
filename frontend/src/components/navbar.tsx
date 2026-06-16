"use client";

import { Zap, Leaf, BarChart3, GitBranch } from "lucide-react";

export function Navbar() {
  return (
    <nav className="border-b border-white/10 bg-white/[0.02] backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-blue-500 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="font-bold text-white text-lg">CoolShift</span>
            <span className="text-slate-400 text-sm ml-2 hidden sm:inline">
              Intelligent Cooling Optimization
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-3 text-xs text-slate-400">
            <span className="flex items-center gap-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-2 py-1 rounded-full">
              <Leaf className="w-3 h-3" /> SDG 7
            </span>
            <span className="flex items-center gap-1 bg-blue-500/10 border border-blue-500/20 text-blue-400 px-2 py-1 rounded-full">
              <BarChart3 className="w-3 h-3" /> SDG 13
            </span>
          </div>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 hover:text-white transition-colors"
          >
            <GitBranch className="w-5 h-5" />
          </a>
        </div>
      </div>
    </nav>
  );
}
