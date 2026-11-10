"""Prepare the prospective structure study; this script never performs timed inference."""

from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import time

import mpmath as mp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.inference import load_model, model_from_dict
from experiments.structure import model_to_dict, simplify_model, structure_summary

OUT = ROOT / "prepared/campaign-002"


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")
    return artifact(path)


def artifact(path):
    path = Path(path)
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def structure(model):
    s = structure_summary(model)
    n, e, c = s["variables"], s["represented_pair_edges"], s["connected_components"]
    largest = int(s["predicted_peak_table_bytes_float64"])
    if largest < 2**20:
        memory_bin = "lt1MiB"
    elif largest <= 128 * 2**20:
        memory_bin = "1to128MiB"
    elif largest <= 512 * 2**20:
        memory_bin = "gt128to512MiB"
    else:
        memory_bin = "gt512MiB"
    q = max(model.domains, default=1)
    return {"variables": n, "nontrivial_variables": sum(d > 1 for d in model.domains),
            "domain_cardinalities": list(model.domains), "factor_scopes": [list(f.scope) for f in model.factors],
            "factor_entries": [int(f.values.size) for f in model.factors], "components": c,
            "primal_edges": e, "primal_density": 2 * e / (n * (n - 1)) if n > 1 else 0,
            "graph_class": "edgeless" if e == 0 else ("pairwise_forest" if e == n-c else "pairwise_cyclic"),
            "max_domain_bin": "le16" if q <= 16 else ("17to64" if q <= 64 else "gt64"),
            "variable_bin": "le8" if n <= 8 else ("9to32" if n <= 32 else "gt32"),
            "elimination_order": s["min_fill_order"], "order_heuristic": "deterministic min-fill, log-domain-size tie break",
            "induced_width": s["predicted_induced_width"],
            "predicted_largest_intermediate_entries": int(s["predicted_peak_table_entries"]),
            "predicted_largest_intermediate_bytes": largest,
            "predicted_workspace_bytes": 2 * largest + sum(f.values.nbytes for f in model.factors),
            "workspace_scope": "Conservative two largest numeric arrays plus input factor arrays; excludes parser/Python/native library memory and is not an RSS prediction.",
            "memory_bin": memory_bin, "log_joint_configurations": sum(math.log(d) for d in model.domains)}


def control(family, n, q, name=None):
    if family == "independent":
        edges = []
    elif family == "chain":
        edges = [(i, i+1) for i in range(n-1)]
    elif family == "cycle":
        edges = [(i, i+1) for i in range(n-1)] + [(0, n-1)]
    elif family.startswith("grid"):
        width = int(family[4:])
        edges = [(r*width+c, r*width+c+1) for r in range(width) for c in range(width-1)]
        edges += [(r*width+c, (r+1)*width+c) for r in range(width-1) for c in range(width)]
    else:
        edges = list(itertools.combinations(range(n), 2))
    factors = []
    if family == "independent":
        factors = [{"scope": [i], "log_values": [-float(a) for a in range(q)]} for i in range(n)]
    for i, j in edges:
        values = [[0.0 if a == b else -1.0 for b in range(q)] for a in range(q)]
        if family == "separable":
            values = [[-float(a+b) for b in range(q)] for a in range(q)]
        elif family == "constant":
            values = [[0.0] * q for _ in range(q)]
        factors.append({"scope": [i, j], "log_values": values})
    model_id = name or f"synthetic-{family}-n{n}-q{q}"
    return {"schema_version": 1, "model_id": model_id, "kind": "synthetic_control", "domains": [q] * n,
            "factors": factors, "metadata": {"family": family, "q": q, "n": n,
                 "generator": "scripts/prepare_round2.py/control-v1", "seed": 2026110602,
                 "interpretation": "Deterministic mechanism/resource control, not a protein or an experimental measurement. Uniform Potts symmetry is deliberate; no generic hardness claim."}}


def analytic_reference(data):
    mp.mp.dps = 90
    family, n, q = (data["metadata"][k] for k in ("family", "n", "q"))
    x = mp.exp(-1)
    if family == "independent":
        log_z = n * mp.log(sum(mp.exp(-a) for a in range(q)))
    elif family == "chain":
        log_z = mp.log(q) + (n-1) * mp.log(1+(q-1)*x)
    elif family == "cycle":
        log_z = mp.log((1+(q-1)*x)**n + (q-1)*(1-x)**n)
    elif family == "constant":
        log_z = n * mp.log(q)
    elif family == "separable":
        log_z = n * mp.log(sum(mp.exp(-(n-1)*a) for a in range(q)))
    elif family == "clique":
        def compositions(total, parts):
            if parts == 1:
                yield (total,)
            else:
                for first in range(total+1):
                    for rest in compositions(total-first, parts-1):
                        yield (first,) + rest
        z = mp.mpf(0)
        for counts in compositions(n, q):
            multiplicity = mp.factorial(n) / math.prod(math.factorial(c) for c in counts)
            unequal = (n*n - sum(c*c for c in counts)) // 2
            z += multiplicity * mp.exp(-unequal)
        log_z = mp.log(z)
    elif family == "grid4":
        width = 4
        rows = list(itertools.product(range(q), repeat=width))
        own = [mp.exp(-sum(row[i] != row[i+1] for i in range(width-1))) for row in rows]
        transfer = [[mp.exp(-sum(a != b for a, b in zip(left, right))) for right in rows] for left in rows]
        mass = own.copy()
        for _ in range(width-1):
            mass = [own[j] * sum(mass[i] * transfer[i][j] for i in range(len(rows))) for j in range(len(rows))]
        log_z = mp.log(sum(mass))
    else:
        return None
    return {"reference_id": "analytic90/" + data["model_id"], "log_z": str(log_z),
            "reference_uncertainty": 1e-70, "uncertainty": 1e-70,
            "kind": "90-decimal-digit analytic closed form or independent row transfer",
            "precision_digits": 90, "assurance": "High-precision numerical reference, not a directed-rounding interval certificate."}


def prepare_one(path, cohort, source_id, evidence, refs, models, conversion_checks):
    started = time.perf_counter()
    original = load_model(path)
    before = structure(original)
    reduced, changes = simplify_model(original)
    after = structure(reduced)
    pre_seconds = time.perf_counter() - started
    evidence_path = OUT / "algebra" / (original.model_id + ".json")
    proof = write(evidence_path, {"model_id": original.model_id, "source": artifact(path),
        "proof_method": "Constants/identical axes by exact binary64 equality; additive splits checked entrywise as exact Fraction(binary64) identities. All domains retained. No tolerance-based reductions.",
        "transformations": changes, "before": before, "after": after, "preparation_seconds": pre_seconds})
    representations = [{"representation_id": "original", "files": [artifact(path)], "structure": before,
                         "simplification": "unchanged", "target_relation": "original stored-log target",
                         "evidence": evidence + [proof], "preparation_seconds": 0.0}]
    changed_edges = before["primal_edges"] != after["primal_edges"]
    if changed_edges:
        target = OUT / "models" / (original.model_id + "__simplified.json")
        derived = write(target, model_to_dict(reduced))
        kinds = {c["kind"] for c in changes}
        representations.append({"representation_id": "simplified", "files": [derived], "structure": after,
            "simplification": "multiple_exact" if len(kinds)>1 else ("exact_separable" if "exact_binary_rational_additive_split" in kinds else "exact_constant_scope"),
            "target_relation": "same ideal-real sum of stored binary-rational log factors by checked exact identities; usual downstream floating arithmetic remains numerical",
            "evidence": evidence + [proof], "preparation_seconds": pre_seconds})
    models.append({"model_id": original.model_id, "cohort": cohort, "source_id": source_id,
        "fixed_sequence_and_conditioning": json.dumps(original.metadata.get("sequence", original.metadata.get("source_aa_assignment", original.metadata.get("selected_amino_acids", {})))),
        "preparation_status": "prepared; no timed inference in this preparation step",
        "source_semantics": original.metadata.get("factor_convention", original.metadata.get("target_semantics", original.metadata.get("target", "Stored finite log factors plus explicit hard zeros; synthetic controls have no molecular interpretation."))) + " " + original.metadata.get("beta_convention", ""),
        "conversion_checks": conversion_checks, "representations": representations})


def main():
    if OUT.exists():
        raise FileExistsError("Do not overwrite prepared campaign artifacts")
    OUT.mkdir(parents=True)
    prior = json.loads((ROOT / "data/uai23_manifest.json").read_text())
    new = json.loads((ROOT / "data/campaign-002/cpd_manifest.json").read_text())
    references, models, baseline_mapping = {}, [], []
    old_results = json.loads((ROOT / "runs/campaign-001/summary.json").read_text())
    high_precision = json.loads((ROOT / "grader/spotcheck_results.json").read_text())
    for observation in old_results["observations"]:
        references[observation["model_id"]] = {"reference_id": "campaign001-independently-audited/"+observation["model_id"],
            "log_z": observation["log_z"]["eliminate"], "reference_uncertainty": 1e-10, "uncertainty": 1e-10,
            "kind": "Historical raw-weight independent enumeration audit; not new confirmatory evidence."}
    for observation in high_precision["decimal_checks"]:
        references[observation["model_id"]] = {"reference_id": "campaign001-Decimal80/"+observation["model_id"],
            "log_z": observation["converted_log_z"], "reference_uncertainty": 1e-65, "uncertainty": 1e-65,
            "kind": "Historical 80-digit stored-log-model reference, independently computed."}
    check = artifact(ROOT / "data/uai23_preparation_checks.json")
    for case in prior["cases"]:
        for state in case["states"]:
            prepare_one(ROOT / state["path"], "original_42", "uai23-prior", [check], references, models, check)
            baseline_mapping.append({"model_id": state["model_id"], "original_path": state["path"], "sha256": state["sha256"]})
    new_check_path = ROOT / new.get("validation_artifact", "data/campaign-002/cpd_validation.json")
    if not new_check_path.exists():
        new_check_path = ROOT / "data/campaign-002/cpd_manifest.json"
    new_check = artifact(new_check_path)
    for case in new["cases"]:
        prepare_one(ROOT / case["path"], "published_protein_extension", "author-cpd", [new_check], references, models, new_check)
    control_specs = [("independent",64,4), ("chain",32,4), ("chain",96,4), ("cycle",48,4),
                     ("grid4",16,3), ("grid8",64,3), ("clique",10,4), ("clique",12,4),
                     ("clique",14,4), ("separable",32,4), ("constant",48,4)]
    control_check = write(OUT / "controls.json", {"specifications": control_specs, "generator": artifact(Path(__file__)),
        "purpose": "Fill >8-variable forest/cycle/grid and exact-algebraic structural gaps; no protein scaling inference.",
        "reference_policy": "90-digit closed forms, clique occupancy enumeration, or independent row-transfer for grid4; grid8 has no adequate numerical oracle in this initial bounded study and remains unverified_accuracy if completed."})
    for family, n, q in control_specs:
        data = control(family, n, q)
        path = OUT / "controls" / (data["model_id"] + ".json")
        write(path, data)
        reference = analytic_reference(data)
        if reference:
            references[data["model_id"]] = reference
        prepare_one(path, "synthetic_measured", "deterministic-controls", [control_check], references, models, control_check)
    mapping = write(OUT / "baseline42_mapping.json", baseline_mapping)
    ledger = write(OUT / "preparation_ledger.json", {"recorded_at": datetime.now(timezone.utc).isoformat(),
        "new_source_selection": new["selection_rule"], "all_source_attempts": "data/campaign-002/preparation_ledger.json",
        "attempts": [{"model_id": m["model_id"], "status": m["preparation_status"]} for m in models],
        "prior_exposure": "Prior campaign's42models and outcomes are known adaptive evidence; all42 retained unchanged. Newsource selection and reductions use static input information only. No new timed protein inference preceded this catalog.",
        "simplification_selection_rule": "Retain original representation for every model; additionally measure exactly simplified representation iff represented pair-edge count decreases. Nonstructural changes are documented but do not create duplicate timing cells."})
    catalog = {"schema_version": 1, "prepared_at": datetime.now(timezone.utc).isoformat(), "models": models,
        "references": references, "preparation_ledger": ledger,
        "source_inventory": [{"source_id": "uai23-prior", "provenance": "Pinned published UAI cohort from prior study; numeric outcomes known, all42 preserved.", "files": [artifact(ROOT/"data/uai23_manifest.json"), check]},
                             {"source_id": "author-cpd", "provenance": "Author-hosted OSPREY energy matrices; six smallest listed position counts chosen before timed inference, fixed source-first AA and declared beta=1 numerical energy target.", "files": [artifact(ROOT/"data/campaign-002/cpd_manifest.json"), new_check]},
                             {"source_id": "deterministic-controls", "provenance": "Synthetic structural mechanism controls, not molecular or measured data.", "files": [control_check]}],
        "selection_rule": {"rule": "Unchanged prior42 plus six statically selected larger author models and eleven prespecified synthetic structural controls; no solver-outcome selection.",
            "baseline_42_mapping": mapping, "coverage_gaps": ["No physical affinity validation; largerauthorbeta=1 is a declared numerical energy target.", "No domain>64 measured family unless newauthorinputs supply one.", "Synthetic uniformPotts/separable controls test mechanisms and resource use, not generic graph hardness.", "No independent oracle for grid8 or potentially intractable newauthorpartition values in this bounded study; completed results without adequate reference remain unverified."],
            "intended_cells": sorted({(r["structure"]["graph_class"],r["structure"]["memory_bin"],r["structure"]["variable_bin"],r["structure"]["max_domain_bin"]) for m in models for r in m["representations"]})},
        "exposure_ledger": [{"event": "campaign001", "exposure": "Prior artifacts, outputs, and independent critique known.", "effect_on_selection": "Motivates larger/resource/structure study; preserves baseline42 and uses static rules for newcases."},
                            {"event": "premeasurement-preparation", "exposure": "Data conversion, exact rational factor reductions, graph/memory estimates, adapter unit controls, and analytic reference evaluation only.", "effect_on_selection": "No timed protein inference or outcome-conditioned exclusions."}]}
    write(OUT / "catalog.json", catalog)
    print(json.dumps({"catalog": str(OUT/"catalog.json"), "models": len(models), "representations": sum(len(m["representations"]) for m in models), "references": len(references)}))


if __name__ == "__main__":
    main()
