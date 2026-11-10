"""Bind amended metadata and measure the unchanged prepared campaign 003."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.bind_round3_amendment import bind, validate_binding
from scripts.campaign_round3 import freeze, run, summarize


def main():
    bind()
    run_dir = ROOT / "runs/campaign-003-amendment-002"
    freeze(ROOT / "prepared/campaign-003/catalog.amendment-002.json", run_dir)
    validate_binding(run_dir)
    run(run_dir)
    summarize(run_dir)


if __name__ == "__main__":
    main()
