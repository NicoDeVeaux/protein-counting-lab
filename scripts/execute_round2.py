"""Execute the already prepared and tested local campaign as one supervised job."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.campaign_round2 import freeze, run, summarize

run_dir = ROOT / "runs/campaign-002"
freeze(ROOT / "prepared/campaign-002/catalog.json", run_dir)
run(run_dir)
summarize(run_dir)
