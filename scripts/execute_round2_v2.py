"""Freeze and execute the complete corrective campaign without replacing original evidence."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.campaign_round2_v2 import freeze, run, summarize

def main():
    run_dir = ROOT / "runs/campaign-002-amendment-001"
    freeze(ROOT / "prepared/campaign-002/amended_catalog.json", run_dir)
    run(run_dir)
    summarize(run_dir)


if __name__ == "__main__":
    main()
