"""Freeze, prepare and measure the declared three-state ranking pilot."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.campaign_round4 import freeze_preparation, prepare_all, freeze_execution, run_all, summarize


if __name__ == "__main__":
    freeze_preparation()
    if prepare_all():
        freeze_execution()
        run_all()
        summarize()
