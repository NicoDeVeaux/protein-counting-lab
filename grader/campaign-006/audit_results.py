"""Check every published campaign row against independent exact enumeration."""

import argparse
import csv
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

import audit
from oracle import affinity, partition, strict_winner

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.certified_rank6.fixtures import CASE_NAMES, make_case


def independent_key(model):
    return model.n, tuple(sorted(audit.raw(model)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    source_seal = json.loads((args.results / "SOURCE_SEAL.json").read_text())
    assert source_seal == json.loads((ROOT / "experiments/certified_rank6/SOURCE_SEAL.json").read_text())
    for name, expected in source_seal.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    rows = json.loads((args.results / "RAW_RESULTS.json").read_text())
    expected_grid = {(case, method, repeat) for case in CASE_NAMES
                     for method in ("adaptive", "fixed", "ve", "enumeration")
                     for repeat in range(3)}
    assert len(rows) == 96
    assert {(r["case"], r["method"], r["repetition"]) for r in rows} == expected_grid
    intervals = native_states = winner_checks = 0
    truths, all_candidates, models_by_case = {}, {}, {}
    for case in CASE_NAMES:
        candidates = all_candidates[case] = make_case(case)
        models = models_by_case[case] = {}
        for candidate in candidates:
            for model in candidate.models:
                models.setdefault(independent_key(model), model)
        truths[case] = {key: partition(model.n, audit.raw(model)) for key, model in models.items()}
        for key, model in models.items():
            assert audit.core.variable_elimination(model)[0] == truths[case][key]
            assert audit.core.enumerate_partition(model) == truths[case][key]
            native_states += 1
    for row in rows:
        case = row["case"]
        candidates, models, true_z = all_candidates[case], models_by_case[case], truths[case]
        scores = {c.name: affinity(*(true_z[independent_key(m)] for m in c.models)) for c in candidates}
        expected_winner = strict_winner(scores)
        assert row["unique_states"] == len(models)
        assert row["status"] != "timeout", (case, row["method"], "timeout retained but no complete timing verdict")
        if row["status"] == "certified_top1":
            assert row["winner"] == expected_winner and expected_winner is not None
            winner_checks += 1
        elif row["status"] == "exact_top_tie":
            assert row["winner"] is None and expected_winner is None
        else:
            assert row["status"] == "unresolved" and row["winner"] is None
        assert math.isfinite(row["seconds"]) and row["seconds"] > 0
        coefficients = [value for model in models.values() for f in model.factors for value in f.values]
        profile = row["input"]
        assert profile["factor_entries"] == len(coefficients)
        assert profile["coefficient_bits"] == max(v.bit_length() for v in coefficients)
        assert profile["coefficient_bits_sum"] == sum(max(1, v.bit_length()) for v in coefficients)
        if row["method"] in ("adaptive", "fixed"):
            assert len(row["bounds"]) == len(models)
            bound_map = dict(zip(models, row["bounds"]))
            for key, interval in bound_map.items():
                lo, hi = interval["lower"], interval["upper"]
                assert type(lo) is int and type(hi) is int
                assert 0 <= lo <= true_z[key] <= hi
                intervals += 1
            assert row["expansions"] <= 20000
            assert row["tolerance_met"] == all((b["upper"] - b["lower"]) * 100 <= b["lower"]
                                                 for b in bound_map.values())
            assert row["all_partitions_exact"] == all(b["lower"] == b["upper"] for b in bound_map.values())
            if row["winner"] is not None:
                ratios = {}
                for c in candidates:
                    cb, pb, lb = [bound_map[independent_key(m)] for m in c.models]
                    assert pb["lower"] > 0 and lb["lower"] > 0
                    ratios[c.name] = (Fraction(cb["lower"], pb["upper"] * lb["upper"]),
                                      Fraction(cb["upper"], pb["lower"] * lb["lower"]))
                assert all(name == row["winner"] or ratios[row["winner"]][0] > interval[1]
                           for name, interval in ratios.items())
    with (args.results / "RESULTS.csv").open() as stream:
        summaries = list(csv.DictReader(stream))
    assert len(summaries) == 32
    for summary in summaries:
        group = [r for r in rows if r["case"] == summary["case"] and r["method"] == summary["method"]]
        assert float(summary["median_seconds"]) == statistics.median(r["seconds"] for r in group)
        assert summary["status"] == group[0]["status"]
        assert summary["winner"] == (group[0]["winner"] or "")
    with (args.results / "WITNESSES.csv").open() as stream:
        witnesses = list(csv.DictReader(stream))
    required = sum(2 for r in rows if r["method"] in ("adaptive", "fixed") and r["winner"] is not None)
    assert len(witnesses) == required
    for witness in witnesses:
        numbers = [int(witness[name]) for name in ("aNL", "aNU", "aDL", "aDU", "bNL", "bNU", "bDL", "bDU")]
        al, au, adl, adu, bl, bu, bdl, bdu = numbers
        assert 0 <= al <= au and 0 < adl <= adu and 0 <= bl <= bu and 0 < bdl <= bdu
        assert Fraction(al, adu) > Fraction(bu, bdl)
    print(f"rows=96 source_seal=pass native_states={native_states} intervals={intervals} "
          f"correct_strict_winners={winner_checks} witnesses={len(witnesses)} medians=32 audit=pass")


if __name__ == "__main__":
    main()
