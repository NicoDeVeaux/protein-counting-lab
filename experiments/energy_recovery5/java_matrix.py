"""Decode the primitive-only Java energy-matrix serialization without executing Java code."""

from dataclasses import dataclass
import math
import struct


CLASS_UIDS = {
    "edu.duke.cs.osprey.ematrix.EnergyMatrix": 6503270845014990929,
    "edu.duke.cs.osprey.confspace.TupleMatrixDouble": -1286639255089978027,
    "edu.duke.cs.osprey.confspace.AbstractTupleMatrix": 1654821458320722522,
    "java.lang.Double": -9172774392245257468,
    "java.lang.Number": -8742448824652078965,
    "[D": 4514449696888150558,
    "[I": 5600894804908749477,
}


class DecodeError(ValueError):
    pass


class Reader:
    def __init__(self, data):
        self.data = memoryview(data)
        self.offset = 0
        self.handles = {}
        if self.take(4) != b"\xac\xed\x00\x05":
            raise DecodeError("Expected Java serialization version 5")

    def take(self, size):
        if size < 0 or self.offset + size > len(self.data):
            raise DecodeError("Truncated stream")
        blob = self.data[self.offset:self.offset + size].tobytes()
        self.offset += size
        return blob

    def number(self, fmt):
        return struct.unpack(">" + fmt, self.take(struct.calcsize(fmt)))[0]

    def utf(self):
        blob = self.take(self.number("H"))
        if b"\xc0\x80" in blob or any(value >= 128 for value in blob):
            raise DecodeError("Only ASCII identifiers are supported")
        return blob.decode("ascii")

    def register(self, value):
        self.handles[0x7e0000 + len(self.handles)] = value
        return value

    def read(self):
        token = self.number("B")
        if token == 0x70:
            return None
        if token == 0x71:
            handle = self.number("I")
            if handle not in self.handles:
                raise DecodeError("Invalid stream reference")
            return self.handles[handle]
        if token == 0x74:
            return self.register(self.utf())
        if token == 0x72:
            name, uid = self.utf(), self.number("q")
            if CLASS_UIDS.get(name) != uid:
                raise DecodeError("Unrecognized class/UID: " + name)
            descriptor = self.register({"name": name, "uid": uid})
            flags = self.number("B")
            if flags != 2:
                raise DecodeError("Only default serializable classes are supported")
            fields = []
            for _ in range(self.number("H")):
                code, field = chr(self.number("B")), self.utf()
                signature = self.read() if code in "L[" else None
                fields.append((code, field, signature))
            if self.number("B") != 0x78:
                raise DecodeError("Class annotations are unsupported")
            descriptor.update(fields=fields, parent=self.read())
            return descriptor
        if token == 0x73:
            descriptor = self.read()
            if not isinstance(descriptor, dict) or "fields" not in descriptor:
                raise DecodeError("Object has no class descriptor")
            value = self.register({"__class__": descriptor["name"]})
            hierarchy = []
            while descriptor is not None:
                hierarchy.append(descriptor)
                descriptor = descriptor["parent"]
            for cls in reversed(hierarchy):
                for code, field, signature in cls["fields"]:
                    if field in value:
                        raise DecodeError("Shadowed fields are unsupported")
                    if code in "L[":
                        value[field] = self.read()
                    elif code in {"I", "D"}:
                        value[field] = self.number({"I": "i", "D": "d"}[code])
                    else:
                        raise DecodeError("Unsupported field type " + code)
            return value
        if token == 0x75:
            descriptor = self.read()
            if not isinstance(descriptor, dict) or descriptor.get("name") not in {"[D", "[I"}:
                raise DecodeError("Only primitive double/int arrays are supported")
            values = self.register([])
            size = self.number("i")
            if not 0 <= size <= 100_000_000:
                raise DecodeError("Array size outside supported range")
            fmt = "d" if descriptor["name"] == "[D" else "i"
            blob = self.take(size * struct.calcsize(fmt))
            values.extend(value[0] for value in struct.iter_unpack(">" + fmt, blob))
            return values
        raise DecodeError("Unsupported serialization token " + hex(token))


@dataclass(frozen=True)
class EnergyMatrix:
    domains: tuple[int, ...]
    one_body: tuple[float, ...]
    pairwise: tuple[float, ...]
    one_body_offsets: tuple[int, ...]
    pairwise_offsets: tuple[int, ...]
    constant: float
    pruning_interval: float

    def single(self, pos, rc):
        if not 0 <= pos < len(self.domains) or not 0 <= rc < self.domains[pos]:
            raise IndexError((pos, rc))
        return self.one_body[self.one_body_offsets[pos] + rc]

    def pair(self, pos1, rc1, pos2, rc2):
        if pos1 == pos2:
            raise IndexError("A position cannot pair with itself")
        if pos1 < pos2:
            pos1, pos2, rc1, rc2 = pos2, pos1, rc2, rc1
        if (not 0 <= pos2 < pos1 < len(self.domains) or not 0 <= rc1 < self.domains[pos1]
                or not 0 <= rc2 < self.domains[pos2]):
            raise IndexError((pos1, rc1, pos2, rc2))
        index = pos1 * (pos1 - 1) // 2 + pos2
        offset = self.pairwise_offsets[index] + self.domains[pos2] * rc1 + rc2
        return self.pairwise[offset]


def decode(data):
    reader = Reader(data)
    obj = reader.read()
    if reader.offset != len(data):
        raise DecodeError("Trailing stream data")
    if not isinstance(obj, dict) or obj.get("__class__") != "edu.duke.cs.osprey.ematrix.EnergyMatrix":
        raise DecodeError("Expected EnergyMatrix root")
    expected = {"__class__", "constTerm", "eRefMat", "oneBody", "pairwise", "numPairwiseTerms", "numPos",
                "pruningInterval", "defaultHigherInteraction", "higherTerms", "numConfAtPos", "oneBodyOffsets",
                "pairwiseOffsets", "tupleTrees"}
    if set(obj) != expected:
        raise DecodeError("Unexpected root fields")
    if any(obj[key] is not None for key in ("higherTerms", "tupleTrees", "eRefMat")):
        raise DecodeError("Higher terms and embedded reference-energy objects are unsupported")
    default = obj["defaultHigherInteraction"]
    if not (isinstance(default, dict) and default.get("__class__") == "java.lang.Double"
            and default.get("value") == 0):
        raise DecodeError("Expected zero default higher interaction")
    dimensions = tuple(obj["numConfAtPos"])
    if len(dimensions) != obj["numPos"] or not dimensions or any(value <= 0 for value in dimensions):
        raise DecodeError("Invalid conformation counts")
    expected_one, expected_pair, one_size, pair_size = [], [], 0, 0
    for pos1, n1 in enumerate(dimensions):
        expected_one.append(one_size)
        one_size += n1
        for pos2 in range(pos1):
            expected_pair.append(pair_size)
            pair_size += n1 * dimensions[pos2]
    if (obj["oneBodyOffsets"] != expected_one or obj["pairwiseOffsets"] != expected_pair
            or len(obj["oneBody"]) != one_size or len(obj["pairwise"]) != pair_size
            or obj["numPairwiseTerms"] != pair_size):
        raise DecodeError("Array dimensions/offsets disagree")
    if not all(math.isfinite(value) for value in obj["oneBody"] + obj["pairwise"] + [obj["constTerm"]]):
        raise DecodeError("Nonfinite energy entry")
    return EnergyMatrix(dimensions, tuple(obj["oneBody"]), tuple(obj["pairwise"]), tuple(expected_one),
                        tuple(expected_pair), obj["constTerm"], obj["pruningInterval"])
