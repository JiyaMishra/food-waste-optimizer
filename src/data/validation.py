from pathlib import Path
import pandas as pd

PROVENANCE = {"is_synthetic", "generation_seed", "generated_at", "scenario_id"}
def validate_dataset(data_dir="data/generated"):
    root = Path(data_dir)
    errors, report = [], {}
    for path in sorted(root.glob("*.csv")):
        df = pd.read_csv(path)
        report[path.name] = {"rows":len(df), "missing_cells":int(df.isna().sum().sum())}
        missing = PROVENANCE - set(df.columns)
        if missing: errors.append(f"{path.name}: missing provenance columns {sorted(missing)}")
        if "is_synthetic" in df and not df["is_synthetic"].astype(str).str.lower().eq("true").all():
            errors.append(f"{path.name}: non-synthetic or missing provenance flag")
        for col in [c for c in df.columns if c.endswith("_qty") or c in ("arrivals","consumed_qty","prepared_qty","served_qty")]:
            if (pd.to_numeric(df[col], errors="coerce").dropna() < 0).any():
                errors.append(f"{path.name}: negative values in {col}")
    ops_path = root/"food_operations.csv"
    if ops_path.exists():
        ops = pd.read_csv(ops_path)
        if not (ops.consumed_qty <= ops.served_qty).all(): errors.append("consumed_qty exceeds served_qty")
        if not (ops.served_qty <= ops.prepared_qty).all(): errors.append("served_qty exceeds prepared_qty")
        if not (ops.untouched_leftover == ops.prepared_qty-ops.served_qty).all():
            errors.append("leftover accounting mismatch")
        if not (ops.plate_waste == ops.served_qty-ops.consumed_qty).all():
            errors.append("plate-waste accounting mismatch")
    att_path = root/"meal_attendance.csv"
    if att_path.exists():
        att = pd.read_csv(att_path)
        totals = att.groupby("meal_id").arrivals.sum()
        # Cumulative attendance must end at total arrivals for each meal.
        last = att.sort_values("interval_start").groupby("meal_id").cumulative_attendance.last()
        if not totals.equals(last.reindex(totals.index).astype(totals.dtype)):
            errors.append("interval arrivals do not reconcile with cumulative attendance")
    return {"ok": not errors, "errors": errors, "files": report}
