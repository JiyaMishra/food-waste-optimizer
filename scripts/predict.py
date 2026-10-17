import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse, json
import joblib
import pandas as pd
p=argparse.ArgumentParser(); p.add_argument("--date",required=True); p.add_argument("--meal-type",default="breakfast")
a=p.parse_args()
artifact=joblib.load("ml/artifacts/context_model.joblib")
ops=pd.read_csv("data/generated/food_operations.csv",parse_dates=["date"])
date=pd.Timestamp(a.date); weekday=date.dayofweek; month=date.month
hist=ops[(ops.date < date)&(ops.meal_type==a.meal_type)]
if hist.empty: raise SystemExit("No historical rows before requested date; generate a longer history.")
rows=[]
for dish, g in hist.groupby("dish_id"):
    g=g.sort_values("date"); last=float(g.demand_qty.iloc[-1])
    rolling=float(g.tail(7).demand_qty.mean())
    x=pd.DataFrame([{"weekday":weekday,"month":month,"demand_lag_1":last,"demand_rolling_7":rolling}])[artifact["features"]]
    pred=max(0,float(artifact["model"].predict(x)[0]))
    rows.append({"date":a.date,"meal_type":a.meal_type,"dish_id":dish,"predicted_demand":round(pred,2),
                 "lower_bound":round(max(0,pred*.8),2),"upper_bound":round(pred*1.2,2),
                 "model_version":artifact["model_version"],"forecast_cutoff":a.date,
                 "feature_schema_version":"1.0","is_synthetic":True})
print(json.dumps(rows,indent=2))
