"""Independently reconstruct source RC labels and replay metadata-only selection."""

import hashlib
import json
import math
import re
from pathlib import Path
from zipfile import ZipFile

from audit_input_inventory import assignments
from decode_matrix import matrix


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/campaign-005/kras2020"
OUT = Path(__file__).with_name("mapping_audit.json")
AA = dict(zip(
    "ARNDCQEGHILKMFPSTWYV",
    "ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL".split(),
))
ONE = {value: key for key, value in AA.items()} | {"HIP": "H", "HID": "H", "HIE": "H"}


def library_counts(text):
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("!")]
    number = int(lines.pop(0))
    result = {}
    for _ in range(number):
        name, dihedrals, rotamers = lines.pop(0).split()
        dihedrals, rotamers = int(dihedrals), int(rotamers)
        del lines[:dihedrals + rotamers]
        result[name] = max(1, rotamers)
    assert not lines
    return result


def pdb_residues(text):
    result = {}
    for line in text.splitlines():
        if line[:6] not in ("ATOM  ", "HETATM"):
            continue
        assert not line[16].strip() and not line[21].strip()
        position = line[22:27].strip()
        assert position.isdecimal()
        name = line[17:20].strip()
        assert name in ONE
        if position in result:
            assert result[position] == name
        result[position] = name
    return result


def positions(config, residues, counts, strand):
    flex = config["strand_flex"][strand]
    first, last = map(int, config["strand_defs"][strand])
    result = []
    for number, wild in residues.items():
        if not first <= int(number) <= last or number not in flex:
            continue
        templates = list(dict.fromkeys([wild] + flex[number]))
        assert "PRO" not in templates, "Proline pucker needs an additional branch"
        labels, codes = [], []
        for template in templates:
            n = counts[template]
            labels.extend([template] * n)
            codes.extend(f"L{i}" for i in range(n))
        labels.append(wild)
        codes.append("W0")
        result.append({"residue": number, "wild_type": wild, "templates": templates,
                       "conformer_labels": labels, "conformer_codes": codes})
    assert len(result) == len(flex)
    return result


def domains(variant, state_positions, residues, flexible):
    mutations = {}
    for token in variant.split("/"):
        match = re.fullmatch(r"([A-Z])([0-9]+)([A-Z])", token)
        assert match, token
        before, number, after = match.groups()
        position = str(int(number) + 125)
        if position not in flexible:
            raise ValueError("Mutation outside flexible positions")
        if ONE[residues[position]] != before:
            raise ValueError("Mutation WT mismatches prepared coordinates")
        if position in mutations:
            raise ValueError("Duplicate mutation position")
        mutations[position] = after
    result = {}
    for version in ("wild_type", "mutant"):
        result[version] = {}
        for state, source in state_positions.items():
            selected = []
            for pos in source:
                chosen = pos["wild_type"]
                if version == "mutant" and pos["residue"] in mutations:
                    choices = sorted(set(label for label in pos["conformer_labels"]
                                         if ONE[label] == mutations[pos["residue"]]))
                    if len(choices) != 1:
                        raise ValueError("Absent or ambiguous mutant template")
                    chosen = choices[0]
                selected.append([i for i, label in enumerate(pos["conformer_labels"]) if label == chosen])
            if not all(selected):
                raise ValueError("Empty state domain")
            result[version][state] = selected
    return result


def main():
    metadata_path = ROOT / "experiments/energy_recovery5/kras_metadata.json"
    plan_path = DATA / "panel_plan.first.json"
    metadata = json.loads(metadata_path.read_text())
    plan = json.loads(plan_path.read_text())
    meta_matrices = {row["member"]: row for row in metadata["matrices"]}
    variants = plan["initial_variants"]
    assert len(variants) == len(set(variants)) == 41
    configs, pair_rows = [], []
    with ZipFile(DATA / "OSPREY.zip") as source:
        counts = library_counts(source.read("OSPREY/resources/config/LovellRotamer.dat").decode())
    with ZipFile(DATA / "rasDesigns.zip") as archive:
        residues = pdb_residues(archive.read("rasDesigns/retrospective/bbks/1gua_adj.min.pdb").decode())
        for number in range(1, 35):
            config_name = f"rasDesigns/retrospective/bbks/ks{number}.cfs"
            config = assignments(archive.read(config_name).decode())
            protein = positions(config, residues, counts, "strand0")
            ligand = positions(config, residues, counts, "strand1")
            state_positions = {"protein": protein, "ligand": ligand, "complex": protein + ligand}
            for state, ps in state_positions.items():
                name = f"rasDesigns/retrospective/bbks/ks{number}/emat.{state}.rigid.dat"
                raw = archive.read(name)
                parsed = matrix(raw)
                assert parsed["counts"] == [len(p["conformer_labels"]) for p in ps], name
                expected = meta_matrices[name]
                assert expected["sha256"] == hashlib.sha256(raw).hexdigest(), name
                for actual, saved in zip(ps, expected["positions"], strict=True):
                    for key, value in actual.items():
                        assert value == saved[key], (name, key)
            flexible = set(config["strand_flex"]["strand1"])
            for variant in variants:
                record = {"variant": variant, "config": number, "config_member": config_name}
                try:
                    selected = domains(variant, state_positions, residues, flexible)
                    products = [math.prod(map(len, selected[version][state]))
                                for version in ("wild_type", "mutant")
                                for state in ("complex", "protein", "ligand")]
                    record.update({"eligible": max(products) <= 1_000_000,
                                   "total_assignments": sum(products), "counts": products,
                                   "domains": selected})
                except ValueError as error:
                    record.update({"eligible": False, "reason": str(error)})
                pair_rows.append(record)
            configs.append({"config": number, "states": state_positions})
    chosen = []
    for variant in variants:
        eligible = [r for r in pair_rows if r["variant"] == variant and r["eligible"]]
        if eligible:
            chosen.append(min(eligible, key=lambda r: (r["total_assignments"], r["config"])))
    chosen.sort(key=lambda r: (r["total_assignments"], r["variant"], r["config"]))
    admitted, cumulative = [], 0
    for record in chosen:
        if cumulative + record["total_assignments"] > 50_000_000:
            break
        admitted.append(record)
        cumulative += record["total_assignments"]
    claimed = plan["selected_unique_variants"]
    assert [(r["variant"], r["config_member"], r["total_assignments"]) for r in admitted] == [
        (r["variant"], r["config_member"], r["total_assignments"]) for r in claimed]
    for actual, saved in zip(admitted, claimed, strict=True):
        for slot in saved["slots"]:
            ds = actual["domains"][slot["version"]][slot["state"]]
            assert ds == slot["domains"]
            assert math.prod(map(len, ds)) == slot["assignments"]
    parent_eligible = {(r["variant"], r["config_member"]) for r in plan["candidate_pairs"] if r["status"] == "eligible"}
    actual_eligible = {(r["variant"], r["config_member"]) for r in pair_rows if r["eligible"]}
    assert parent_eligible == actual_eligible, (parent_eligible ^ actual_eligible)
    summary = {"configurations": len(configs), "state_label_mappings": len(configs) * 3,
               "candidate_pairs": len(pair_rows), "eligible_pairs": len(actual_eligible),
               "admitted_variants": len(admitted), "admitted_state_slots": len(admitted) * 6,
               "admitted_assignments": cumulative, "variant_names": [r["variant"] for r in admitted],
               "plan_matches": True, "new_scores_computed": False,
               "coordinate_regeneration": "Not performed; labels/order reconstructed from source, PDB and dimension agreement."}
    result = {"inputs": [{"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                         for p in (metadata_path, plan_path, DATA / "OSPREY.zip", DATA / "rasDesigns.zip")],
              "summary": summary, "configs": configs, "candidate_pairs": pair_rows,
              "admitted": admitted}
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
