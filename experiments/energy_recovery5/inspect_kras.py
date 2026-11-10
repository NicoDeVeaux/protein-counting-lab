"""Inventory archived matrices and reconstruct source-defined residue-conformer labels."""

import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import posixpath
import re
import zipfile

from .java_matrix import decode


ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "data/campaign-005/kras2020"
OUT = Path(__file__).with_name("kras_metadata.json")
STATES = ("protein", "ligand", "complex")
SOURCES = (
    "OSPREY/src/edu/duke/cs/osprey/confspace/AbstractTupleMatrix.java",
    "OSPREY/src/edu/duke/cs/osprey/confspace/TupleMatrixDouble.java",
    "OSPREY/src/edu/duke/cs/osprey/ematrix/EnergyMatrix.java",
    "OSPREY/src/edu/duke/cs/osprey/confspace/SimpleConfSpace.java",
    "OSPREY/src/edu/duke/cs/osprey/confspace/Strand.java",
    "OSPREY/src/edu/duke/cs/osprey/restypes/ResidueTemplateLibrary.java",
    "OSPREY/src/edu/duke/cs/osprey/kstar/pfunc/BoltzmannCalculator.java",
    "OSPREY/src/edu/duke/cs/osprey/energy/PoissonBoltzmannEnergy.java",
    "OSPREY/src/edu/duke/cs/osprey/energy/ConfEnergyCalculator.java",
    "OSPREY/src/edu/duke/cs/osprey/energy/EnergyPartition.java",
    "OSPREY/resources/config/LovellRotamer.dat",
)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def config_from_text(text):
    result = {}
    for statement in ast.parse(text).body:
        if not (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)):
            raise ValueError("Only literal top-level config assignments are supported")
        name = statement.targets[0].id
        if name in result:
            raise ValueError("Repeated config variable: " + name)
        result[name] = ast.literal_eval(statement.value)
    if set(result) != {"mol", "strand_defs", "strand_flex"}:
        raise ValueError("Unexpected config variables")
    return result


def rotamer_counts(text):
    rows = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("!")]
    count = int(rows.pop(0))
    result = {}
    for _ in range(count):
        name, ndihedrals, nrotamers = rows.pop(0).split()
        ndihedrals, nrotamers = int(ndihedrals), int(nrotamers)
        result[name] = 2 if name == "PRO" else max(1, nrotamers)
        del rows[:ndihedrals + nrotamers]
    if rows:
        raise ValueError("Trailing rotamer rows")
    return result


def pdb_residues(text):
    result = {}
    for row in text.splitlines():
        if row.startswith(("MODEL", "ENDMDL")):
            raise ValueError("Multiple or explicit PDB models are unsupported")
        if not row.startswith(("ATOM  ", "HETATM")):
            continue
        if row[16] != " " or row[21] != " ":
            raise ValueError("Alternate conformers or explicit chains require native label reconstruction")
        number = row[22:27].strip()
        name = row[17:20].strip()
        if number in result and result[number] != name:
            raise ValueError("PDB residue identity is inconsistent")
        result[number] = name
    return result


def reconstruct_positions(config, residues, counts):
    strands = {}
    residue_order = list(residues)
    for strand in ("strand0", "strand1"):
        start, end = config["strand_defs"][strand]
        positions = []
        interval = residue_order[residue_order.index(start):residue_order.index(end) + 1]
        flex = config["strand_flex"][strand]
        if not set(flex) <= set(interval):
            raise ValueError("Flexibility outside strand")
        for number in interval:
            if number not in flex:
                continue
            wild_type = residues[number]
            templates = list(dict.fromkeys([wild_type] + flex[number]))
            labels = []
            codes = []
            for template in templates:
                for index in range(counts[template]):
                    labels.append(template)
                    codes.append("L" + str(index))
            labels.append(wild_type)
            codes.append("W0")
            positions.append({"residue": number, "wild_type": wild_type, "templates": templates,
                              "conformer_labels": labels, "conformer_codes": codes,
                              "template_counts": dict(Counter(labels))})
        strands[strand] = positions
    return {"protein": strands["strand0"], "ligand": strands["strand1"],
            "complex": strands["strand0"] + strands["strand1"]}


def inspect():
    with zipfile.ZipFile(DIRECTORY / "OSPREY.zip") as source:
        counts = rotamer_counts(source.read("OSPREY/resources/config/LovellRotamer.dat").decode())
        sources = [{"member": name, "sha256": digest(source.read(name))} for name in SOURCES]
        boltzmann = source.read("OSPREY/src/edu/duke/cs/osprey/energy/PoissonBoltzmannEnergy.java").decode()
        expression = re.search(r"double\s+constRT\s*=\s*([^;]+);", boltzmann).group(1)
        if expression != "1.9891/1000.0 * 298.15":
            raise ValueError("Unexpected source RT expression")
        constants = {"constRT_expression": expression, "constRT_binary64_hex": (1.9891 / 1000.0 * 298.15).hex()}
    with zipfile.ZipFile(DIRECTORY / "rasDesigns.zip") as archive:
        names = archive.namelist()
        directories = sorted({str(PurePosixPath(name).parent) for name in names if name.endswith(".rigid.dat")})
        configs = []
        matrices = []
        failures = []
        for directory in directories:
            config_name = directory + ".cfs"
            try:
                config_blob = archive.read(config_name)
                config = config_from_text(config_blob.decode())
                pdb_name = posixpath.normpath(directory + "/" + config["mol"])
                pdb_blob = archive.read(pdb_name)
                positions = reconstruct_positions(config, pdb_residues(pdb_blob.decode()), counts)
                states = {}
                for state in STATES:
                    member = directory + "/emat." + state + ".rigid.dat"
                    blob = archive.read(member)
                    matrix = decode(blob)
                    if tuple(len(pos["conformer_labels"]) for pos in positions[state]) != matrix.domains:
                        raise ValueError("Reconstructed RC labels disagree with matrix domains: " + member)
                    row = {"member": member, "sha256": digest(blob), "bytes": len(blob),
                           "domains": list(matrix.domains), "cartesian_count": math.prod(matrix.domains),
                           "one_body_entries": len(matrix.one_body), "pairwise_entries": len(matrix.pairwise),
                           "constant_hex": matrix.constant.hex(), "pruning_interval": "Infinity",
                           "higher_terms": None, "tuple_trees": None, "embedded_reference_energy_object": None,
                           "all_energy_entries_finite": True, "positions": positions[state]}
                    matrices.append(row)
                    states[state] = {"matrix_member": member, "domains": row["domains"],
                                     "cartesian_count": row["cartesian_count"]}
                configs.append({"config_member": config_name, "config_sha256": digest(config_blob),
                                "pdb_member": pdb_name, "pdb_sha256": digest(pdb_blob), "config": config,
                                "states": states, "all_matrix_domains_match_source_reconstruction": True})
            except Exception as error:
                failures.append({"config_member": config_name, "error": str(error)})
        result = {"scope": "Static archive, array-dimension and source-defined label reconstruction only; no partition sums or scores.",
                  "archives": [{"path": str(path.relative_to(ROOT)), "sha256": digest(path.read_bytes())}
                               for path in (DIRECTORY / "rasDesigns.zip", DIRECTORY / "OSPREY.zip")],
                  "source_members": sources, "source_numeric_constants": constants,
                  "rotamer_library_counts": counts, "configs": configs, "matrices": matrices, "failures": failures,
                  "restrictions": ["Source reconstruction rejects all alternate conformers and chain labels.",
                                   "A native Java conformation-space cross-check has not been executed.",
                                   "Rigid matrix sums define a new discrete target, not the authors' continuous-minimized BBK* prediction."]}
        OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"candidate_configs": len(directories), "reconstructed_configs": len(configs),
                      "decoded_rigid_matrices": len(matrices), "failures": failures,
                      "source_numeric_constants": constants}))


if __name__ == "__main__":
    inspect()
