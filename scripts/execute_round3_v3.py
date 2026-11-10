"""Validate the complete metadata correction, then run the unchanged experiment."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.bind_round3_enum import bind, verify_binding
from scripts.campaign_round3 import freeze, run, summarize


def main():
    if not (ROOT / "prepared/campaign-003/binding-amendment-003.json").exists():
        bind()
    verify_binding()
    run_dir = ROOT / "runs/campaign-003-amendment-003"
    freeze(ROOT / "prepared/campaign-003/catalog.amendment-003.json", run_dir)
    run(run_dir)
    summarize(run_dir)


if __name__ == "__main__":
    main()
