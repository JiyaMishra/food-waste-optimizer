from src.data.validation import validate_dataset
import pandas as pd

def test_generated_data_passes_validation(tmp_path):
    meta={"is_synthetic":True,"generation_seed":42,"generated_at":"2026-01-01T00:00:00+00:00",
          "scenario_id":"test","dataset_version":"1"}
    pd.DataFrame([{"resident_key":"r1","hostel_id":"h1","mess_id":"m1",**meta}]).to_csv(
        tmp_path/"residents_synthetic.csv",index=False)
    pd.DataFrame([{"date":"2026-01-01","hostel_id":"h1","mess_id":"m1",**meta}]).to_csv(
        tmp_path/"hostel_daily_state.csv",index=False)
    pd.DataFrame([{"date":"2026-01-01","cohort_id":"c1",**meta}]).to_csv(
        tmp_path/"academic_slots.csv",index=False)
    pd.DataFrame(columns=["event_id","date","start_time","end_time","event_type","expected_participants",
        "is_synthetic","generation_seed","generated_at","scenario_id","dataset_version"]).to_csv(
        tmp_path/"campus_events.csv",index=False)
    pd.DataFrame([{"date":"2026-01-01","rain_mm":0,"temperature_c":28,**meta}]).to_csv(
        tmp_path/"weather_daily.csv",index=False)
    pd.DataFrame([{"meal_id":"m1","dish_id":"d1",**meta}]).to_csv(tmp_path/"menu_calendar.csv",index=False)
    pd.DataFrame([{"respondent_key":"p1","dish_id":"d1","rating":4,**meta}]).to_csv(
        tmp_path/"preference_survey_synthetic.csv",index=False)
    pd.DataFrame([{"meal_id":"m1","interval_start":"07:00","arrivals":10,
        "cumulative_attendance":10,**meta}]).to_csv(tmp_path/"meal_attendance.csv",index=False)
    pd.DataFrame([{"meal_id":"m1","dish_id":"d1","prepared_qty":10,"served_qty":8,
        "consumed_qty":6,"untouched_leftover":2,"plate_waste":2,"demand_qty":8,**meta}]).to_csv(
        tmp_path/"food_operations.csv",index=False)
    report=validate_dataset(tmp_path)
    assert report["ok"], report["errors"]
