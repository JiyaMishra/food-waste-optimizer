"""Verify generated synthetic values repeat for a fixed seed (timestamps are expected to differ)."""
import argparse
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.data.synthetic_data import generate_synthetic_data

def substantive_frame(path):
    frame = pd.read_csv(path)
    if "generated_at" in frame.columns:
        frame = frame.drop(columns=["generated_at"])
    return frame.sort_values(list(frame.columns), kind="stable").reset_index(drop=True)

parser = argparse.ArgumentParser()
parser.add_argument("--months", type=int, default=6)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--residents", type=int, default=900)
args = parser.parse_args()
with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
    a = generate_synthetic_data(first, months=args.months, seed=args.seed, residents=args.residents)
    b = generate_synthetic_data(second, months=args.months, seed=args.seed, residents=args.residents)
    files_a = {p.name for p in Path(a).glob("*.csv")}
    files_b = {p.name for p in Path(b).glob("*.csv")}
    if files_a != files_b:
        raise SystemExit(f"CSV file sets differ: {files_a ^ files_b}")
    failures = []
    for name in sorted(files_a):
        left, right = substantive_frame(Path(a) / name), substantive_frame(Path(b) / name)
        try:
            pd.testing.assert_frame_equal(left, right, check_dtype=False)
        except AssertionError as exc:
            failures.append(f"{name}: {exc}")
    if failures:
        raise SystemExit("Reproducibility check failed:\n" + "\n".join(failures))
print(f"PASS: all {len(files_a)} generated CSVs are reproducible for seed={args.seed} (generated_at ignored).")
