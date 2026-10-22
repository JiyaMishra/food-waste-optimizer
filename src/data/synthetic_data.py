from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

MEALS = ["breakfast", "lunch", "snacks", "dinner"]
GROUPS = [("H01", "M01", 650), ("H02", "M02", 550), ("H03", "M03", 500)]

def generate_synthetic_data(output_dir="data/generated", months=6, seed=42, residents=900):
    """Create deterministic, internally linked synthetic CSVs with provenance metadata."""
    rng = np.random.default_rng(seed)
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    end = pd.Timestamp("2026-08-31")
    dates = pd.date_range(end=end, periods=max(30, months * 30), freq="D")
    scenario_id = "synthetic_baseline_v1"
    generated_at = datetime.now(timezone.utc).isoformat()
    meta = {"is_synthetic": True, "generation_seed": seed, "generated_at": generated_at,
            "scenario_id": scenario_id, "dataset_version": "1.0.0"}

    resident_rows = []
    for i in range(residents):
        hostel, mess, capacity = GROUPS[i % len(GROUPS)]
        resident_rows.append({"resident_key": f"R{i+1:05d}", "hostel_id": hostel,
                              "mess_id": mess, "cohort": f"C{i%6+1}", "active": True, **meta})
    residents_df = pd.DataFrame(resident_rows)
    residents_df.to_csv(out/"residents_synthetic.csv", index=False)

    menu = pd.read_csv("data/menu_seed/vegetarian_menu.csv")
    menu_rows, state_rows, slot_rows, event_rows, weather_rows = [], [], [], [], []
    attendance_rows, operations_rows, preference_rows = [], [], []
    meal_counter = 0
    for day_i, date in enumerate(dates):
        weekday = date.dayofweek
        rain = max(0, float(rng.gamma(1.5, 4) if rng.random() < 0.25 else 0))
        temp = float(np.clip(rng.normal(30, 3), 21, 39))
        weather_rows.append({"date": date.date().isoformat(), "rain_mm": round(rain,2),
                             "temperature_c": round(temp,1), "weather_label": "rainy" if rain>5 else "normal",
                             "source_type": "synthetic", **meta})
        event = (day_i % 37 == 0)
        if event:
            event_rows.append({"event_id": f"E{day_i:04d}", "date": date.date().isoformat(),
                               "start_time":"16:00", "end_time":"20:00", "event_type":"campus_event",
                               "expected_participants": int(rng.integers(80,260)), **meta})
        for hostel, mess, capacity in GROUPS:
            occupied = int(rng.integers(int(capacity*.78), capacity+1))
            state_rows.append({"date":date.date().isoformat(),"hostel_id":hostel,"mess_id":mess,
                               "capacity":capacity,"occupied_count":occupied,
                               "occupancy_rate":round(occupied/capacity,4),**meta})
            # Synthetic academic blocks are documented context, not a real timetable.
            slot_rows.append({"date":date.date().isoformat(),"cohort_id":f"{hostel}_COHORT",
                              "activity_type":"class_or_lab","start_time":"08:00","end_time":"10:00",
                              "location_id":"SYNTHETIC_CAMPUS",**meta})
        for meal in MEALS:
            meal_counter += 1
            meal_id = f"MEAL{meal_counter:07d}"
            meal_dishes = menu[menu.meal_type == meal]
            if meal_dishes.empty:
                meal_dishes = menu.iloc[[0]]
            occupancy = sum(x[2] for x in GROUPS) * float(rng.uniform(.78,.98))
            meal_factor = {"breakfast":.54,"lunch":.76,"snacks":.34,"dinner":.68}[meal]
            context_factor = (0.88 if weekday == 6 else 1.0) * (0.90 if rain > 12 else 1.0)
            if event and meal in ("snacks","dinner"): context_factor *= 1.10
            demand_total = max(10, int(occupancy * meal_factor * context_factor * rng.normal(1,.06)))
            # 30-minute arrival intervals reconcile exactly to meal attendance.
            weights = rng.dirichlet(np.ones(4)*2)
            arrivals = rng.multinomial(demand_total, weights)
            cumulative = 0
            for j, amount in enumerate(arrivals):
                cumulative += int(amount)
                interval = ["07:00","07:30","08:00","08:30"][j] if meal=="breakfast" else \
                           (["12:00","12:30","13:00","13:30"][j] if meal=="lunch" else \
                           (["16:30","17:00","17:30","18:00"][j] if meal=="snacks" else
                            ["19:00","19:30","20:00","20:30"][j]))
                attendance_rows.append({"meal_id":meal_id,"date":date.date().isoformat(),"meal_type":meal,
                                        "interval_start":interval,"arrivals":int(amount),
                                        "cumulative_attendance":cumulative,"hostel_id":"ALL_SYNTHETIC",**meta})
            dish_total = 0
            chosen = meal_dishes.to_dict("records")
            for d in chosen:
                share = 1/len(chosen)
                demand = max(0, int(demand_total*share*rng.uniform(.75,1.25)))
                prepared = int(np.ceil(demand*rng.uniform(1.03,1.22)))
                served = min(prepared, int(np.ceil(demand*rng.uniform(.95,1.08))))
                consumed = int(rng.integers(0, served+1))
                operations_rows.append({"meal_id":meal_id,"date":date.date().isoformat(),"meal_type":meal,
                    "dish_id":d["dish_id"],"prepared_qty":prepared,"served_qty":served,
                    "consumed_qty":consumed,"untouched_leftover":prepared-served,
                    "plate_waste":served-consumed,"demand_qty":demand,"unit":"portions",**meta})
                is_veg = bool(str(d.get("vegetarian_flag", "true")).strip().lower() in ("true", "1", "yes"))
                menu_rows.append({"date":date.date().isoformat(),"meal_id":meal_id,"meal_type":meal,
                                  "dish_id":d["dish_id"],"dish_name":d["dish_name"],"vegetarian_flag":is_veg,**meta})
    pd.DataFrame(state_rows).to_csv(out/"hostel_daily_state.csv",index=False)
    pd.DataFrame(slot_rows).to_csv(out/"academic_slots.csv",index=False)
    pd.DataFrame(event_rows, columns=["event_id","date","start_time","end_time","event_type","expected_participants",
        "is_synthetic","generation_seed","generated_at","scenario_id","dataset_version"]).to_csv(out/"campus_events.csv",index=False)
    pd.DataFrame(weather_rows).to_csv(out/"weather_daily.csv",index=False)
    pd.DataFrame(menu_rows).to_csv(out/"menu_calendar.csv",index=False)
    pd.DataFrame(attendance_rows).to_csv(out/"meal_attendance.csv",index=False)
    pd.DataFrame(operations_rows).to_csv(out/"food_operations.csv",index=False)
    # Synthetic preference responses; never real survey data. Each respondent rates
    # a subset of dishes, creating enough observations for preference aggregation.
    for respondent_i in range(min(max(residents, 100), 300)):
        chosen_count = min(len(menu), int(rng.integers(3, min(7, len(menu)) + 1)))
        chosen_indices = rng.choice(len(menu), size=chosen_count, replace=False)
        for menu_i in chosen_indices:
            row = menu.iloc[int(menu_i)]
            preference_rows.append({"respondent_key":f"P{respondent_i+1:05d}","dish_id":row.dish_id,
                                    "rating":int(rng.integers(1,6)),"is_synthetic":True,
                                    "generation_seed":seed,"generated_at":generated_at,
                                    "scenario_id":scenario_id,"dataset_version":"1.0.0"})
    pd.DataFrame(preference_rows).to_csv(out/"preference_survey_synthetic.csv",index=False)
    return out
