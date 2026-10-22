# Autonomous Context-Aware Food Waste Optimization System

An intelligent, context-driven cafeteria food waste optimization platform combining machine learning demand forecasting, constrained split-batch kitchen optimization, multi-agent orchestration, interactive real-time simulation, and an executive operations dashboard.

> **CRITICAL SYNTHETIC-DATA NOTICE**: All records, student resident rosters, timetable slots, hostel contexts, weather readings, forecasts, waste diagnoses, and simulation outcomes are **synthetic simulations**. The system is **NOT** connected to live VIT attendance, student biometric identity systems, live campus telemetry, or university kitchen facilities.

---

## System Workstreams & Architecture

| Workstream | Lead | Core Deliverables | Technology Stack |
|---|---|---|---|
| **Data & ML Forecaster** | **Person A** | Synthetic dataset generator (6 months), data validator, vegetarian menu catalogue, overlap-safe availability engine, historical lag feature pipeline, Random Forest context-aware model, 80% quantile residual uncertainty, evaluation protocols. | Python 3.11+, Scikit-learn, Pandas, NumPy, Pytest |
| **Backend & Orchestrator** | **Person B** | Production FastAPI application, SQLAlchemy ORM & Alembic migrations (PostgreSQL/SQLite), pre/post meal evidence-based waste diagnosis, deterministic split-batch optimizer, 5-stage sequential agent orchestrator, interval simulation engine, CSV/JSON audit exports. | FastAPI, SQLAlchemy, Alembic, Pydantic v2, PostgreSQL / SQLite |
| **Frontend & Cockpit** | **Person C** | Modern React 19 + TypeScript cockpit, dark glassmorphism design system, persistent synthetic guardrail banners, 4 custom SVG interactive charts, 10 operational dashboard pages, resilient API client with domain error recovery, multi-stage Dockerfile, Docker Compose, 5-7 min demo script, automated 12-step smoke test suite. | React 19, TypeScript, Vite, Lucide Icons, Nginx Alpine, Docker |

---

## Dashboard Pages (Person C Cockpit)

1. **Executive Overview (`/`)**: Daily KPI metrics (portions and kg), system readiness, and daily meal forecast vs waste summary.
2. **Smart Meal Planner (`/planner`)**: Dish demand forecast with 80% residual bounds (`[q10, q90]`) and split-batch optimizer (initial batch, dynamic reserve, trigger threshold).
3. **Rush Timeline (`/timeline`)**: 30-minute interval diner arrival curves and peak rush categorization.
4. **Context & Availability (`/context`)**: Environmental signals (rain, temperature), hostel occupancy, and overlap-safe diner availability deduction.
5. **Waste Diagnosis (`/diagnosis`)**: Pre-meal waste risk scoring and post-meal evidence-based root-cause diagnosis with actionable remedies.
6. **Kitchen Live Simulation (`/simulation`)**: Interactive interval-by-interval meal simulation comparing fixed baseline vs context-aware split-batch policies with real-time reserve triggering.
7. **Menu Analytics (`/menu`)**: Dish popularity, preparation cost per portion, and historical waste intensity tracking.
8. **Policy Evaluation (`/evaluation`)**: Direct policy benchmark comparing baseline vs context-aware policies under identical synthetic demand realizations.
9. **Agent Orchestrator Trace (`/traces`)**: Inspection of the 5-stage sequential autonomous agent workflow with execution latency and payload inspector.
10. **Settings & Data Management (`/settings`)**: Synthetic dataset regeneration, database synchronization, model retraining trigger, and CSV/JSON audit exports.

---

## Quick Start Guide

### Option 1: Single-Command Plug & Play (Recommended - Zero Setup)

Run the entire integrated platform (Backend + ML Engine + Frontend Cockpit) with one command. The unified runner automatically checks dependencies, configures local environment, verifies the SQLite database, and launches both services:

```bash
# Clone and enter the person-c branch
git clone -b person-c https://github.com/JiyaMishra/food-waste-optimizer.git
cd food-waste-optimizer

# Start the full stack:
npm start
# or:
npm run dev
# or:
python run_project.py
```

- **Interactive Web Cockpit**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

*(To stop both services cleanly, press `Ctrl + C` in the terminal).*

---

### Option 2: Full-Stack via Docker Compose

Run the platform in isolated containers (PostgreSQL database, FastAPI backend, and React/Nginx frontend):

```bash
# 1. Copy the environment template
cp .env.example .env

# 2. Build and launch all containers
docker compose up --build
```

- **Frontend Dashboard**: http://localhost:80
- **Backend API & Swagger Docs**: http://localhost:8000/docs
- **PostgreSQL Database**: `localhost:5432`

---

### Option 3: Manual Step-by-Step Setup

#### 1. Backend Setup (FastAPI & ML Engine)
```bash
# Set up Python virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# Install dependencies
python -m pip install -r requirements.txt

# Apply database migrations
alembic -c backend/alembic.ini upgrade head

# Run backend test suite (51 passing tests)
pytest backend/tests -q
pytest tests -q

# Start backend server
python -m uvicorn backend.app.main:app --reload --port 8000
```

#### 2. Frontend Setup (React 19 + TypeScript)
```bash
cd frontend

# Install node dependencies
npm install

# Build production bundle (Zero errors)
npm run build

# Start Vite development server
npm run dev
```

Open your browser to: **http://localhost:5173**

---

## Integration & Smoke Verification

To execute an automated verification of all 12 implementation steps (frontend connectivity, API guardrails, dataset generation, model training, availability, forecasting, optimization, live simulation, diagnosis, agent traces, policy evaluation, and data exports):

```bash
python scripts/person_c_smoke_test.py
```

Expected output:
```
======================================================================
 ALL PERSON C INTEGRATION AND SMOKE TESTS PASSED SUCCESSFULLY! 
======================================================================
```

---

## Operational Units & Accounting Guardrails

1. **Quantities are measured in Portions**:
   - Serving quantities are calculated in discrete whole or fractional portions ($1\text{ portion} \approx 0.35\text{ kg}$).
   - `consumed_qty <= served_qty <= prepared_qty`.
2. **Strict Waste Categorization**:
   - **Untouched Kitchen Leftovers**: Food prepared and kept in holding containers, never served to diners. Hygienic and potentially repurposable.
   - **Post-Consumer Plate Waste**: Food served onto diner plates and returned unconsumed. Bio-waste scrap.
   - **Shortage Count**: Diners arriving who could not be served due to stock exhaustion.
3. **No Mixed Denominators**: Waste ratios are explicitly calculated against either `prepared_portions` or `served_portions` with zero-denominator safeguards.

---

## Key Documentation Links

- [Engineering Audit & Defect Log](docs/engineering_audit.md)
- [Person C Implementation Handover](docs/person_c_handover.md)
- [Person C 5-7 Minute Demonstration Script](docs/person_c_demo_script.md)
- [Person B Backend Handover](docs/person_b_handover.md)
- [Person A Data & ML Handover](docs/person_a_handover.md)
- [Data Dictionary](docs/data_dictionary.md)
- [Evaluation Protocol](docs/evaluation_protocol.md)
