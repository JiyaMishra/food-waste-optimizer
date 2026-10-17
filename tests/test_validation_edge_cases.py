import pandas as pd
from src.data.validation import validate_dataset

def test_missing_directory_fails_clearly(tmp_path):
    report = validate_dataset(tmp_path / "missing")
    assert not report["ok"]
    assert "does not exist" in report["errors"][0]

def test_invalid_quantity_accounting_is_reported(tmp_path):
    meta = {"is_synthetic": True, "generation_seed": 42, "generated_at": "2026-01-01T00:00:00Z",
            "scenario_id": "test", "dataset_version": "1"}
    pd.DataFrame([{"meal_id":"m1","dish_id":"d1","prepared_qty":10,"served_qty":8,
        "consumed_qty":9,"untouched_leftover":2,"plate_waste":-1,"demand_qty":8,**meta}]).to_csv(
        tmp_path/"food_operations.csv", index=False)
    report = validate_dataset(tmp_path)
    assert not report["ok"]
    assert any("negative values" in e or "consumed_qty exceeds" in e for e in report["errors"])
