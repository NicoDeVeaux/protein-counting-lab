"""Check decoded source energies against the archived OSPREY Java getters."""

import ast
import hashlib
from pathlib import Path
import struct
import unittest
import zipfile

from .java_matrix import decode, DecodeError


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data/campaign-005/kras2020/rasDesigns.zip"
NATIVE = Path(__file__).with_name("native_matrix_check.tsv")


class MatrixIdentity(unittest.TestCase):
    def test_all_native_getter_values_and_domains(self):
        rows = [row.split("\t") for row in NATIVE.read_text().splitlines()]
        self.assertEqual(len(rows), 126)
        entries = 0
        with zipfile.ZipFile(ARCHIVE) as archive:
            for member, domain_text, constant_text, expected_hash in rows:
                with self.subTest(member=member):
                    matrix = decode(archive.read(member))
                    self.assertEqual(matrix.domains, tuple(ast.literal_eval(domain_text)))
                    self.assertEqual(matrix.constant, float.fromhex(constant_text))
                    digest = hashlib.sha256(struct.pack(">d", matrix.constant))
                    for pos, size in enumerate(matrix.domains):
                        for rc in range(size):
                            digest.update(struct.pack(">d", matrix.single(pos, rc)))
                            entries += 1
                    for pos1, size1 in enumerate(matrix.domains):
                        for pos2 in range(pos1):
                            for rc1 in range(size1):
                                for rc2 in range(matrix.domains[pos2]):
                                    value = matrix.pair(pos1, rc1, pos2, rc2)
                                    self.assertEqual(value, matrix.pair(pos2, rc2, pos1, rc1))
                                    digest.update(struct.pack(">d", value))
                                    entries += 1
                    self.assertEqual(digest.hexdigest(), expected_hash)
        self.assertGreater(entries, 100_000)

    def test_truncated_and_trailing_streams_rejected(self):
        with zipfile.ZipFile(ARCHIVE) as archive:
            member = "rasDesigns/retrospective/bbks/ks5/emat.protein.rigid.dat"
            blob = archive.read(member)
        for data in (blob[:-1], blob + b"unexpected"):
            with self.subTest(length=len(data)), self.assertRaises(DecodeError):
                decode(data)

    def test_unknown_class_identity_rejected(self):
        with zipfile.ZipFile(ARCHIVE) as archive:
            member = "rasDesigns/retrospective/bbks/ks5/emat.protein.rigid.dat"
            blob = archive.read(member)
        invalid = blob.replace(b"edu.duke.cs.osprey.ematrix.EnergyMatrix", b"edu.duke.cs.osprey.ematrix.EnergyMatriX", 1)
        self.assertNotEqual(blob, invalid)
        with self.assertRaises(DecodeError):
            decode(invalid)


if __name__ == "__main__":
    unittest.main()
