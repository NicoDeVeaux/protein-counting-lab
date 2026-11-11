"""Select a prospective cohort from archive metadata and CNF syntax only."""

import argparse
import hashlib
import json
import lzma
from pathlib import Path
import random
import tarfile

from .cnf import eligibility, parse_dimacs


ARCHIVE_URL = "https://nextcloud.liu.se/s/STzdpXNgZDZaPRo/download?path=%2F&files=mc2026_track1_public.tar"
ARCHIVE_SHA256 = "30766e5e4e69bcca2d5d2b33ab4884cedd4dd5362e3dd72361b5cd68e9270a03"


def select(archive, destination):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("official archive differs from acquired bytes")
    destination.mkdir(parents=True, exist_ok=False)
    catalogue, inputs = [], {}
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            if not member.isfile():
                continue
            if not member.name.endswith(".cnf.xz"):
                raise ValueError("unexpected source archive member")
            compressed = source.extractfile(member).read()
            row = {"member": member.name, "compressed_bytes": len(compressed),
                   "compressed_sha256": hashlib.sha256(compressed).hexdigest()}
            decoder = lzma.LZMADecompressor()
            raw = decoder.decompress(compressed, max_length=8 * 1024 * 1024 + 1)
            if not decoder.eof or len(raw) > 8 * 1024 * 1024:
                row["exclusions"] = ["uncompressed_bytes_above_8MiB"]
            else:
                row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                try:
                    cnf = parse_dimacs(raw.decode("ascii"))
                    inventory, reasons = eligibility(cnf)
                    row.update(inventory)
                    row["exclusions"] = reasons
                    if not reasons:
                        inputs[member.name] = raw
                except (ValueError, UnicodeError) as error:
                    row["exclusions"] = ["unsupported_or_invalid_dimacs"]
                    row["parse_error"] = str(error)
            catalogue.append(row)
    eligible = sorted(inputs)
    random.Random(8008).shuffle(eligible)
    chosen = eligible[:12]
    records = []
    by_name = {row["member"]: row for row in catalogue}
    for name in chosen:
        target = destination / Path(name).name.removesuffix(".xz")
        target.write_bytes(inputs[name])
        records.append({**by_name[name], "local_filename": target.name})
    result = {"source_url": ARCHIVE_URL, "source_sha256": ARCHIVE_SHA256,
              "seed": 8008, "eligible_count": len(eligible), "selected": records,
              "catalogue": sorted(catalogue, key=lambda row: row["member"]),
              "queries": [[chosen[i], chosen[i + 1]] for i in range(0, len(chosen) - 1, 2)]}
    (destination / "COHORT.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = select(args.archive, args.destination)
    print(json.dumps({"catalogue_entries": len(result["catalogue"]),
                      "eligible": result["eligible_count"],
                      "selected": result["selected"], "queries": result["queries"]}))


if __name__ == "__main__":
    main()
