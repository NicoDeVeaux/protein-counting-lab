"""Inspect pilot archive metadata without conditioning or evaluating any partition sum."""

from collections import Counter
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("metadata_inspection.json")


def named(text, name):
    match = re.search(r"^" + re.escape(name) + r"\s*$", text, re.M)
    if match is None:
        raise ValueError(name)
    return json.JSONDecoder().raw_decode(text[match.end():].lstrip())[0]


def inspect():
    manifest_path = ROOT / "data/uai23_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    case = next(case for case in manifest["cases"] if case["case_id"].startswith("2rfe_prepped_00012_"))
    archive_path = ROOT / case["local_path"]
    sha = lambda data: hashlib.sha256(data).hexdigest()
    assert sha(archive_path.read_bytes()) == case["sha256"]
    with zipfile.ZipFile(archive_path) as archive:
        summary_bytes = archive.read("uai_conversion_summary.txt")
        summary = summary_bytes.decode()
        labels = named(summary, "residue_aminoAcids")
        groups = named(summary, "residue_id_to_conformationVariable_id")
        conformation_labels = named(summary, "residue_conformation_pair_to_aminoAcid")
        residues = named(summary, "residues")
        panel = []
        for template in labels["3"]:
            state_domains = []
            for state, group in enumerate(groups):
                dimensions = []
                for residue in group:
                    target = template if residue == "3" else labels[residue][0]
                    dimensions.append(sum(value == target for key, value in conformation_labels[state].items()
                                          if key.startswith("(" + residue + ", ")))
                state_domains.append(dimensions)
            panel.append({"template": template, "state_domains": state_domains,
                          "state_cartesian_counts": [math.prod(domain) for domain in state_domains]})
        formats = {}
        for state in ("complex", "protein", "ligand"):
            member = "emat." + state + ".txt"
            blob = archive.read(member)
            singles, pairs = blob.decode().split("pairs:")
            singles_rows = [line.split() for line in singles.splitlines()[2:] if line.strip()]
            pairs_rows = [line.split() for line in pairs.splitlines()[2:] if line.strip()]
            lexemes = [value for row in singles_rows + pairs_rows for value in row[1:]]
            energies = [Decimal(value) for value in lexemes]
            assert all(value.is_finite() for value in energies)
            formats[state] = {"member": member, "sha256": sha(blob), "entries": len(lexemes),
                              "finite_entries": len(energies),
                              "printed_decimal_exponents": dict(sorted(Counter(value.as_tuple().exponent
                                                                               for value in energies).items()))}
    result = {"scope": "Static lexical and metadata inspection only; no source conditioning or inference.",
              "case_id": case["case_id"], "archive_path": case["local_path"], "archive_sha256": case["sha256"],
              "source_manifest_sha256": sha(manifest_path.read_bytes()), "summary_sha256": sha(summary_bytes),
              "selector": 3, "residue": residues[3], "panel": panel,
              "sum_state_cartesian_counts": sum(sum(row["state_cartesian_counts"]) for row in panel),
              "max_state_cartesian_count": max(max(row["state_cartesian_counts"]) for row in panel),
              "energy_formats": formats}
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"templates": len(panel), "sum_state_cartesian_counts": result["sum_state_cartesian_counts"],
                      "max_state_cartesian_count": result["max_state_cartesian_count"],
                      "energy_entries": sum(row["entries"] for row in formats.values())}))


if __name__ == "__main__":
    inspect()
