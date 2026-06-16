# CoolShift — Intelligent Cooling Optimization Platform

> SDG 7: Affordable and Clean Energy · SDG 13: Climate Action
> Rapid Forge Buildathon — 48-Hour Product Development Challenge

## What it does

CoolShift converts raw environmental and energy data into an actionable 24-hour cooling schedule using Linear Programming optimization. It minimizes electricity cost, carbon emissions, peak demand and comfort violations while respecting all 9 mandatory hard constraints.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) · TypeScript · Tailwind CSS · shadcn/ui · Recharts |
| Optimization Engine | Python 3.11 · FastAPI · PuLP (LP solver) |
| Data Processing | Pandas · NumPy · openpyxl |
| Database | Supabase (PostgreSQL + RLS) |
| Weather API | Open-Meteo (free, no key) |
| Deployment | Vercel (frontend) · Railway (Python API) · Docker |

## Quick Start

### Backend (Python API)
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (Next.js)
```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local — set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

### Docker (full stack)
```bash
docker-compose up --build
```

Open [http://localhost:3000](http://localhost:3000)

## Competition Requirements Met

| Requirement | Status |
|---|---|
| Dynamic baseline calculation | ✅ RC thermal model |
| 24-hour optimization (96 intervals) | ✅ PuLP LP solver |
| Solar & battery modeling | ✅ SOC tracking, charge/discharge constraints |
| Outage handling | ✅ Grid energy = 0 enforced |
| All 9 hard constraints | ✅ A1–A12 acceptance tests |
| 2,688+ interval outputs | ✅ Per-scenario + combined export |
| Custom 7-day scenario | ✅ Open-Meteo API + provenance |
| CSV + Excel export | ✅ Multi-sheet with summaries |
| Explainability (reason codes) | ✅ 10 coded reasons + NL explanations |
| Unseen case handling | ✅ No hardcoded values |
| Dynamic recalculation | ✅ Any input change reruns optimizer |

## Architecture

```
Browser (Next.js)
    ↕ REST API
FastAPI (Python)
    ├── data_loader.py      ← validates Excel/CSV, fills heat index
    ├── baseline.py         ← RC thermal model, always-on baseline
    ├── optimizer.py        ← PuLP LP: minimize cost+emissions+discomfort
    ├── comfort.py          ← RC thermal estimator, comfort classification
    └── weather_api.py      ← Open-Meteo custom scenario generation
    ↕
Supabase (PostgreSQL)
    ├── scenarios
    ├── appliances
    ├── energy_assets
    ├── optimization_runs
    └── interval_outputs
```

## Optimization Objective

```
minimize:  w_cost × ΣGridCost
         + w_em × ΣEmissions
         + w_comfort × ΣComfortPenalty
         + w_peak × PeakDemand

subject to:
  GridEnergy[t] = 0   if grid_available[t] = False
  ACUnits[t] ≤ installed_quantity
  Setpoint[t] ∈ [min_setpoint, max_setpoint]
  BatterySoC[t] ∈ [reserve, capacity]
  Charge[t] ≤ max_charge_kw × Δt
  Discharge[t] ≤ max_discharge_kw × Δt
  EnergyBalance[t]: Grid + Solar + Battery_discharge = Load + Battery_charge
  OccupiedComfort: Prioritized via objective penalty
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `POST /scenarios/upload` | Upload & validate workbook |
| `POST /optimize/run` | Run LP optimization for one scenario |
| `POST /optimize/all-scenarios` | Process all 3 public scenarios |
| `GET /weather/custom-scenario` | Generate custom 7-day scenario |
| `POST /export/csv/{id}` | Export interval CSV |
| `POST /export/excel-all` | Export all scenarios as Excel |
| `GET /docs` | Interactive API documentation |

## External Data Sources

- **Weather**: Open-Meteo ERA5 reanalysis (CC BY 4.0) — https://open-meteo.com
- **Solar reference**: NASA POWER (CC BY 4.0) — https://power.larc.nasa.gov
- **Tariff**: Pakistan NEPRA domestic tariff schedule 2024
- **Carbon factor**: NTDC national grid average 0.40–0.52 kgCO2e/kWh

## Deployment

**Frontend → Vercel**
```
vercel deploy
```

**Backend → Railway**
```
railway up
```
Set `NEXT_PUBLIC_API_URL` in Vercel to your Railway URL.
