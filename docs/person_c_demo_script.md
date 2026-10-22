# Autonomous Context-Aware Food Waste Optimization System
## Person C — 5 to 7 Minute Demonstration & Presentation Script

> **Important Synthetic Disclosure**: All data, residents, hostel contexts, weather readings, meal schedules, and optimization results demonstrated in this walkthrough are **synthetic simulations**. The system is not connected to live VIT student biometric attendance, campus kitchen telemetry, or active university ERPs.

---

### Demonstration Overview & Timing Breakdown

| Segment | Timing | Dashboard View | Key Discussion Points |
|---|---|---|---|
| 1. Introduction & Guardrails | 0:00 – 0:45 | **Global UI / Header** | Synthetic disclosure, unit hygiene, problem statement, architecture |
| 2. Executive Overview | 0:45 – 1:30 | **Overview Page** | KPI cards (portions vs kg), health check, quick actions, demand vs waste |
| 3. Context & Availability | 1:30 – 2:15 | **Context & Availability** | Weather, hostel occupancy, exam/holiday calendar, overlap-safe availability formula |
| 4. Smart Meal Planner | 2:15 – 3:15 | **Meal Planner** | Dish demand forecast, 80% quantile uncertainty bounds, split-batch optimizer |
| 5. Kitchen Live Simulation | 3:15 – 4:30 | **Kitchen Live Simulation** | Baseline vs context-aware policy, step-by-step interval progression, dynamic reserve release |
| 6. Waste Diagnosis & Trace | 4:30 – 5:30 | **Diagnosis & Agent Trace** | Pre-meal risk vs post-meal root-cause diagnosis, 5-stage agent execution pipeline |
| 7. Policy Evaluation & Wrap | 5:30 – 6:30 | **Evaluation & Settings** | Side-by-side benchmark, waste reduction percentage, shortage protection, exports |

---

### Step-by-Step Walkthrough & Talking Points

#### Segment 1: Introduction & System Guardrails (0:00 – 0:45)
- **Visual**: Point out the persistent warning banner at the top of the interface:
  `SYNTHETIC DEMO DATA — All records, forecasts, and simulation results are generated for demonstration. Not connected to live VIT cafeteria or kitchen systems.`
- **Talking Points**:
  - *"Welcome. Today we are demonstrating the frontend and interactive decision cockpit for the Autonomous Context-Aware Food Waste Optimization System."*
  - *"Before we dive into the operational screens, notice our global guardrails: every single screen explicitly labels data as synthetic. We enforce strict unit discipline: quantities are tracked in **portions** (standard meal units) with explicit conversion to kilograms ($0.35\text{ kg/portion}$), ensuring food operations never mix up serving counts with physical mass."*
  - *"Notice the top navigation bar displays live API connectivity to Person B's FastAPI backend (`http://localhost:8000`), model training cutoff status, and interactive scenario switcher."*

---

#### Segment 2: Executive Overview (0:45 – 1:30)
- **Visual**: Navigate to **Overview** (`/`).
- **Talking Points**:
  - *"The Overview cockpit serves as the daily operational summary for mess managers and kitchen supervisors."*
  - *"In the top KPI row, we monitor Today's Planned Portions, Total Prepared, Served, and our primary waste metrics. Crucially, notice how we separate **Untouched Kitchen Leftovers** (unserved food still in warming trays) from **Post-Consumer Plate Waste** (scrapped food from dining tables). Conflating these two leads to bad kitchen interventions."*
  - *"Below the KPIs, we see the System Readiness indicator, confirming the database status and machine learning model artifact (`context-rf-v4`)."*
  - *"The Demand vs Waste summary chart visualizes our demand forecast alongside unserved food and shortages across breakfast, lunch, snacks, and dinner."*

---

#### Segment 3: Context & Diner Availability Deep-Dive (1:30 – 2:15)
- **Visual**: Navigate to **Context & Availability** (`/context`).
- **Talking Points**:
  - *"Why do traditional university cafeterias overcook? Because they plan with static historical averages without considering contextual shocks."*
  - *"Here we inspect our environmental and hostel signals for the selected date: rainfall (e.g., $20.4\text{ mm}$ rain suppresses out-of-campus dining), temperature, and active hostel occupancy ($574 / 650$ students present)."*
  - *"The Diner Availability Engine calculates the effective dining population. Notice the calculation: Total Residents minus Academic Unavailability (lab slots/classes) and Event Absences (hackathons/festivals). Person A and B implemented conservative overlapping-absence protection so students are not double-deducted."*
  - *"This gives us an Expected Diners metric with clear confidence indicators before any food is prepped."*

---

#### Segment 4: Smart Meal Planner & Split-Batch Optimizer (2:15 – 3:15)
- **Visual**: Navigate to **Meal Planner** (`/planner`).
- **Talking Points**:
  - *"Now we step into meal production planning for our vegetarian dishes (e.g., Paneer Butter Masala, Dal Makhani, Mixed Vegetable Korma)."*
  - *"For each dish, the Context-Aware Random Forest predicts expected demand. Look at the Demand Forecast Card: we don't just output a single point estimate like $288$ portions. We provide **80% Residual Quantile Uncertainty Bounds** ($184$ to $346$ portions). Kitchen staff need to see the risk spread."*
  - *"Below the forecast is the **Constrained Split-Batch Optimizer**. Instead of cooking all 300 portions in one large batch at 07:00 (which guarantees massive waste if students skip breakfast), the optimizer solves for:*
    1. **Initial Batch** (e.g., $300$ portions) cooked prior to service opening.
    2. **Dynamic Reserve** (e.g., $60$ portions) prepped but held in holding state.
    3. **Trigger Threshold** (e.g., $98$ portions remaining) which dictates when the kitchen should fire the secondary cook.
  - *"The system explains its rationale in plain text: balancing expected leftover against shortage penalty while respecting minimum kettle cook sizes."*

---

#### Segment 5: Real-Time Kitchen Live Simulation (3:15 – 4:30)
- **Visual**: Navigate to **Kitchen Simulation** (`/simulation`).
- **Talking Points**:
  - *"This is our core operational innovation: the Step-by-Step Meal Service Simulator. We compare two distinct policies running against the exact same synthetic diner arrival sequence:"*
    - **Baseline Fixed Policy**: Cook entire forecasted demand upfront at interval 0.
    - **Context-Aware Split-Batch Policy**: Cook initial batch, monitor interval depletion, and dynamically trigger or cancel the reserve.
  - *Click 'Next Interval (+30 min)' or 'Auto-Play':*
    - *"Interval 0 (07:00): 34 diners arrive. Stock decreases smoothly. Holding trigger is monitored."*
    - *"Interval 1 (07:30): 26 diners arrive. Kitchen stays on 'HOLD'."*
    - *"Interval 2 (08:00): A massive morning rush occurs ($149$ arrivals). Remaining stock drops to $90$ portions, dipping below our $98$-portion threshold!"*
    - *"Notice the decision audit log: The optimizer issues an alert: 'RESERVE TRIGGERED / PREPARED' or 'RESERVE CANCELLED' depending on the morning's trajectory."*
    - *"At Interval 3 (08:30): Meal closes. The reserve is cancelled or held, preventing unneeded cooking."*
  - *"The interactive Stock Flow Chart shows remaining inventory, cumulative served meals, and the trigger threshold line in real time."*

---

#### Segment 6: Evidence-Based Waste Diagnosis & Agent Orchestrator (4:30 – 5:30)
- **Visual**: Navigate to **Waste Diagnosis** (`/diagnosis`) then **Agent Trace** (`/traces`).
- **Talking Points**:
  - *"After service concludes, the system diagnoses why waste occurred using formal hypothesis testing:"*
    - *Is it a Model Forecasting Error? ($|Forecast - Actual| > 15\%$)*
    - *Is it a Kitchen Execution Overshoot? ($Prepared > Forecast + 10\%$)*
    - *Is it Low Diner Turnout? ($Available \ll Resident Count$)*
    - *Is it Recipe or Palatability Acceptance? ($Plate Waste > 15\%$)*
  - *"Each diagnosis outputs a confidence score, primary cause, and concrete actionable remedy for tomorrow's shift."*
  - *"Now let's switch to the **Agent Trace** screen. Here we see Person B's multi-agent orchestrator in action. The 5 autonomous agents run sequentially:*
    1. `context_observer`
    2. `availability_estimator`
    3. `demand_forecaster`
    4. `kitchen_planner`
    5. `waste_diagnostician`
  - *"Every stage record displays its execution duration in milliseconds, status badge, input context, and structured output payload."*

---

#### Segment 7: Policy Evaluation, Benchmarking & Wrap-Up (5:30 – 6:30)
- **Visual**: Navigate to **Evaluation** (`/evaluation`) and highlight **Menu Analytics** (`/menu`) & **Settings & Data** (`/settings`).
- **Talking Points**:
  - *"Finally, how do we prove the system works? The Policy Evaluation benchmark runs a rigorous comparison across identical synthetic realizations."*
  - *"Look at the Evaluation Comparison Chart: The context-aware split-batch policy reduces total waste significantly while maintaining a $0.0\%$ shortage rate. In commercial dining, eliminating waste by starving diners is unacceptable; our system guarantees zero shortage while cutting unserved leftovers."*
  - *"In **Menu Analytics**, we track popularity, recipe prep cost, and waste intensity by dish."*
  - *"In **Settings & Data**, administrators can trigger synthetic dataset regeneration, retrain models with a single click, view database row counts, and export all audit records as clean CSV or JSON files."*
  - *"In conclusion, Person C has delivered a resilient, modern, dark-glassmorphism React interface with complete error recovery, live simulation steering, and rigorous mathematical transparency. Thank you!"*
