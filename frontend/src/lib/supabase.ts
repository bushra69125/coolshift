import { createClient, SupabaseClient } from "@supabase/supabase-js";

let _client: SupabaseClient | null = null;

function getClient(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key || url === "your_supabase_url_here") return null;
  if (!_client) _client = createClient(url, key);
  return _client;
}

export const supabase = new Proxy({} as SupabaseClient, {
  get: (_, prop) => {
    const client = getClient();
    if (!client) return () => ({ data: null, error: new Error("Supabase not configured") });
    return (client as any)[prop];
  },
});

// ---- Runs ----
export async function saveRun(result: any) {
  const { data, error } = await supabase
    .from("optimization_runs")
    .upsert({
      run_id: result.run_id,
      scenario_id: result.scenario_id,
      algorithm_version: result.summary?.algorithm_version ?? "coolshift-lp-v1",
      status: "completed",
      days_optimized: Math.floor(result.intervals_optimized / 96),
      ...result.summary,
    });
  return { data, error };
}

export async function getRuns(scenarioId?: string) {
  let q = supabase
    .from("optimization_runs")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(50);
  if (scenarioId) q = q.eq("scenario_id", scenarioId);
  const { data, error } = await q;
  return { data, error };
}

// ---- Interval outputs ----
export async function saveIntervals(runId: string, rows: any[]) {
  const batch = rows.map((r) => ({ ...r, run_id: runId }));
  const CHUNK = 500;
  for (let i = 0; i < batch.length; i += CHUNK) {
    const { error } = await supabase
      .from("interval_outputs")
      .insert(batch.slice(i, i + CHUNK));
    if (error) return { error };
  }
  return { error: null };
}

export async function getIntervals(runId: string) {
  const { data, error } = await supabase
    .from("interval_outputs")
    .select("*")
    .eq("run_id", runId)
    .order("timestamp_local");
  return { data, error };
}
