import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
from src.data.validation import validate_dataset
result=validate_dataset()
print(json.dumps(result,indent=2))
raise SystemExit(0 if result["ok"] else 1)
