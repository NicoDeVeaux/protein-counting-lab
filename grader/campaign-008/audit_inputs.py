#!/usr/bin/env python3
"""Audit the external cohort without reading or calculating its model counts."""

import argparse
import hashlib
import json
import lzma
from pathlib import Path
import random
import re
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.external_count8.cnf import parse_dimacs as implementation_parse, to_model
from oracle import exact_count, expected_factor_tables, normalized_clauses, parse_dimacs


def sha(data):
    return hashlib.sha256(data).hexdigest()


def independent_inventory(cnf):
    clauses = normalized_clauses(cnf)
    arities = [len({abs(v) for v in clause}) for clause in clauses]
    maximum = max(arities, default=0)
    return {"variables": cnf.n, "clauses": len(cnf.clauses),
            "nontrivial_clauses": len(clauses), "max_clause_arity": maximum,
            "factor_entries": sum(1 << n for n in arities) if maximum <= 20 else None}


def reasons(inventory):
    result = []
    for field, cap, reason in (("variables", 256, "variables_above_256"),
                               ("clauses", 2000, "clauses_above_2000"),
                               ("max_clause_arity", 6, "clause_arity_above_6")):
        if inventory[field] > cap:
            result.append(reason)
    if inventory["factor_entries"] is None or inventory["factor_entries"] > 50000:
        result.append("factor_entries_above_50000")
    return result


def tiny_controls():
    cases = [("p cnf 0 0\n", 1), ("p cnf 0 1\n0\n", 0),
             ("p cnf 3 1\n1 0\n", 4),
             ("p cnf 2 2\n1 1 0\n-1 2 0\n", 1),
             ("p cnf 2 1\n1 -1 0\n", 4),
             ("p cnf 3 2\n1 -2\n0\n1 -2 0\n", 6),
             ("p cnf 2 2\n1 0\n-1 0\n", 0),
             ("p cnf 5 0\n", 32)]
    for text, expected in cases:
        independent = parse_dimacs(text)
        assert exact_count(independent) == expected
        model = to_model(implementation_parse(text))
        assert model.n == independent.n
        assert tuple((f.scope, f.values) for f in model.key[1]) == expected_factor_tables(independent)
    bad = ["", "p cnf -1 0\n", "p cnf 1 1\n2 0\n", "p cnf 1 1\n1\n",
           "p cnf 1 0\n0\n", "p cnf 1 0\np cnf 1 0\n",
           "c t wmc\np cnf 1 0\n", "c p weight 1 0.5 0\np cnf 1 0\n"]
    for text in bad:
        for parser in (parse_dimacs, implementation_parse):
            try:
                parser(text)
            except ValueError:
                pass
            else:
                raise AssertionError("malformed tiny control accepted")
    return len(cases), len(bad)


def audit(archive, cohort):
    manifest = json.loads((cohort / "COHORT.json").read_text())
    assert sha(archive.read_bytes()) == manifest["source_sha256"]
    catalogue = {r["member"]: r for r in manifest["catalogue"]}
    assert len(catalogue) == len(manifest["catalogue"]) == 100
    selected = {r["member"]: r for r in manifest["selected"]}
    eligible = []
    checked = selected_tables = 0
    cap_headers = []
    with tarfile.open(archive) as source:
        members = [m for m in source.getmembers() if m.isfile()]
        assert len(members) == 100
        assert {m.name for m in members} == set(catalogue)
        for member in members:
            record = catalogue[member.name]
            compressed = source.extractfile(member).read()
            assert len(compressed) == record["compressed_bytes"]
            assert sha(compressed) == record["compressed_sha256"]
            decoder = lzma.LZMADecompressor()
            raw = decoder.decompress(compressed, max_length=8 * 1024 * 1024 + 1)
            if not decoder.eof or len(raw) > 8 * 1024 * 1024:
                # This operational read cap must not change protocol eligibility.
                header = re.search(rb"^p cnf\s+(\d+)\s+(\d+)\s*$", raw[:65536], re.M)
                assert header, "cannot establish static exclusion before decompression cap"
                n, clauses = map(int, header.groups())
                assert n > 256 or clauses > 2000, "read cap might exclude an eligible source"
                assert record["exclusions"] == ["uncompressed_bytes_above_8MiB"]
                cap_headers.append({"member": member.name, "variables": n, "clauses": clauses})
                continue
            assert len(raw) == record["bytes"] and sha(raw) == record["sha256"]
            independent = parse_dimacs(raw.decode("ascii"))
            inventory = independent_inventory(independent)
            assert all(record[key] == value for key, value in inventory.items())
            assert record["exclusions"] == reasons(inventory)
            checked += 1
            if not reasons(inventory):
                eligible.append(member.name)
            if member.name in selected:
                row = selected[member.name]
                assert row["sha256"] == sha(raw)
                assert (cohort / row["local_filename"]).read_bytes() == raw
                model = to_model(implementation_parse(raw.decode("ascii")))
                assert model.n == independent.n
                actual = tuple((f.scope, f.values) for f in model.key[1])
                expected = expected_factor_tables(independent)
                assert actual == expected, "selected clause/table translation mismatch"
                selected_tables += len(expected)
    chosen = sorted(eligible)
    random.Random(8008).shuffle(chosen)
    assert len(chosen) == manifest["eligible_count"] == 24
    assert [r["member"] for r in manifest["selected"]] == chosen[:12]
    assert manifest["queries"] == [[chosen[i], chosen[i + 1]] for i in range(0, 12, 2)]
    valid, invalid = tiny_controls()
    return {"catalogue_members": len(catalogue), "full_metadata_checks": checked,
            "capped_headers_statically_ineligible": cap_headers,
            "eligible": len(eligible), "selected": 12, "queries": 6,
            "selected_factor_tables": selected_tables,
            "tiny_valid_controls": valid, "tiny_invalid_controls": invalid,
            "external_counts_computed": 0, "audit": "pass"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("cohort", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.archive, args.cohort)))


if __name__ == "__main__":
    main()
