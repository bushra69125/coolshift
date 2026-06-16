"""
Groq AI-powered natural language explanations for optimization decisions.
Falls back to rule-based explanations if Groq key is not set.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_groq_client = None


def _get_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=api_key)
        return _groq_client
    except Exception as e:
        logger.warning(f"Groq client init failed: {e}")
        return None


def generate_interval_explanation(
    reason_code: str,
    outdoor_temp: float,
    indoor_temp: float,
    occupancy: int,
    ac_units_on: int,
    total_ac_units: int,
    grid_energy: float,
    solar_energy: float,
    battery_discharge: float,
    cost: float,
    comfort_status: str,
    tariff_type: str,
    is_outage: bool,
) -> str:
    """Generate a concise, human-readable explanation for one 15-min interval."""
    client = _get_client()
    if client is None:
        return _fallback_explanation(reason_code, outdoor_temp, indoor_temp,
                                     ac_units_on, total_ac_units, grid_energy,
                                     solar_energy, battery_discharge, cost, comfort_status)

    prompt = f"""You are an energy optimization assistant. Explain this 15-minute cooling decision in 1-2 clear sentences for a building manager. Be specific about numbers.

Decision data:
- Outdoor temperature: {outdoor_temp:.1f}°C
- Estimated indoor temperature: {indoor_temp:.1f}°C
- Occupancy: {occupancy} people
- AC units running: {ac_units_on} of {total_ac_units}
- Grid energy used: {grid_energy:.3f} kWh
- Solar energy used: {solar_energy:.3f} kWh
- Battery discharge: {battery_discharge:.3f} kWh
- Interval electricity cost: PKR {cost:.2f}
- Comfort status: {comfort_status.replace('_', ' ')}
- Tariff period: {tariff_type}
- Grid outage: {is_outage}
- Primary reason code: {reason_code}

Write 1-2 sentences explaining WHY this decision was made and what benefit it provides. Be specific with numbers. Do not use markdown."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Groq explanation failed: {e}")
        return _fallback_explanation(reason_code, outdoor_temp, indoor_temp,
                                     ac_units_on, total_ac_units, grid_energy,
                                     solar_energy, battery_discharge, cost, comfort_status)


def generate_daily_summary(
    scenario_id: str,
    date: str,
    total_cost: float,
    baseline_cost: float,
    total_energy: float,
    peak_demand: float,
    emissions: float,
    comfort_pct: float,
    solar_pct: float,
) -> str:
    """Generate a natural-language daily summary for the dashboard."""
    client = _get_client()
    saving = baseline_cost - total_cost
    saving_pct = (saving / max(baseline_cost, 0.01)) * 100

    if client is None:
        return (f"On {date}, the optimizer saved PKR {saving:.0f} ({saving_pct:.1f}%) "
                f"vs baseline while maintaining {comfort_pct:.0f}% comfort compliance. "
                f"Peak demand: {peak_demand:.2f} kW. Solar used: {solar_pct:.0f}% of available.")

    prompt = f"""Summarize this day's cooling optimization results in 2-3 sentences for a building manager. Be encouraging and specific.

Scenario: {scenario_id} | Date: {date}
- Optimized cost: PKR {total_cost:.0f} (baseline was PKR {baseline_cost:.0f})
- Cost saving: PKR {saving:.0f} ({saving_pct:.1f}%)
- Grid energy: {total_energy:.2f} kWh
- Peak demand: {peak_demand:.2f} kW
- Carbon emissions: {emissions:.2f} kgCO2e
- Comfort compliance: {comfort_pct:.1f}%
- Solar utilization: {solar_pct:.1f}%

Write 2-3 sentences. Be specific with numbers. No markdown."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Groq summary failed: {e}")
        saving = baseline_cost - total_cost
        return (f"On {date}, CoolShift saved PKR {saving:.0f} ({saving_pct:.1f}%) "
                f"with {comfort_pct:.0f}% comfort compliance and {solar_pct:.0f}% solar utilization.")


def _fallback_explanation(reason_code, outdoor_temp, indoor_temp,
                           ac_units_on, total_ac, grid_e, solar_e, bat_e, cost, comfort) -> str:
    """Rule-based fallback when Groq is unavailable."""
    if reason_code == "OUTAGE":
        return f"Grid unavailable — operating on battery ({bat_e:.3f} kWh) to maintain essential cooling."
    if reason_code == "HEAT_RISK":
        return (f"Extreme outdoor heat ({outdoor_temp:.1f}°C) — running {ac_units_on}/{total_ac} AC units "
                f"to keep indoor temperature at {indoor_temp:.1f}°C.")
    if reason_code == "SOLAR_AVAILABLE":
        return (f"Using {solar_e:.3f} kWh solar energy to offset grid draw, "
                f"reducing electricity cost to PKR {cost:.2f} this interval.")
    if reason_code == "PEAK_TARIFF":
        return (f"Peak tariff period — reduced AC from {total_ac} to {ac_units_on} unit(s) "
                f"to cut cost, indoor temp remains {indoor_temp:.1f}°C.")
    if reason_code == "LOW_OCCUPANCY":
        return f"Space unoccupied — cooling reduced to save energy (indoor {indoor_temp:.1f}°C)."
    return (f"Optimized schedule: {ac_units_on}/{total_ac} AC units, "
            f"grid {grid_e:.3f} kWh, cost PKR {cost:.2f}, comfort {comfort.replace('_', ' ')}.")
