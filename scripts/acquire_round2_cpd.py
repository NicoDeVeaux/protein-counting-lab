"""Acquire and audit preselected author-hosted CPD matrices without inference."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import itertools
import json
import lzma
import math
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/campaign-002"
RAW = DATA / "raw"
MODELS = DATA / "models/cpd"
AUDITS = DATA / "audits"
BETA = 1.0
SENTINEL = "1.0E38"
MAX_NEW_BYTES = 40_000_000
SELECTION = json.loads((DATA / "cpd_selection.json").read_text())
NOW = datetime.now(timezone.utc).isoformat()


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def save_bytes(path, blob):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != blob:
            raise FileExistsError(f"Refusing to overwrite {path}")
    else:
        path.write_bytes(blob)


def save_json(path, value):
    save_bytes(path, (json.dumps(value, indent=2, allow_nan=False) + "\n").encode())


def relative(path):
    return str(path.relative_to(ROOT))


def fetch(item):
    path = RAW / Path(item["relative_url"]).name
    request = urllib.request.Request(item["url"], headers={"User-Agent": "protein-counting-lab academic reproducibility"})
    if path.exists():
        blob = path.read_bytes()
        headers = {}
        status = "cached_original_bytes"
    else:
        with urllib.request.urlopen(request, timeout=90) as response:
            headers = dict(response.headers)
            blob = response.read(MAX_NEW_BYTES + 1)
        if len(blob) > MAX_NEW_BYTES:
            raise ValueError("Per-file download bound exceeded")
        save_bytes(path, blob)
        status = "downloaded"
    return {"source_url": item["url"], "local_path": relative(path), "sha256": digest(blob),
            "bytes": len(blob), "observed_utc": NOW, "status": status, "response_headers": headers}


def label_parts(label):
    position, aa, rotamer = label.rsplit("-", 2)
    int(position)
    int(rotamer)
    return position, aa, rotamer


def source_rows(path):
    with lzma.open(path, "rt", encoding="ascii") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            if line.startswith("Etmp"):
                yield line_number, "Etmp", None, line.split("=", 1)[1].strip(), None
            else:
                fields = line.split()
                if len(fields) != 4 or fields[0] not in ("ROT::BKB", "ROT::SELF", "ROT::ROT"):
                    raise ValueError((line_number, line[:100]))
                yield line_number, fields[0], fields[1], fields[2], fields[3]


def log_value(token):
    if token == SENTINEL:
        return None
    energy = float(token)
    if not math.isfinite(energy):
        raise ValueError("Nonfinite energy")
    return -BETA * energy


def min_fill(domains, edges):
    graph = {v: set() for v, d in enumerate(domains) if d > 1}
    for a, b in edges:
        if a in graph and b in graph:
            graph[a].add(b)
            graph[b].add(a)
    peak = 1
    width = 0
    order = []
    while graph:
        def score(v):
            neighbors = graph[v]
            missing = sum(b not in graph[a] for a, b in itertools.combinations(neighbors, 2))
            return missing, math.prod(domains[x] for x in neighbors | {v}), v
        v = min(graph, key=score)
        neighbors = graph[v]
        peak = max(peak, math.prod(domains[x] for x in neighbors | {v}))
        width = max(width, len(neighbors))
        order.append(v)
        for a, b in itertools.combinations(neighbors, 2):
            graph[a].add(b)
            graph[b].add(a)
        for x in neighbors:
            graph[x].remove(v)
        del graph[v]
    return {"order": order, "induced_width": width, "max_join_entries": peak,
            "max_join_float64_bytes": 8 * peak,
            "interpretation": "Geometry-only dense join estimate; excludes simultaneous buffers, indexes, and Python overhead."}


def structure_census(domains, pair_tokens):
    classes = Counter()
    dependency_edges = []
    separable_edges = []
    for (i, j), tokens in pair_tokens.items():
        di, dj = domains[i], domains[j]
        rows = [tokens[k * dj:(k + 1) * dj] for k in range(di)]
        if all(value == tokens[0] for value in tokens):
            classes["constant"] += 1
        elif all(row == rows[0] for row in rows):
            classes["depends_only_on_second_axis"] += 1
        elif all(all(value == row[0] for value in row) for row in rows):
            classes["depends_only_on_first_axis"] += 1
        else:
            dependency_edges.append((i, j))
            if SENTINEL not in tokens:
                values = [Decimal(token) for token in tokens]
                base = values[0]
                separable = all(values[a * dj + b] + base == values[a * dj] + values[b]
                                for a in range(di) for b in range(dj))
            else:
                separable = False
            if separable:
                classes["additive_separable_decimal_exact"] += 1
            else:
                classes["coupled"] += 1
                separable_edges.append((i, j))
    all_edges = list(pair_tokens)
    return {"pair_factor_classes": dict(classes), "represented_pair_edges": len(all_edges),
            "axis_dependency_edges": len(dependency_edges), "after_exact_decimal_separability_edges": len(separable_edges),
            "represented_min_fill": min_fill(domains, all_edges),
            "axis_dependency_min_fill": min_fill(domains, dependency_edges),
            "decimal_separability_min_fill": min_fill(domains, separable_edges),
            "warning": "Census only: model files retain every pair factor. Decimal-exact source separability may differ after floating-point arithmetic; parent preprocessing must preserve equivalence and audit it."}


def compile_case(item, provenance):
    path = ROOT / provenance["local_path"]
    unary = {"ROT::BKB": {}, "ROT::SELF": {}}
    original_labels = {}
    template = None
    for _, kind, label, token, _ in source_rows(path):
        if kind == "Etmp":
            if template is not None:
                raise ValueError("Repeated template energy")
            template = token
        elif kind != "ROT::ROT":
            if label in unary[kind]:
                raise ValueError("Duplicate unary coordinate")
            unary[kind][label] = token
            if kind == "ROT::BKB":
                position, _, _ = label_parts(label)
                original_labels.setdefault(position, []).append(label)
    if template is None or set(unary["ROT::BKB"]) != set(unary["ROT::SELF"]):
        raise ValueError("Missing template or unmatched unary labels")
    positions = sorted(original_labels, key=int)
    if len(positions) != item["positions"]:
        raise ValueError("Declared position count differs from source")
    selected_aa = {p: label_parts(original_labels[p][0])[1] for p in positions}
    selected_labels = [[label for label in original_labels[p] if label_parts(label)[1] == selected_aa[p]] for p in positions]
    domains = list(map(len, selected_labels))
    selected_index = {label: (i, k) for i, labels in enumerate(selected_labels) for k, label in enumerate(labels)}
    original_domains = [len(original_labels[p]) for p in positions]
    original_index = {label: (i, k) for i, p in enumerate(positions) for k, label in enumerate(original_labels[p])}
    pairs = list(itertools.combinations(range(len(positions)), 2))
    coordinate_bits = {(i, j): bytearray((original_domains[i] * original_domains[j] + 7) // 8) for i, j in pairs}
    coordinate_counts = Counter()
    missing = object()
    pair_tokens = {(i, j): [missing] * (domains[i] * domains[j]) for i, j in pairs}
    counts = Counter()
    sentinels = Counter()
    unequal = Counter()
    selected_sentinels = Counter()
    source_energy_digest = hashlib.sha256()
    source_energy_min = math.inf
    source_energy_max_finite_non_sentinel = -math.inf
    for line_number, kind, label, token, second in source_rows(path):
        counts[kind] += 1
        source_energy_digest.update(f"{kind}\t{label}\t{token}\t{second}\n".encode())
        value = float(token)
        if not math.isfinite(value):
            raise ValueError("Nonfinite source energy")
        source_energy_min = min(source_energy_min, value)
        if token != SENTINEL:
            source_energy_max_finite_non_sentinel = max(source_energy_max_finite_non_sentinel, value)
        else:
            sentinels[kind] += 1
        if second is not None and float(second) != value:
            unequal[kind] += 1
        if kind == "ROT::ROT":
            left, right = label.split("::")
            i, a = original_index[left]
            j, b = original_index[right]
            if i == j:
                raise ValueError("Same-position pair")
            if i > j:
                i, j, a, b = j, i, b, a
            index = a * original_domains[j] + b
            bits = coordinate_bits[i, j]
            if bits[index // 8] & (1 << (index % 8)):
                raise ValueError(("Duplicate pair coordinate", line_number))
            bits[index // 8] |= 1 << (index % 8)
            coordinate_counts[i, j] += 1
            if left in selected_index and right in selected_index:
                si, sa = selected_index[left]
                sj, sb = selected_index[right]
                if si > sj:
                    si, sj, sa, sb = sj, si, sb, sa
                pair_tokens[si, sj][sa * domains[sj] + sb] = token
                if token == SENTINEL:
                    selected_sentinels[kind] += 1
        elif label in selected_index and token == SENTINEL:
            selected_sentinels[kind] += 1
    expected_pairs = sum(original_domains[i] * original_domains[j] for i, j in pairs)
    if counts["ROT::ROT"] != expected_pairs or any(coordinate_counts[i, j] != original_domains[i] * original_domains[j] for i, j in pairs):
        raise ValueError("Incomplete source pair grid; no implicit zero-energy assumption allowed")
    if any(token is missing for tokens in pair_tokens.values() for token in tokens):
        raise ValueError("Incomplete selected pair table")
    factors = [{"scope": [i], "log_values": [log_value(unary["ROT::BKB"][label]) for label in labels]}
               for i, labels in enumerate(selected_labels)]
    factors += [{"scope": [i, j], "log_values": [log_value(token) for token in pair_tokens[i, j]]} for i, j in pairs]
    model_id = item["pdb_id"] + "__cpd_source_first_aa__beta1"
    model = {"schema_version": 1, "model_id": model_id, "kind": "published_computational_model",
             "domains": domains, "factors": factors, "constant_log_weight": log_value(template),
             "metadata": {"source_family": "Traore et al. 2013 author-hosted OSPREY CPD matrices",
                          "source_url": item["url"], "source_matrix_sha256": provenance["sha256"],
                          "pdb_id": item["pdb_id"], "state": "single_structure_design_energy",
                          "target": "Z = sum_rotamers exp(-beta * (Etmp + sum ROT::BKB + sum ROT::ROT)), restricted to declared fixed AA sequence",
                          "beta": BETA, "beta_convention": "Explicit dimensionless numerical benchmark; no physical temperature asserted.",
                          "sequence_policy": "First AA encountered in source ROT::BKB records at each position, selected before inference; arbitrary declared sequence, not asserted native or optimal.",
                          "source_position_ids": positions, "source_aa_assignment": selected_aa,
                          "source_rotamer_labels": selected_labels,
                          "coordinate_convention": "Variables in numeric residue-position order; domain values in source BKB encounter order within selected AA; pair scopes ascending, second variable varies fastest (C order).",
                          "energy_convention": "First source energy column. BKB already contains unary energy in the author converter; SELF is archived for audit, not added. Etmp retained; no SELF reference subtraction, rounding, saturation, or rescaling.",
                          "hard_zero_convention": "Only exact source token 1.0E38 becomes null log weight, following the author's explicit steric-clash sentinel. All other finite source energies retained as logs; no positive-weight pruning.",
                          "limitations": ["Single-state published computational design model, not measured affinity and not a paired binding ensemble.", "Source-first AA is not a biological sequence recommendation.", "No sequence optimization, affinity prediction, physical-temperature calibration, or inference has been performed."]}}
    model_path = MODELS / (model_id + ".json")
    save_json(model_path, model)
    reread = json.loads(model_path.read_text())
    factor_lookup = {tuple(f["scope"]): f["log_values"] for f in reread["factors"]}
    audit_count = Counter()
    for _, kind, label, token, _ in source_rows(path):
        if kind == "Etmp":
            assert reread["constant_log_weight"] == log_value(token)
            audit_count[kind] += 1
        elif kind == "ROT::BKB" and label in selected_index:
            i, a = selected_index[label]
            assert factor_lookup[i,][a] == log_value(token)
            audit_count[kind] += 1
        elif kind == "ROT::ROT":
            left, right = label.split("::")
            if left in selected_index and right in selected_index:
                i, a = selected_index[left]
                j, b = selected_index[right]
                if i > j:
                    i, j, a, b = j, i, b, a
                assert factor_lookup[i, j][a * domains[j] + b] == log_value(token)
                audit_count[kind] += 1
    assert audit_count["ROT::BKB"] == sum(domains)
    assert audit_count["ROT::ROT"] == sum(domains[i] * domains[j] for i, j in pairs)
    census = structure_census(domains, pair_tokens)
    audit = {"model_id": model_id, "source_matrix": provenance,
             "source_row_counts": dict(counts), "source_sentinel_counts": dict(sentinels),
             "source_first_second_energy_column_unequal_counts": dict(unequal),
             "source_first_energy_min": source_energy_min,
             "source_first_energy_max_excluding_literal_sentinel": source_energy_max_finite_non_sentinel,
             "normalized_all_source_energy_records_sha256": source_energy_digest.hexdigest(),
             "original_domains": original_domains, "original_position_ids": positions,
             "full_pair_coordinate_audit": {"expected_entries": expected_pairs, "observed_entries": counts["ROT::ROT"],
                                             "duplicate_coordinates": 0, "missing_coordinates": 0,
                                             "method": "Every original pair coordinate checked using position-indexed bitsets; pair grids are complete."},
             "selected_sentinel_counts": dict(selected_sentinels),
             "selected_full_entry_reread_audit": {"matched": dict(audit_count), "mismatches": 0,
                                                  "method": "Independent third streaming read compares every selected source BKB/pair entry and Etmp against parsed serialized model."},
             "selected_SELF_audit_only": [[unary["ROT::SELF"][label] for label in labels] for labels in selected_labels],
             "selected_BKB_energy_tokens": [[unary["ROT::BKB"][label] for label in labels] for labels in selected_labels],
             "template_energy_token": template,
             "reference_offset_if_author_minSELF_subtraction_were_applied": str(sum(min(Decimal(unary["ROT::SELF"][label]) for label in labels) for labels in selected_labels)),
             "structure_census": census}
    audit_path = AUDITS / (model_id + ".json")
    save_json(audit_path, audit)
    record = {"model_id": model_id, "path": relative(model_path), "sha256": digest(model_path.read_bytes()),
              "audit_path": relative(audit_path), "audit_sha256": digest(audit_path.read_bytes()),
              "pdb_id": item["pdb_id"], "domains": domains, "n_variables": len(domains),
              "n_nontrivial": sum(d > 1 for d in domains), "configuration_count": math.prod(domains),
              "unary_supported_values_per_variable": [sum(token != SENTINEL for token in row) for row in audit["selected_BKB_energy_tokens"]],
              "factor_count": len(factors), "table_entries": sum(len(f["log_values"]) for f in factors),
              "zero_entries": sum(value is None for f in factors for value in f["log_values"]),
              "source_matrix": provenance, "sentinel_counts": dict(selected_sentinels), "structure_census": census}
    print(json.dumps({k: record[k] for k in ("model_id", "n_variables", "n_nontrivial", "domains", "configuration_count", "zero_entries")}), flush=True)
    return record


def main():
    if (DATA / "cpd_manifest.json").exists():
        raise FileExistsError("Campaign manifest already exists; do not overwrite frozen preparation.")
    pending = [item for item in SELECTION["selected"] if not (RAW / Path(item["relative_url"]).name).exists()]
    with ThreadPoolExecutor(max_workers=3) as executor:
        downloads = list(executor.map(fetch, SELECTION["selected"]))
    if sum(d["bytes"] for d in downloads if d["status"] == "downloaded") > MAX_NEW_BYTES:
        raise ValueError("Aggregate new matrix download bound exceeded")
    save_json(DATA / "cpd_downloads.json", {"observed_utc": NOW, "new_matrix_limit_bytes": MAX_NEW_BYTES, "downloads": downloads})
    records = [compile_case(item, provenance) for item, provenance in zip(SELECTION["selected"], downloads)]
    code_files = [DATA / "source_code/mat2wcsp.pl", DATA / "source_code/RotamerSearch.java"]
    manifest = {"schema_version": 1, "created_utc": NOW, "work_classification": "poc",
                "selection_rule": SELECTION["selection_rule"], "selection_sha256": digest((DATA / "cpd_selection.json").read_bytes()),
                "target_semantics": "Six source-first fixed-AA single-state conformational partition sums from published computational protein design matrices; not binding affinity ensembles.",
                "beta": BETA, "temperature_kelvin": None,
                "hard_zero_rule": "Exact source token 1.0E38 only; author steric-clash convention.",
                "source_code": [{"path": relative(p), "sha256": digest(p.read_bytes())} for p in code_files],
                "acquisition_script": {"path": relative(Path(__file__)), "sha256": digest(Path(__file__).read_bytes())},
                "downloads": downloads, "cases": records,
                "inference_executed": False}
    save_json(DATA / "cpd_manifest.json", manifest)


if __name__ == "__main__":
    main()
