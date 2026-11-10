"""Inventory published KRas inputs without reading predictions or energy values."""

import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data/campaign-005/kras2020/rasDesigns.zip"
OUT = Path(__file__).with_name("input_inventory.json")


def assignments(source):
    values = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                values[target.id] = ast.literal_eval(node.value)
    return values


def main():
    configs = []
    with ZipFile(ARCHIVE) as archive:
        infos = {entry.filename: entry for entry in archive.infolist()}
        config_names = sorted(
            name for name in infos
            if re.fullmatch(r"rasDesigns/retrospective/bbks/ks[0-9]+\.cfs", name)
        )
        for name in config_names:
            raw = archive.read(name)
            config = assignments(raw.decode())
            ident = Path(name).stem
            matrices = []
            for state in ("protein", "ligand", "complex"):
                for form in ("rigid", "minimized"):
                    path = f"rasDesigns/retrospective/bbks/{ident}/emat.{state}.{form}.dat"
                    entry = infos.get(path)
                    matrices.append({
                        "state": state,
                        "form": form,
                        "path": path,
                        "present": entry is not None,
                        "bytes": entry.file_size if entry else None,
                    })
            flex = config["strand_flex"]
            mutable = [
                {"strand": strand, "position": position, "templates": templates}
                for strand, positions in sorted(flex.items())
                for position, templates in sorted(positions.items())
                if len(templates) > 1
            ]
            configs.append({
                "id": ident,
                "configuration_path": name,
                "configuration_sha256": hashlib.sha256(raw).hexdigest(),
                "declared_molecule": config["mol"],
                "strand_definitions": config["strand_defs"],
                "flexible_positions": flex,
                "mutable_positions": mutable,
                "matrices": matrices,
            })
        prepared = [
            {"path": name, "bytes": entry.file_size}
            for name, entry in infos.items()
            if name.endswith("1gua_adj.min.pdb")
        ]
        reads = [name for name in infos if name.endswith("README.txt")]
        summary = {
            "source_archive": str(ARCHIVE.relative_to(ROOT)),
            "source_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
            "source_bytes": ARCHIVE.stat().st_size,
            "archive_entries": len(infos),
            "retrospective_core_configurations": len(configs),
            "matrix_presence": dict(Counter(
                str(matrix["present"]) for config in configs for matrix in config["matrices"]
            )),
            "prepared_structure_entries": prepared,
            "readme_paths": reads,
            "configurations": configs,
            "scope": {
                "read_predictions": False,
                "read_energy_values": False,
                "imported_experiment_code": False,
                "readiness": "Potential input source; state/conformer/sequence and assay mappings not yet validated.",
            },
        }
    OUT.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in (
        "archive_entries", "retrospective_core_configurations", "matrix_presence"
    )}))


if __name__ == "__main__":
    main()
