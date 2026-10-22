# Engineering Audit & Architectural Assessment
**Project:** Autonomous Context-Aware Food Waste Optimization System  
**Repository:** `https://github.com/JiyaMishra/food-waste-optimizer`  
**Target Branch:** `person-c`  
**Date:** October 2026  
**Auditor:** Senior Full-Stack & ML Systems Engineer, QA Lead  

---

## 1. Executive Summary & Baseline State

This engineering audit assesses the repository against the master specification: **`Autonomous_Context_Aware_Food_Waste_Optimization_Implementation_Blueprint.docx`**, as well as the Person A, B, and C guides, handover documents, and current codebase.

### Baseline Health Check Results
* **Python Backend Test Suite:** `pytest tests backend/tests -v`
  * **Result:** **50 passed** (36 backend tests, 14 root unit tests), with 5 deprecation warnings.
* **Database & Migrations:** `alembic -c backend/alembic.ini current`
  * **Result:** Up to date at head (`2d8896a08ce2`).
* **Frontend Lint & Typecheck:** `npm --prefix frontend run lint && npm --prefix frontend run build`
  * **Result:** Build succeeded with 0 errors. **44 oxlint warnings** identified (unused imports, set-state in effect, unhandled hook dependencies).
* **End-to-End Workflow Verification:** `backend/scripts/demo_workflow.py`
  * **Result:** Successfully ran all 13 end-to-end integration stages against `TestClient(app)` using SQLite.

---

## 2. Confirmed Defects Discovered

### Defect 1: Hardcoded Meal Times & Intervals Across Frontend Pages
* **Severity:** High (Breaks core multi-meal operations)
* **Location:** `frontend/src/pages/MealPlanner.tsx`, `frontend/src/pages/RushTimeline.tsx`, `frontend/src/pages/Overview.tsx`, `backend/app/schemas/agents.py`
* **Details:**
  * In `MealPlanner.tsx`, the service intervals are hardcoded to `07:00, 07:30, 08:00, 08:30` and service window is hardcoded to `07:00` - `10:00`.
  * When a user changes the meal dropdown to `lunch` (12:00–14:30), `snacks` (16:00–18:30), or `dinner` (19:00–21:30), the planner continues sending 07:00 morning intervals.
  * In `PlanningWorkflowRequest` schema, `service_start` and `service_close` default to `07:00` and `10:00`, which conflicts with non-breakfast meals where intervals are in the afternoon/evening.
* **Remedy:** Parameterize meal windows and interval generators by `MealType` (`breakfast`: 07:00–09:30, `lunch`: 12:00–14:30, `snacks`: 16:00–18:30, `dinner`: 19:00–21:30) across frontend and backend schemas.

### Defect 2: Hardcoded Dish Selection in Kitchen Simulation & Waste Diagnosis
* **Severity:** Medium-High (Limits interactive testing)
* **Location:** `frontend/src/pages/KitchenSimulation.tsx`, `frontend/src/pages/WasteDiagnosis.tsx`, `frontend/src/pages/Evaluation.tsx`
* **Details:**
  * In `KitchenSimulation.tsx`, starting a simulation hardcodes `dish_external_id: 'D001'`, `forecast_expected: 288`, `initial_qty: 380`, `reserve_qty: 100`, `trigger_qty: 80`. Selecting `lunch` or `dinner` still runs simulation against breakfast dish D001 (Idli).
  * In `WasteDiagnosis.tsx`, `runPreMealDiagnosis` hardcodes `D001` with `prediction: 288, lower_bound: 184, upper_bound: 346`.
  * In `Evaluation.tsx`, live comparison fallback hardcodes `D001`.
* **Remedy:** Implement dynamic dish selector pulling from the active meal menu items (`api.getMenu`), populating dish-specific forecasts and batch plans automatically.

### Defect 3: Deprecated FastAPI Startup Event Handler
* **Severity:** Medium (Compatibility / Technical Debt)
* **Location:** `backend/app/main.py:49`
* **Details:** `@app.on_event("startup")` is deprecated in Starlette/FastAPI in favor of the `lifespan` context manager on `FastAPI(lifespan=...)`.
* **Remedy:** Refactor application lifecycle to modern `asynccontextmanager` lifespan handler.

### Defect 4: Deprecated Pandas Timedelta Unit Construction
* **Severity:** Low-Medium (Future Runtime Error)
* **Location:** `backend/app/services/forecasting.py:222`
* **Details:** `cutoff = operations["date"].max() + pd.Timedelta(days=1)` emits:
  `DeprecationWarning: The 'generic' unit for NumPy timedelta is deprecated, and will raise an error in the future.`
* **Remedy:** Replace with `pd.Timedelta(days=1)` with explicit conversion or `pd.DateOffset(days=1)`.

### Defect 5: Oxlint 44 Frontend Warnings
* **Severity:** Low (Code Hygiene)
* **Location:** `frontend/src/pages/` and `frontend/src/charts/`
* **Details:** Unused imports (e.g., `TrendingUp`, `AlertTriangle`, `Calendar`, `Sparkles`), calling `setState` inside `useEffect` causing render cycles, and missing `exhaustive-deps`.
* **Remedy:** Clean up all unused imports, optimize `useEffect` dependencies, and derive state properly.

---

## 3. Security, Privacy & Repository Hygiene

### Security Concern 1: `.env` Tracked in Version Control
* **Status:** Confirmed.
* **Details:** While the current `.env` contains local development defaults (`CORS_ORIGINS`, `ENVIRONMENT=local`, `VITE_API_BASE_URL`), tracking `.env` directly in git presents a significant credential leakage risk if a developer adds real database or API secrets.
* **Remedy:**
  1. Remove `.env` from git tracking (`git rm --cached .env`).
  2. Add `.env` and `*.env` to `.gitignore`.
  3. Ensure `.env.example` remains tracked as a safe placeholder template without secrets.

### Security Concern 2: Committed Local Database Binary File
* **Status:** Confirmed.
* **Details:** `backend/data/food_optimizer.db` is tracked in git. SQLite database files should not be checked into git repositories as they inflate repo size and can cause merge conflicts.
* **Remedy:**
  1. Remove `backend/data/food_optimizer.db` from git tracking (`git rm --cached backend/data/food_optimizer.db`).
  2. Add `backend/data/*.db` and `*.db` to `.gitignore`.

### Security Concern 3: Synthetic Data & Privacy Guardrails
* **Status:** Verified compliant.
* **Details:** No real student identifiers, VIT registration numbers, or real personal biometric records are used. All resident keys use pseudonymous identifiers (`R00001`...`R00900`), hostel codes (`H01`..`H03`), and synthetic weather/attendance data. The global `SYNTHETIC DEMO DATA` banner is visible across the application.

---

## 4. Product Quality & Blueprint Page Alignment

The blueprint and specification mandate 10 complete pages:

| Blueprint Required Page | Current Route / Component | Alignment Status | Required Enhancements |
|---|---|---|---|
| 1. Executive Overview | `Overview.tsx` | Partial (Uses synthetic approximations for arrival preview) | Connect interval arrival curve to real backend availability & attendance |
| 2. Smart Meal Planner | `MealPlanner.tsx` | Partial (Hardcoded breakfast hours) | Parameterize by meal type; support all dishes from vegetarian menu |
| 3. Rush Timeline | `RushTimeline.tsx` | Partial (Fixed share multipliers) | Dynamically display arrival intervals and rush classification |
| 4. Context & Availability | `ContextAvailability.tsx` | Complete | Display all synthetic factors, weather, timetable, and caveats |
| 5. Waste Diagnosis | `WasteDiagnosis.tsx` | Partial (Pre-meal diagnosis hardcodes D001) | Query active date/meal forecast and plan dynamically |
| 6. Kitchen Simulation | `KitchenSimulation.tsx` | Partial (Hardcodes D001) | Add dish selector; support stepping and finish with real database persistence |
| 7. Menu Analytics | `MenuAnalytics.tsx` | Complete | Dish popularity, portion size, and category breakdown |
| 8. Policy Evaluation | `Evaluation.tsx` | Complete | Baseline vs Context split-batch benchmark with clear units and denominators |
| 9. Agent Orchestrator Trace | `AgentTrace.tsx` | Complete | 5-stage sequential workflow trace, timing, status, and payload inspection |
| 10. Settings & Data Management | `SettingsData.tsx` | Complete | Seeded generation, database sync, model retraining, JSON/CSV exports |

---

## 5. Prioritized Implementation & Repair Plan

1. **Security & Hygiene First:** Untrack `.env` and `food_optimizer.db`, update `.gitignore`, and verify clean git status. (COMPLETED)
2. **Backend Modernization:**
   - Migrate FastAPI `on_event("startup")` to `lifespan` context manager. (COMPLETED)
   - Fix NumPy/Pandas timedelta deprecation warning across backend and scripts. (COMPLETED)
   - Parameterize `PlanningWorkflowRequest` default meal window times based on meal type. (COMPLETED)
   - Add unit test `test_planning_workflow_lunch_and_dinner` to permanently verify non-breakfast planning workflows. (COMPLETED)
3. **Frontend Integration & Bug Fixes:**
   - Parameterize meal windows and intervals across `MealPlanner`, `RushTimeline`, `Overview`, `KitchenSimulation`. (COMPLETED)
   - Add dish selector to `KitchenSimulation` and `WasteDiagnosis`. (COMPLETED)
   - Connect `Overview` timeline chart to real availability response. (COMPLETED)
   - Resolve all oxlint warnings, clean unused imports, wrap data fetching in `useCallback` with proper dependencies. (COMPLETED)
4. **Verification & Regression Testing:**
   - Run pytest suite (all 51 tests passing with 0 project warnings). (COMPLETED)
   - Run frontend oxlint (0 errors) and production build (`tsc -b && vite build` passing cleanly in ~225ms). (COMPLETED)
   - Run end-to-end smoke test script (`scripts/person_c_smoke_test.py` - all 12 steps PASSED). (COMPLETED)
   - Validate and verify Docker Compose configuration (`docker-compose config` verified). (COMPLETED)

---

## 6. Verification & Resolution Results

| Test / Check | Command Executed | Result | Notes |
|---|---|---|---|
| **Security / Git Hygiene** | `git status` / `.gitignore` inspection | **VERIFIED** | `.env` and `food_optimizer.db` untracked from git; `.env.example` verified safe. |
| **Backend Unit & Integration Tests** | `pytest tests backend/tests -v` | **51 PASSED / 0 FAILED** | All tests passed cleanly. 0 project deprecation warnings. |
| **Reproducibility Test** | `python scripts/check_reproducibility.py` | **PASSED** | All 9 generated CSVs are bit-for-bit reproducible for seed 42. |
| **Synthetic Dataset Validation** | `python scripts/validate_data.py` | **PASSED** | 0 missing cells, 0 schema errors across all 9 operational tables. |
| **Model Training & Evaluation** | `python scripts/train_model.py && python scripts/evaluate_model.py` | **PASSED** | Context-aware model beats baseline MAE chronologically; 0 warnings. |
| **Frontend Linting** | `npm --prefix frontend run lint` | **0 ERRORS** | All unused imports, unhandled hooks, and dependency issues resolved. |
| **Frontend Production Build** | `npm --prefix frontend run build` | **PASSED (0 errors)** | `tsc -b && vite build` bundled client in 225ms (346 kB gzip: 98.7 kB). |
| **Full End-to-End Smoke Test** | `python scripts/person_c_smoke_test.py` | **ALL 12 STEPS PASSED** | Verified frontend reachability, health, generation, training, forecasting, batch plan, kitchen simulation, waste diagnosis, multi-agent orchestrator, evaluation comparison, and JSON/CSV exports. |
| **Headless Workflow Demo** | `python backend/scripts/demo_workflow.py` | **PASSED** | Ran all 13 stages against FastAPI TestClient. |
| **Docker Configuration** | `docker-compose config` | **VALID** | Compose configuration validated with Postgres 16, FastAPI backend, and Nginx frontend. |
| **GitHub Actions CI** | `.github/workflows/person-c-ci.yml` | **CONFIGURED** | Full-stack CI workflow automated for `person-c` branch. |

