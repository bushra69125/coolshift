"""
Simplified RC (Resistance-Capacitance) thermal model.
Estimates indoor temperature each 15-minute interval based on:
- Outdoor temperature / heat index
- Building insulation & area
- Sun exposure
- Occupancy (internal heat gain)
- Active cooling capacity & setpoint
- Thermal memory from previous interval
"""

from dataclasses import dataclass
from typing import Optional


# Fraction of outdoor-indoor temp difference that infiltrates per hour (thermal RC model)
# low insulation = RC ~8 hrs, medium ~20 hrs, high ~40 hrs
INSULATION_FACTOR = {"low": 0.12, "medium": 0.05, "high": 0.025}
SUN_EXPOSURE_GAIN = {"low": 0.0, "medium": 0.4, "high": 0.9}

DT_HOURS = 0.25          # 15-minute interval
OCCUPANT_HEAT_GAIN_KW = 0.08   # ~80W sensible heat per person
AREA_THERMAL_MASS = 0.05       # kWh/°C per m² — lightweight commercial construction


@dataclass
class BuildingThermalState:
    indoor_temp_c: float
    area_m2: float
    insulation_level: str
    sun_exposure: str
    comfort_min_c: float
    comfort_max_c: float
    vulnerable_occupants: bool


def estimate_indoor_temp(
    state: BuildingThermalState,
    outdoor_temp_c: float,
    heat_index_c: float,
    occupancy_count: int,
    cooling_capacity_active_kw: float,
    ac_setpoint_c: Optional[float],
    solar_irradiance_w_m2: float,
) -> float:
    """Return estimated indoor temperature after one 15-minute interval."""
    leak = INSULATION_FACTOR.get(str(state.insulation_level).lower(), 0.55)
    sun = SUN_EXPOSURE_GAIN.get(str(state.sun_exposure).lower(), 0.5)

    # Heat infiltration from outside
    delta_infiltration = leak * (heat_index_c - state.indoor_temp_c) * DT_HOURS

    # Solar heat gain through windows (simplified)
    solar_gain_kw = (solar_irradiance_w_m2 / 1000) * sun * (state.area_m2 * 0.05)
    delta_solar = (solar_gain_kw / (state.area_m2 * AREA_THERMAL_MASS)) * DT_HOURS

    # Internal heat from occupants
    occ_gain_kw = occupancy_count * OCCUPANT_HEAT_GAIN_KW
    delta_occ = (occ_gain_kw / (state.area_m2 * AREA_THERMAL_MASS)) * DT_HOURS

    # Cooling effect
    if cooling_capacity_active_kw > 0 and ac_setpoint_c is not None:
        # Cooling drives indoor temp toward setpoint
        temp_error = state.indoor_temp_c - ac_setpoint_c
        cooling_effect = min(
            cooling_capacity_active_kw * DT_HOURS / (state.area_m2 * AREA_THERMAL_MASS),
            max(0, temp_error)
        )
        delta_cooling = -cooling_effect
    else:
        delta_cooling = 0.0

    new_temp = state.indoor_temp_c + delta_infiltration + delta_solar + delta_occ + delta_cooling
    return round(new_temp, 2)


def classify_comfort(
    indoor_temp_c: float,
    comfort_min_c: float,
    comfort_max_c: float,
    occupied: bool,
    vulnerable: bool,
) -> str:
    if not occupied:
        return "within_range"
    safety_max = comfort_max_c + (0.5 if not vulnerable else 0.0)
    if indoor_temp_c <= comfort_max_c and indoor_temp_c >= comfort_min_c:
        return "within_range"
    elif indoor_temp_c <= safety_max:
        return "warning"
    elif indoor_temp_c <= safety_max + 2.0:
        return "unsafe"
    else:
        return "infeasible"


def comfort_penalty(indoor_temp_c: float, comfort_min_c: float, comfort_max_c: float) -> float:
    """Degree-minutes above/below comfort range — used as optimizer penalty."""
    if indoor_temp_c < comfort_min_c:
        return comfort_min_c - indoor_temp_c
    elif indoor_temp_c > comfort_max_c:
        return indoor_temp_c - comfort_max_c
    return 0.0
