import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd

from ..engines.data_loader import load_excel, parse_workbook, validate_intervals, fill_missing_heat_index
from ..engines.baseline import compute_baseline, summarize_baseline

logger = logging.getLogger("coolshift.scenarios")
router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("/upload")
async def upload_scenario(file: UploadFile = File(...)):
    """Upload organizer Excel workbook and validate all sheets."""
    logger.info(f"[UPLOAD] Received file: {file.filename} ({file.content_type})")

    if not file.filename.endswith((".xlsx", ".xls", ".csv")):
        logger.warning(f"[UPLOAD] ❌ Rejected unsupported file type: {file.filename}")
        raise HTTPException(400, "Only .xlsx, .xls and .csv files are accepted")

    contents = await file.read()
    logger.info(f"[UPLOAD] File size: {len(contents)/1024:.1f} KB")

    try:
        sheets = load_excel(contents)
        parsed = parse_workbook(sheets)
        logger.info(f"[UPLOAD] Sheets found: {list(sheets.keys())}")
    except Exception as e:
        logger.error(f"[UPLOAD] ❌ Parse error: {e}")
        raise HTTPException(400, f"Cannot parse workbook: {e}")

    intervals = parsed.get("intervals")
    if intervals is None or len(intervals) == 0:
        logger.error("[UPLOAD] ❌ No interval_inputs sheet found")
        raise HTTPException(400, "No interval_inputs sheet found in workbook")

    intervals = fill_missing_heat_index(intervals)
    validation = validate_intervals(intervals)

    scenario_ids = []
    if "scenario_id" in intervals.columns:
        scenario_ids = intervals["scenario_id"].unique().tolist()

    status = "ok" if validation["is_valid"] else "warnings"
    logger.info(f"[UPLOAD] ✅ Validation {status} — {len(intervals)} records, scenarios: {scenario_ids}")
    if validation["errors"]:
        logger.warning(f"[UPLOAD] Errors: {validation['errors']}")
    if validation["warnings"]:
        logger.info(f"[UPLOAD] Warnings: {validation['warnings']}")

    return JSONResponse({
        "status": status,
        "filename": file.filename,
        "sheets_found": list(sheets.keys()),
        "scenario_ids": [str(s) for s in scenario_ids],
        "total_interval_records": len(intervals),
        "validation": validation,
    })


@router.post("/validate")
async def validate_file(file: UploadFile = File(...)):
    logger.info(f"[VALIDATE] File: {file.filename}")
    contents = await file.read()
    sheets = load_excel(contents)
    parsed = parse_workbook(sheets)
    intervals = parsed.get("intervals")
    if intervals is None:
        logger.error("[VALIDATE] ❌ No interval data found")
        raise HTTPException(400, "No interval data found")
    intervals = fill_missing_heat_index(intervals)
    result = validate_intervals(intervals)
    logger.info(f"[VALIDATE] ✅ Result: valid={result['is_valid']}, records={result['total_records']}")
    return result
