-- Useful views for the dashboard

-- Latest run per scenario
create or replace view latest_runs as
select distinct on (scenario_id)
  run_id, scenario_id, status,
  cost_saving_pct, energy_saving_kwh, emission_reduction_pct,
  comfort_compliance_pct, constraint_violations,
  days_optimized, completed_at, created_at
from optimization_runs
where status = 'completed'
order by scenario_id, created_at desc;

-- Daily summary aggregated from interval_outputs
create or replace view daily_summaries as
select
  run_id,
  scenario_id,
  date_trunc('day', timestamp_local)::date as day,
  sum(grid_energy_kwh) as grid_energy_kwh,
  sum(solar_energy_used_kwh) as solar_kwh,
  sum(battery_discharge_kwh) as battery_kwh,
  sum(cooling_energy_kwh) as cooling_kwh,
  sum(interval_cost_pkr) as cost_pkr,
  sum(interval_emissions_kgco2e) as emissions_kgco2e,
  max(grid_energy_kwh / 0.25) as peak_demand_kw,
  avg(estimated_indoor_temp_c) as avg_indoor_temp,
  count(*) filter (where comfort_status = 'within_range') as comfortable_intervals,
  count(*) filter (where comfort_status in ('unsafe','infeasible')) as unsafe_intervals,
  count(*) as total_intervals
from interval_outputs
group by run_id, scenario_id, date_trunc('day', timestamp_local)::date
order by run_id, day;
