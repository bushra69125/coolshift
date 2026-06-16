"""Thin Supabase client wrapper. Errors are logged but never raised — DB is non-critical."""
import os
import logging

logger = logging.getLogger("coolshift.supabase")
_client = None


def get_supabase():
    global _client
    if _client is not None:
        return _client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("[SUPABASE] ✅ Client initialized")
        return _client
    except Exception as e:
        logger.warning(f"[SUPABASE] Init failed: {e}")
        return None


def save_optimization_run(
    run_id: str,
    scenario_id: str,
    summary: dict,
    days: int,
    weights: dict,
) -> None:
    """Insert optimization run summary into optimization_runs table."""
    client = get_supabase()
    if not client:
        logger.debug("[SUPABASE] Skipping save — not configured")
        return
    try:
        client.table("optimization_runs").upsert({
            "run_id": run_id,
            "scenario_id": scenario_id,
            "algorithm_version": summary.get("algorithm_version", "coolshift-lp-v1"),
            "status": "completed",
            "days_optimized": days,
            "weight_cost": weights.get("cost", 0.35),
            "weight_emissions": weights.get("emissions", 0.30),
            "weight_comfort": weights.get("comfort", 0.25),
            "weight_peak": weights.get("peak_demand", 0.10),
            "baseline_total_energy_kwh": summary.get("baseline_total_energy_kwh"),
            "optimized_total_energy_kwh": summary.get("optimized_total_energy_kwh"),
            "baseline_total_cost_pkr": summary.get("baseline_total_cost_pkr"),
            "optimized_total_cost_pkr": summary.get("optimized_total_cost_pkr"),
            "baseline_peak_demand_kw": summary.get("baseline_peak_demand_kw"),
            "optimized_peak_demand_kw": summary.get("optimized_peak_demand_kw"),
            "baseline_emissions_kgco2e": summary.get("baseline_emissions_kgco2e"),
            "optimized_emissions_kgco2e": summary.get("optimized_emissions_kgco2e"),
            "energy_saving_kwh": summary.get("energy_saving_kwh"),
            "cost_saving_pkr": summary.get("cost_saving_pkr"),
            "cost_saving_pct": summary.get("cost_saving_pct"),
            "emission_reduction_kgco2e": summary.get("emission_reduction_kgco2e"),
            "emission_reduction_pct": summary.get("emission_reduction_pct"),
            "solar_utilization_pct": summary.get("solar_utilization_pct"),
            "comfort_compliance_pct": summary.get("comfort_compliance_pct"),
            "unsafe_heat_intervals": summary.get("unsafe_heat_intervals"),
            "constraint_violations": summary.get("constraint_violations"),
        }).execute()
        logger.info(f"[SUPABASE] ✅ Run {run_id[:8]} saved to DB")
    except Exception as e:
        logger.warning(f"[SUPABASE] ⚠ Save failed (non-critical): {e}")
