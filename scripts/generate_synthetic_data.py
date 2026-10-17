import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from src.data.synthetic_data import generate_synthetic_data
p=argparse.ArgumentParser()
p.add_argument("--months",type=int,default=6); p.add_argument("--seed",type=int,default=42)
p.add_argument("--residents",type=int,default=900)
a=p.parse_args()
out=generate_synthetic_data(months=a.months,seed=a.seed,residents=a.residents)
print(f"Synthetic datasets generated in {out.resolve()}")
