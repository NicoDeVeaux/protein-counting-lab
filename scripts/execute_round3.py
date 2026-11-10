"""Freeze and execute campaign003 without replacing any existing evidence."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.campaign_round3 import freeze, run, summarize


def prepare():
    from scripts.prepare_round3 import setup_controls, freeze_preparation, prepare_all

    setup_controls()
    freeze_preparation()
    prepare_all()


def main():
    prepare()
    run_dir = ROOT/"runs/campaign-003"
    freeze(ROOT/"prepared/campaign-003/catalog.json", run_dir)
    run(run_dir)
    summarize(run_dir)


if __name__ == "__main__":
    main()
