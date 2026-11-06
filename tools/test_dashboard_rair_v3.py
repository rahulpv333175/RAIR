import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.ablations import RAIRv3Study

study = RAIRv3Study()
data = study.describe()
print("RAIRv3Study describe output:")
print(data)
assert "available" in data
print("Dashboard RAIRv3 integration check PASSED!")

