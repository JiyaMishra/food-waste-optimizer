from src.data.validation import validate_dataset

def test_generated_data_passes_validation(tmp_path):
    import pandas as pd
    meta={"is_synthetic":True,"generation_seed":42,"generated_at":"2026-01-01T00:00:00+00:00",
          "scenario_id":"test","dataset_version":"1"}
    pd.DataFrame([{"meal_id":"m1","dish_id":"d1","prepared_qty":10,"served_qty":8,
        "consumed_qty":6,"untouched_leftover":2,"plate_waste":2,"unit":"portions",**meta}]).to_csv(
        tmp_path/"food_operations.csv",index=False)
    report=validate_dataset(tmp_path)
    assert report["ok"], report["errors"]
