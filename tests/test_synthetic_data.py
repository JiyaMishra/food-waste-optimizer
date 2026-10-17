def test_quantity_invariants():
    import pandas as pd
    from pathlib import Path
    p=Path("data/generated/food_operations.csv")
    if not p.exists():
        import pytest; pytest.skip("Run synthetic data generator first")
    df=pd.read_csv(p)
    assert (df.consumed_qty <= df.served_qty).all()
    assert (df.served_qty <= df.prepared_qty).all()
    assert (df[["prepared_qty","served_qty","consumed_qty"]] >= 0).all().all()
    assert df.is_synthetic.astype(str).str.lower().eq("true").all()
