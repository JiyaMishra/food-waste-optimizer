# Data dictionary (Person A synthetic package)

All records are simulated. Quantities are portions unless otherwise stated. CSV rows carry provenance columns is_synthetic, generation_seed, generated_at, scenario_id and dataset_version (the event file includes these columns even when there are no events).

| File | Grain / primary key | Important fields and units | Purpose |
|---|---|---|---|
| residents_synthetic.csv | one pseudonymous synthetic resident; resident_key | hostel_id, mess_id, cohort, active | Synthetic population segments; no real names or student IDs |
| hostel_daily_state.csv | date + hostel/mess | capacity, occupied_count (people), occupancy_rate (0–1) | Daily synthetic occupancy context |
| academic_slots.csv | date + synthetic cohort/activity | activity_type, start_time, end_time, location_id | Synthetic timetable context |
| campus_events.csv | synthetic event_id | date, start/end, event type, expected participants | Optional synthetic events |
| weather_daily.csv | date | rain_mm (mm), temperature_c (°C), weather_label | Simulated weather context, not live weather |
| menu_calendar.csv | meal_id + dish_id | date, meal type, dish name, vegetarian flag | Dish served in each synthetic meal |
| preference_survey_synthetic.csv | respondent key + dish | rating (synthetic ordinal response) | Illustrative synthetic preference responses, not real survey data |
| meal_attendance.csv | meal_id + interval_start | arrivals and cumulative attendance (people) | Four 30-minute interval arrival estimates per meal; final cumulative equals sum of arrivals |
| food_operations.csv | meal_id + dish_id | demand_qty, prepared_qty, served_qty, consumed_qty, untouched_leftover, plate_waste (portions) | Synthetic demand and waste outcomes |

## Quantity rules
- All quantity fields must be non-negative.
- consumed_qty <= served_qty <= prepared_qty.
- untouched_leftover = prepared_qty - served_qty.
- plate_waste = served_qty - consumed_qty.
- Unserved leftovers and plate waste are separate; do not add them twice.
- Menu and food-operations (meal_id, dish_id) keys should match.

## Forecast schema
Dish forecasts: date, meal_type, dish_id, prediction, lower_bound, upper_bound, model_version, forecast_cutoff, feature_schema_version, interval_method, interval_is_calibrated, unit, is_synthetic.
Arrival forecasts: date, meal_type, interval_start, predicted_arrivals, lower_bound, upper_bound, rush_class, historical_samples, is_synthetic, interval_method.
