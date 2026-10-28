"""Fail CI when ruff or mypy finds MORE problems than ci/baselines.json allows.

The codebase has known lint/type debt; blocking every PR on it would just get
the check disabled. This ratchet blocks new problems and asks for the baseline
to be lowered when problems are fixed.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = json.loads((ROOT / "ci" / "baselines.json").read_text())

ruff = subprocess.run([sys.executable, "-m", "ruff", "check", "src", "tests", "--output-format", "json"],
                      cwd=ROOT, capture_output=True, text=True)
ruff_count = len(json.loads(ruff.stdout or "[]"))

mypy = subprocess.run([sys.executable, "-m", "mypy", "src"], cwd=ROOT, capture_output=True, text=True)
m = re.search(r"Found (\d+) errors?", mypy.stdout)
mypy_count = int(m.group(1)) if m else (0 if "Success" in mypy.stdout else -1)
if mypy_count < 0:
    print(mypy.stdout[-2000:], mypy.stderr[-2000:])
    sys.exit("mypy did not run")

failed = False
for name, count in (("ruff", ruff_count), ("mypy", mypy_count)):
    allowed = base[name]
    status = "OK" if count <= allowed else "FAIL"
    print(f"{name}: {count} (baseline {allowed}) {status}")
    if count > allowed:
        failed = True
        print((ruff.stdout if name == "ruff" else mypy.stdout)[-4000:])
    elif count < allowed:
        print(f"  {name} improved: lower ci/baselines.json to {count}")
sys.exit(1 if failed else 0)
