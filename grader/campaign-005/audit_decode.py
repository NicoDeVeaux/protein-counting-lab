"""Audit matrix serialization and metadata without solving molecular targets."""

import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

from decode_matrix import matrix


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("decode_audit.json")
ARCHIVE = ROOT / "data/campaign-005/kras2020/rasDesigns.zip"
SOURCE = ROOT / "data/campaign-005/kras2020/OSPREY.zip"
UIDS = {
    "edu.duke.cs.osprey.ematrix.EnergyMatrix": 6503270845014990929,
    "edu.duke.cs.osprey.confspace.TupleMatrixDouble": -1286639255089978027,
    "edu.duke.cs.osprey.confspace.AbstractTupleMatrix": 1654821458320722522,
}


def digest_doubles(items):
    return hashlib.sha256(b"".join(struct.pack(">d", x) for x in items)).hexdigest()


def main():
    rows = []
    with ZipFile(SOURCE) as archive:
        sources = []
        for name in (
            "OSPREY/src/edu/duke/cs/osprey/ematrix/EnergyMatrix.java",
            "OSPREY/src/edu/duke/cs/osprey/confspace/TupleMatrixDouble.java",
            "OSPREY/src/edu/duke/cs/osprey/confspace/AbstractTupleMatrix.java",
            "OSPREY/src/edu/duke/cs/osprey/energy/PoissonBoltzmannEnergy.java",
            "OSPREY/src/edu/duke/cs/osprey/kstar/pfunc/BoltzmannCalculator.java",
        ):
            content = archive.read(name)
            sources.append({"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    with ZipFile(ARCHIVE) as archive:
        for number in range(1, 35):
            for state in ("protein", "ligand", "complex"):
                for form in ("rigid", "minimized"):
                    name = f"rasDesigns/retrospective/bbks/ks{number}/emat.{state}.{form}.dat"
                    payload = archive.read(name)
                    obj = matrix(payload)
                    assert obj["class_serials"] == UIDS, name
                    assert obj["pruning_interval"] == math.inf, name
                    rows.append({
                        "path": name,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "bytes": len(payload),
                        "configuration": f"ks{number}",
                        "state": state,
                        "form": form,
                        "counts": obj["counts"],
                        "one_offsets": obj["one_offsets"],
                        "pair_offsets": obj["pair_offsets"],
                        "one_values": len(obj["one_body"]),
                        "pair_values": len(obj["pairwise"]),
                        "one_body_bits_sha256": digest_doubles(obj["one_body"]),
                        "pairwise_bits_sha256": digest_doubles(obj["pairwise"]),
                        "positive_infinite_entries": sum(x == math.inf for x in obj["one_body"] + obj["pairwise"]),
                        "constant_hex": obj["constant"].hex(),
                        "reference_object": None,
                        "higher_terms": None,
                        "tuple_trees": None,
                    })
        # A source-byte truncation must never be accepted as a complete matrix.
        try:
            matrix(payload[:-1])
        except (ValueError, KeyError, struct.error):
            truncated_rejected = True
        else:
            raise AssertionError("Truncated stream accepted")
    result = {
        "input_archive": str(ARCHIVE.relative_to(ROOT)),
        "input_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        "source_archive": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "source_files": sources,
        "parser": "Independent restricted stdlib Java stream reader; no experiment imports or Java object execution.",
        "matrices": rows,
        "summary": {
            "matrices": len(rows),
            "rigid_matrices": sum(row["form"] == "rigid" for row in rows),
            "numeric_entries": sum(row["one_values"] + row["pair_values"] for row in rows),
            "constant_hex_counts": dict(Counter(row["constant_hex"] for row in rows)),
            "positive_infinite_entries": sum(row["positive_infinite_entries"] for row in rows),
            "truncated_stream_rejected": truncated_rejected,
            "scores_computed": False,
            "conformer_labels_validated": False,
            "molecular_readiness": "Partial: serialization, dimensions, offsets and class versions verify; sequence/conformer and assay mapping still required.",
        },
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
