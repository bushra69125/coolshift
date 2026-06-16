-- CoolShift Database Schema
-- Supabase / PostgreSQL

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ========================
-- SCENARIOS
-- ========================
create table if not exists scenarios (
  id uuid primary key default uuid_generate_v4(),
  scenario_id text not null unique,
  name text not null,
  scenario_type text not null default 'public',  -- 'public' | 'custom'
  building_type text,
  area_m2 numeric,
  room_count int,
  max_occupancy int,
  insulation_level text,
  sun_exposure text,
  comfort_min_c numeric default 22,
  comfort_max_c numeric default 26,
  vulnerable_occupants boolean default false,
  budget_pkr_per_day numeric,
  maximum_grid_demand_kw numeric,
  timezone text default 'Asia/Karachi',
  source_file text,
  provenance jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ========================
-- APPLIANCES
-- ========================
create table if not exists appliances (
  id uuid primary key default uuid_generate_v4(),
  scenario_id text references scenarios(scenario_id) on delete cascade,
  appliance_id text not null,
  zone_id text default 'main',
  appliance_type text not null,
  quantity int not null default 1,
  rated_power_kw numeric not null,
  cooling_capacity_kw numeric,
  efficiency_label text,
  min_runtime_minutes int default 15,
  min_setpoint_c numeric default 16,
  max_setpoint_c numeric default 30,
  created_at timestamptz default now()
);

-- ========================
-- ENERGY ASSETS (solar + battery)
-- ========================
create table if not exists energy_assets (
  id uuid primary key default uuid_generate_v4(),
  scenario_id text references scenarios(scenario_id) on delete cascade unique,
  solar_capacity_kw numeric default 0,
  solar_conversion_efficiency numeric default 0.18,
  battery_capacity_kwh numeric default 0,
  initial_soc_kwh numeric default 0,
  minimum_reserve_kwh numeric default 0,
  max_charge_kw numeric default 0,
  max_discharge_kw numeric default 0,
  charge_efficiency numeric default 0.95,
  discharge_efficiency numeric default 0.95,
  created_at timestamptz default now()
);

-- ========================
-- OPTIMIZATION RUNS
-- ========================
create table if not exists optimization_runs (
  id uuid primary key default uuid_generate_v4(),
  run_id text not null unique,
  scenario_id text references scenarios(scenario_id) on delete cascade,
  algorithm_version text not null default 'coolshift-lp-v1',
  status text not null default 'pending',  -- pending | running | completed | failed
  days_optimized int,
  weight_cost numeric default 0.35,
  weight_emissions numeric default 0.30,
  weight_comfort numeric default 0.25,
  weight_peak numeric default 0.10,
  -- Summary metrics
  baseline_total_energy_kwh numeric,
  optimized_total_energy_kwh numeric,
  baseline_total_cost_pkr numeric,
  optimized_total_cost_pkr numeric,
  baseline_peak_demand_kw numeric,
  optimized_peak_demand_kw numeric,
  baseline_emissions_kgco2e numeric,
  optimized_emissions_kgco2e numeric,
  energy_saving_kwh numeric,
  cost_saving_pkr numeric,
  cost_saving_pct numeric,
  emission_reduction_kgco2e numeric,
  emission_reduction_pct numeric,
  solar_utilization_pct numeric,
  comfort_compliance_pct numeric,
  unsafe_heat_intervals int,
  constraint_violations int,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz default now()
);

-- ========================
-- INTERVAL OUTPUTS
-- ========================
create table if not exists interval_outputs (
  id uuid primary key default uuid_generate_v4(),
  run_id text references optimization_runs(run_id) on delete cascade,
  scenario_id text,
  timestamp_local timestamptz not null,
  recommended_ac_units_on int,
  recommended_ac_setpoint_c numeric,
  recommended_fan_units_on int,
  grid_energy_kwh numeric,
  solar_energy_used_kwh numeric,
  battery_charge_kwh numeric,
  battery_discharge_kwh numeric,
  battery_soc_kwh numeric,
  cooling_energy_kwh numeric,
  estimated_indoor_temp_c numeric,
  comfort_status text,
  interval_cost_pkr numeric,
  interval_emissions_kgco2e numeric,
  reason_code text,
  explanation text,
  constraint_violation_count int default 0
);

-- ========================
-- INDEXES
-- ========================
create index if not exists idx_interval_outputs_run_id on interval_outputs(run_id);
create index if not exists idx_interval_outputs_timestamp on interval_outputs(timestamp_local);
create index if not exists idx_optimization_runs_scenario on optimization_runs(scenario_id);
create index if not exists idx_optimization_runs_status on optimization_runs(status);

-- ========================
-- RLS (Row Level Security) — enable when adding auth
-- ========================
alter table scenarios enable row level security;
alter table optimization_runs enable row level security;
alter table interval_outputs enable row level security;

-- Public read access (competition demo mode)
create policy "Public read scenarios" on scenarios for select using (true);
create policy "Public read runs" on optimization_runs for select using (true);
create policy "Public read outputs" on interval_outputs for select using (true);

-- Insert/update for authenticated users only
create policy "Auth insert scenarios" on scenarios for insert with check (true);
create policy "Auth insert runs" on optimization_runs for insert with check (true);
create policy "Auth insert outputs" on interval_outputs for insert with check (true);
