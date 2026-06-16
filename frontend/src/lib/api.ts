const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

console.log("[CoolShift] API base URL:", API_BASE);

export async function uploadAndValidate(file: File) {
  console.log("[Upload] Starting validation for:", file.name, `(${(file.size / 1024).toFixed(1)} KB)`);
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await fetch(`${API_BASE}/scenarios/upload`, { method: "POST", body: form });
    if (!res.ok) {
      const text = await res.text();
      console.error("[Upload] Validation failed:", res.status, text);
      throw new Error(text);
    }
    const data = await res.json();
    console.log("[Upload] ✅ Validation success:", {
      status: data.status,
      scenarios: data.scenario_ids,
      totalRecords: data.total_interval_records,
      errors: data.validation?.errors?.length ?? 0,
      warnings: data.validation?.warnings?.length ?? 0,
    });
    return data;
  } catch (err) {
    console.error("[Upload] ❌ Error:", err);
    throw err;
  }
}

export async function runOptimization(
  file: File,
  scenarioId: string,
  days = 7,
  weights = { cost: 0.35, emissions: 0.30, comfort: 0.25, peak_demand: 0.10 }
) {
  console.log("[Optimizer] Starting LP optimization:", { scenarioId, days, weights });
  const form = new FormData();
  form.append("file", file);
  const params = new URLSearchParams({
    scenario_id: scenarioId,
    days: String(days),
    weight_cost: String(weights.cost),
    weight_emissions: String(weights.emissions),
    weight_comfort: String(weights.comfort),
    weight_peak: String(weights.peak_demand),
  });
  const t0 = Date.now();
  try {
    const res = await fetch(`${API_BASE}/optimize/run?${params}`, { method: "POST", body: form });
    if (!res.ok) {
      const text = await res.text();
      console.error("[Optimizer] ❌ Failed:", res.status, text);
      throw new Error(text);
    }
    const data = await res.json();
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    console.log(`[Optimizer] ✅ Done in ${elapsed}s:`, {
      runId: data.run_id,
      intervalsOptimized: data.intervals_optimized,
      costSavingPct: data.summary?.cost_saving_pct,
      emissionReductionPct: data.summary?.emission_reduction_pct,
      comfortCompliance: data.summary?.comfort_compliance_pct,
      constraintViolations: data.summary?.constraint_violations,
    });
    return data;
  } catch (err) {
    console.error("[Optimizer] ❌ Error:", err);
    throw err;
  }
}

export async function optimizeAllScenarios(file: File, days = 7) {
  console.log("[Optimizer] Running all scenarios, days:", days);
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await fetch(`${API_BASE}/optimize/all-scenarios?days=${days}`, { method: "POST", body: form });
    if (!res.ok) {
      const text = await res.text();
      console.error("[Optimizer] ❌ All-scenarios failed:", text);
      throw new Error(text);
    }
    const data = await res.json();
    console.log("[Optimizer] ✅ All scenarios done:", data.scenarios_processed);
    return data;
  } catch (err) {
    console.error("[Optimizer] ❌ Error:", err);
    throw err;
  }
}

export async function fetchCustomScenario(params: {
  scenario_id?: string;
  lat?: number;
  lon?: number;
  start_date?: string;
  end_date?: string;
  has_outage?: boolean;
}) {
  console.log("[Weather] Fetching custom scenario from Open-Meteo:", params);
  const q = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]));
  try {
    const res = await fetch(`${API_BASE}/weather/custom-scenario?${q}`);
    if (!res.ok) {
      const text = await res.text();
      console.error("[Weather] ❌ Failed:", res.status, text);
      throw new Error(text);
    }
    const data = await res.json();
    console.log("[Weather] ✅ Custom scenario generated:", {
      scenarioId: data.scenario_id,
      records: data.records,
      dateRange: data.date_range,
      source: data.source,
    });
    return data;
  } catch (err) {
    console.error("[Weather] ❌ Error:", err);
    throw err;
  }
}

export async function downloadCSV(file: File, scenarioId: string, days = 7) {
  console.log("[Export] Downloading CSV for:", scenarioId, days, "days");
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await fetch(`${API_BASE}/export/csv/${scenarioId}?days=${days}`, {
      method: "POST", body: form,
    });
    if (!res.ok) {
      const text = await res.text();
      console.error("[Export] ❌ CSV export failed:", text);
      throw new Error(text);
    }
    const blob = await res.blob();
    console.log("[Export] ✅ CSV ready:", (blob.size / 1024).toFixed(1), "KB");
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `coolshift_${scenarioId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error("[Export] ❌ Error:", err);
    throw err;
  }
}

export async function downloadExcel(file: File, days = 7) {
  console.log("[Export] Downloading all-scenarios Excel, days:", days);
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await fetch(`${API_BASE}/export/excel-all?days=${days}`, {
      method: "POST", body: form,
    });
    if (!res.ok) {
      const text = await res.text();
      console.error("[Export] ❌ Excel export failed:", text);
      throw new Error(text);
    }
    const blob = await res.blob();
    console.log("[Export] ✅ Excel ready:", (blob.size / 1024).toFixed(1), "KB");
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "coolshift_all_scenarios.xlsx";
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error("[Export] ❌ Error:", err);
    throw err;
  }
}
