from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class ScenarioProfile(BaseModel):
    scenario_id: str
    name: str
    timezone: str = "Asia/Karachi"
    building_type: str
    area_m2: float
    room_count: int
    max_occupancy: int
    insulation_level: Literal["low", "medium", "high"]
    sun_exposure: Literal["low", "medium", "high"]
    comfort_min_c: float = 22.0
    comfort_max_c: float = 26.0
    vulnerable_occupants: bool = False
    budget_pkr_per_day: float
    maximum_grid_demand_kw: float


class Appliance(BaseModel):
    scenario_id: str
    appliance_id: str
    zone_id: str = "main"
    appliance_type: Literal["ac", "fan", "evaporative_cooler", "other"]
    quantity: int
    rated_power_kw: float
    cooling_capacity_kw: float
    efficiency_label: str = "3-star"
    min_runtime_minutes: int = 15
    min_setpoint_c: float = 16.0
    max_setpoint_c: float = 30.0


class EnergyAssets(BaseModel):
    scenario_id: str
    solar_capacity_kw: float = 0.0
    solar_conversion_efficiency: float = 0.18
    battery_capacity_kwh: float = 0.0
    initial_soc_kwh: float = 0.0
    minimum_reserve_kwh: float = 0.0
    max_charge_kw: float = 0.0
    max_discharge_kw: float = 0.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95


class IntervalInput(BaseModel):
    scenario_id: str
    timestamp_local: datetime
    temperature_c: float
    relative_humidity_pct: float
    heat_index_c: float
    solar_irradiance_w_m2: float = 0.0
    occupancy_count: int = 0
    grid_available: bool = True
    tariff_type: str = "off_peak"
    tariff_pkr_per_kwh: float
    grid_carbon_kgco2_per_kwh: float
    non_cooling_load_kw: float = 0.0


class BaselineInterval(BaseModel):
    scenario_id: str
    timestamp_local: datetime
    baseline_ac_units_on: int
    baseline_ac_setpoint_c: float
    baseline_fan_units_on: int
    baseline_other_cooling_kw: float = 0.0


class OptimizationRequest(BaseModel):
    scenario_id: str
    run_id: Optional[str] = None
    algorithm_version: str = "coolshift-lp-v1"
    start_timestamp: Optional[datetime] = None
    days: int = Field(default=7, ge=1, le=30)
    priority_weights: dict = Field(default={
        "cost": 0.35,
        "emissions": 0.30,
        "comfort": 0.25,
        "peak_demand": 0.10
    })
    comfort_override: Optional[dict] = None


class IntervalOutput(BaseModel):
    scenario_id: str
    run_id: str
    timestamp_local: datetime
    recommended_ac_units_on: int
    recommended_ac_setpoint_c: Optional[float]
    recommended_fan_units_on: int
    grid_energy_kwh: float
    solar_energy_used_kwh: float
    battery_charge_kwh: float
    battery_discharge_kwh: float
    battery_soc_kwh: float
    cooling_energy_kwh: float
    estimated_indoor_temp_c: float
    comfort_status: Literal["within_range", "warning", "unsafe", "infeasible"]
    interval_cost_pkr: float
    interval_emissions_kgco2e: float
    reason_code: str
    explanation: str
    constraint_violation_count: int


class ScenarioSummary(BaseModel):
    scenario_id: str
    run_id: str
    period_start: datetime
    period_end: datetime
    baseline_total_energy_kwh: float
    optimized_total_energy_kwh: float
    baseline_total_cost_pkr: float
    optimized_total_cost_pkr: float
    baseline_peak_demand_kw: float
    optimized_peak_demand_kw: float
    baseline_emissions_kgco2e: float
    optimized_emissions_kgco2e: float
    energy_saving_kwh: float
    cost_saving_pkr: float
    cost_saving_pct: float
    emission_reduction_kgco2e: float
    emission_reduction_pct: float
    solar_utilization_pct: float
    comfort_compliance_pct: float
    unsafe_heat_intervals: int
    constraint_violations: int
    algorithm_version: str
    run_timestamp: datetime


class ValidationResult(BaseModel):
    is_valid: bool
    total_records: int
    valid_records: int
    errors: List[dict]
    warnings: List[dict]
    missing_fields: List[str]
