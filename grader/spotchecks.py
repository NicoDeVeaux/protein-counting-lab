"""High-precision direct sums and independent supplement extraction."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import re
import zipfile

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "grader"


def load(path):
    return json.loads((ROOT / path).read_text())


def parse_tokens(blob):
    it = iter(blob.decode().split())
    assert next(it) == "MARKOV"
    n = int(next(it))
    dims = [int(next(it)) for _ in range(n)]
    scopes = [[int(next(it)) for _ in range(int(next(it)))] for _ in range(int(next(it)))]
    tables = [[next(it) for _ in range(int(next(it)))] for _ in scopes]
    assert next(it, None) is None
    return dims, scopes, tables


def index(scope, dims, assignment):
    result = 0
    for v in scope:
        result = result * dims[v] + assignment.get(v, 0)
    return result


def main():
    cohort = load("data/uai23_manifest.json")
    chosen = {s["model_id"] for c in cohort["cases"] for s in c["states"] if s["configuration_count"] <= 1000}
    complex_spot = min((s for c in cohort["cases"] for s in c["states"] if s["model_id"].endswith("__complex") and s["configuration_count"] <= 30000), key=lambda s: s["model_id"])
    chosen.add(complex_spot["model_id"])
    decimal_checks, nonzero_to_zero = [], []
    with localcontext() as ctx:
        ctx.prec = 80
        for case in cohort["cases"]:
            with zipfile.ZipFile(ROOT / case["local_path"]) as archive:
                name = next(n for n in archive.namelist() if n.endswith(".uai"))
                dims, scopes, tables = parse_tokens(archive.read(name))
            lexical_underflows = sum(Decimal(s) != 0 and float(s) == 0 for t in tables for s in t)
            nonzero_to_zero.append({"case_id": case["case_id"], "nonzero_literal_to_float_zero": lexical_underflows})
            for state in case["states"]:
                if state["model_id"] not in chosen:
                    continue
                model = load(state["path"])
                meta = model["metadata"]
                vars_ = meta["source_variable_ids"]
                domains = [meta["source_domain_indices"][str(v)] for v in vars_]
                selected = meta["source_factor_indices"]
                factors = []
                for j, i in enumerate(selected):
                    scope = scopes[i]
                    active = [v for v in scope if v in vars_]
                    look, converted_look = {}, {}
                    for flat, values in enumerate(itertools.product(*(meta["source_domain_indices"][str(v)] for v in active))):
                        loc = dict(zip(active, values))
                        token = tables[i][index(scope, dims, loc)]
                        look[values] = Decimal.from_float(float(token))
                        stored = model["factors"][j]["log_values"][flat]
                        converted_look[values] = Decimal(0) if stored is None else Decimal.from_float(stored).exp()
                    factors.append((active, look, converted_look))
                total, converted_total = Decimal(0), Decimal(0)
                for values in itertools.product(*domains):
                    assignment = dict(zip(vars_, values))
                    weight, converted_weight = Decimal(1), Decimal(1)
                    for active, lookup, converted_lookup in factors:
                        key = tuple(assignment[v] for v in active)
                        weight *= lookup[key]
                        converted_weight *= converted_lookup[key]
                    total += weight
                    converted_total += converted_weight
                logz = total.ln()
                converted_logz = converted_total.ln()
                decimal_checks.append({"model_id": state["model_id"], "states": state["configuration_count"], "precision_decimal_digits": 80, "log_z": str(logz), "z": str(total), "converted_log_z": str(converted_logz), "conversion_delta_log_z": str(converted_logz - logz), "input_semantics": "Raw reference uses exact Decimal representation of binary64 values parsed from original UAI tokens. Converted reference uses exp of exact Decimal representation of stored binary64 log factors. Both use 80-digit product/sum/log arithmetic."})
    trials = [json.loads(line) for line in (ROOT / "runs/campaign-001/trials.jsonl").read_text().splitlines()]
    refs = {x["model_id"]: Decimal(x["log_z"]) for x in decimal_checks}
    converted_refs = {x["model_id"]: Decimal(x["converted_log_z"]) for x in decimal_checks}
    comparison = []
    for row in trials:
        if row["model_id"] not in refs:
            continue
        r = row["result"]
        ref = refs[row["model_id"]]
        if row["method"] == "bounded":
            lo, hi = Decimal.from_float(r["log_z_lower"]), Decimal.from_float(r["log_z_upper"])
            cref = converted_refs[row["model_id"]]
            comparison.append({"trial_id": row["trial_id"], "method": row["method"], "strict_contains_80digit_reference": lo <= ref <= hi, "strict_contains_converted_80digit_reference": lo <= cref <= hi, "signed_lower_error": str(lo - ref), "signed_upper_error": str(hi - ref), "signed_converted_lower_error": str(lo - cref), "signed_converted_upper_error": str(hi - cref)})
        else:
            comparison.append({"trial_id": row["trial_id"], "method": row["method"], "error_80digit": str(Decimal.from_float(r["log_z"]) - ref)})
    pdf_path = "data/raw/ayyildiz2025/JCC-46-0-s001.pdf"
    pdf = PdfReader(ROOT / pdf_path)
    parsed, pocket, sequence = [], None, None
    page_text = []
    for i in [2, 3, 4]:
        text = pdf.pages[i].extract_text()
        page_text.append({"page_1based": i + 1, "text": text})
        for line in text.splitlines():
            header = re.search(r"(Arg|Tyr|Trp|Ile|His)-binder\s*\(([A-Z]+)\)", line)
            if header:
                pocket, sequence = header.groups()
            match = re.fullmatch(r"\s*([A-Z])\s+([0-9]+(?:\.[0-9]+)?)\s+([0-9]+(?:\.[0-9]+)?|-)\s*", line)
            if match:
                residue, kd, error = match.groups()
                parsed.append({"record_id": pocket + "_" + residue, "pocket_sequence": sequence, "kd_nm": float(kd), "reported_error_nm": None if error == "-" else float(error), "source_page_1based": i + 1})
    labels = load("data/ayyildiz2025_affinities.json")
    normalized = {r["record_id"]: r for r in labels["records"]}
    assert len(parsed) == len(normalized) == 63
    for row in parsed:
        assert all(normalized[row["record_id"]][k] == v for k, v in row.items())
    package_files = {}
    for relative in ["data/raw/ayyildiz2025/supplementaryFiles.zip", "data/raw/ayyildiz2025/JCC-46-0-s002.zip"]:
        with zipfile.ZipFile(ROOT / relative) as archive:
            assert archive.testzip() is None
            package_files[relative] = archive.namelist()
    audit = load("grader/audit_results.json")
    verified = {}
    for name, hashes in [("campaign", load("runs/campaign-001/manifest.json")["source_snapshot"])]:
        verified[name] = all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in hashes.items())
    for relative in ["runs/campaign-001/manifest.json", "runs/eth-schedule-001/manifest.json"]:
        expected = (ROOT / relative.replace(".json", ".sha256")).read_text().split()[0]
        verified[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    source = (ROOT / "experiments/eth_schedule/source/main_full_version.tex").read_text()
    start = source.index(r"\begin{lemma}\label{lem:incidence-parameters}")
    transcription = source[start:source.index(r"\end{lemma}", start) + len(r"\end{lemma}")]
    save = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(), "selection_after_exposure": "All state models with <=1000 configurations plus lexicographically first complex with <=30000 configurations; diagnostic, not a prospective experiment.", "decimal_checks": decimal_checks, "trial_comparisons": comparison, "nonzero_literal_to_float_zero": nonzero_to_zero, "supplement": {"parsed_records": parsed, "matches_all_normalized_fields": True, "missing_error_count": sum(x["reported_error_nm"] is None for x in parsed), "pypdf_page_text": page_text, "package_members": package_files}, "manifest_source_snapshot_checks": verified, "eth_parameter_source_excerpt": transcription}
    (OUT / "spotcheck_results.json").write_text(json.dumps(save, indent=2) + "\n")
    print(json.dumps({"decimal_models": len(decimal_checks), "decimal_states_enumerated": sum(x["states"] for x in decimal_checks), "labels_independently_matched": len(parsed), "nonzero_literal_underflows": sum(x["nonzero_literal_to_float_zero"] for x in nonzero_to_zero), "integrity_checks": verified, "high_precision_bound_noncontainment": sum(x.get("strict_contains_80digit_reference") is False for x in comparison)}))


if __name__ == "__main__":
    main()
