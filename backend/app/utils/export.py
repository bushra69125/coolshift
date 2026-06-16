"""Export optimization results to CSV / Excel."""

import io
import pandas as pd
from typing import Dict, Any


def export_interval_csv(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def export_summary_excel(
    interval_dfs: Dict[str, pd.DataFrame],
    summaries: Dict[str, Dict[str, Any]],
) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#1e3a5f", "font_color": "white"})
        pct_fmt = workbook.add_format({"num_format": "0.00%"})
        num_fmt = workbook.add_format({"num_format": "#,##0.00"})

        for scenario_id, df in interval_dfs.items():
            sheet_name = str(scenario_id)[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]
            for col_num, col_name in enumerate(df.columns):
                ws.write(0, col_num, col_name, header_fmt)
                ws.set_column(col_num, col_num, max(len(col_name) + 2, 14))

        # Summary sheet
        summary_rows = []
        for sid, s in summaries.items():
            summary_rows.append({
                "Scenario": sid,
                "Baseline Energy (kWh)": s.get("baseline_total_energy_kwh"),
                "Optimized Energy (kWh)": s.get("optimized_total_energy_kwh"),
                "Energy Saving (kWh)": s.get("energy_saving_kwh"),
                "Baseline Cost (PKR)": s.get("baseline_total_cost_pkr"),
                "Optimized Cost (PKR)": s.get("optimized_total_cost_pkr"),
                "Cost Saving (PKR)": s.get("cost_saving_pkr"),
                "Cost Saving (%)": s.get("cost_saving_pct"),
                "Baseline Emissions (kgCO2e)": s.get("baseline_emissions_kgco2e"),
                "Optimized Emissions (kgCO2e)": s.get("optimized_emissions_kgco2e"),
                "Emission Reduction (%)": s.get("emission_reduction_pct"),
                "Solar Utilization (%)": s.get("solar_utilization_pct"),
                "Comfort Compliance (%)": s.get("comfort_compliance_pct"),
                "Unsafe Heat Intervals": s.get("unsafe_heat_intervals"),
                "Constraint Violations": s.get("constraint_violations"),
                "Algorithm": s.get("algorithm_version"),
                "Run Timestamp": s.get("run_timestamp"),
            })

        if summary_rows:
            summary_df = pd.DataFrame(summary_rows)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            ws = writer.sheets["Summary"]
            for col_num, col_name in enumerate(summary_df.columns):
                ws.write(0, col_num, col_name, header_fmt)
                ws.set_column(col_num, col_num, max(len(col_name) + 2, 18))

    buf.seek(0)
    return buf.read()
