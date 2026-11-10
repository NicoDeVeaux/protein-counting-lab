"""Independent restricted Java-serialization decoder for archived energy matrices."""

import math
import struct


class Decoder:
    def __init__(self, payload):
        self.payload = memoryview(payload)
        self.offset = 0
        self.handles = []
        if self.take(4).tobytes() != b"\xac\xed\x00\x05":
            raise ValueError("Not a version-5 Java serialization stream")

    def take(self, length):
        if length < 0 or self.offset + length > len(self.payload):
            raise ValueError("Truncated serialization stream")
        result = self.payload[self.offset:self.offset + length]
        self.offset += length
        return result

    def unpack(self, fmt):
        return struct.unpack(">" + fmt, self.take(struct.calcsize(">" + fmt)))[0]

    def utf(self, wide=False):
        length = self.unpack("q" if wide else "H")
        raw = self.take(length).tobytes()
        # The source class/field names and residue labels use ASCII.
        if any(value > 127 for value in raw) or 0 in raw:
            raise ValueError("Non-ASCII modified UTF-8 is outside this decoder's scope")
        return raw.decode("ascii")

    def remember(self, value):
        self.handles.append(value)
        return value

    def annotation(self):
        values = []
        while True:
            tag = self.unpack("B")
            if tag == 0x78:
                return values
            if tag == 0x77:
                values.append(self.take(self.unpack("B")).tobytes())
            elif tag == 0x7A:
                values.append(self.take(self.unpack("i")).tobytes())
            else:
                values.append(self.item(tag))

    def item(self, tag=None):
        if tag is None:
            tag = self.unpack("B")
        if tag == 0x70:
            return None
        if tag == 0x71:
            handle = self.unpack("I") - 0x7E0000
            if not 0 <= handle < len(self.handles):
                raise ValueError("Invalid serialization handle")
            return self.handles[handle]
        if tag in (0x74, 0x7C):
            return self.remember(self.utf(wide=tag == 0x7C))
        if tag == 0x72:
            name = self.utf()
            serial = self.unpack("q")
            result = self.remember({"kind": "class", "name": name, "serial": serial})
            result["flags"] = self.unpack("B")
            result["fields"] = []
            for _ in range(self.unpack("H")):
                code = chr(self.unpack("B"))
                field = self.utf()
                class_name = self.item() if code in "L[" else None
                result["fields"].append((code, field, class_name))
            result["annotation"] = self.annotation()
            result["parent"] = self.item()
            return result
        if tag == 0x73:
            descriptor = self.item()
            result = self.remember({"kind": "object", "class": descriptor, "fields": {}})
            hierarchy = []
            current = descriptor
            while current is not None:
                hierarchy.append(current)
                current = current["parent"]
            for current in reversed(hierarchy):
                flags = current["flags"]
                if flags & ~0x03 or not flags & 0x02:
                    raise ValueError("Unsupported class serialization flags")
                fields = {}
                for code, field, _ in current["fields"]:
                    fields[field] = self.primitive(code) if code not in "L[" else self.item()
                result["fields"][current["name"]] = fields
                if flags & 0x01:
                    result.setdefault("annotations", {})[current["name"]] = self.annotation()
            return result
        if tag == 0x75:
            descriptor = self.item()
            result = self.remember({"kind": "array", "class": descriptor, "values": None})
            length = self.unpack("i")
            if not 0 <= length <= 20_000_000:
                raise ValueError("Array length outside decoder scope")
            code = descriptor["name"][1:2]
            if code in "BCDFIJSZ":
                result["values"] = [self.primitive(code) for _ in range(length)]
            else:
                result["values"] = [self.item() for _ in range(length)]
            return result
        raise ValueError(f"Unsupported serialization tag {tag:#x} at {self.offset - 1}")

    def primitive(self, code):
        formats = {"B": "b", "C": "H", "D": "d", "F": "f", "I": "i", "J": "q", "S": "h", "Z": "?"}
        if code not in formats:
            raise ValueError(f"Unsupported primitive type {code!r}")
        return self.unpack(formats[code])


def values(array, expected_type):
    if array["kind"] != "array" or array["class"]["name"] != expected_type:
        raise ValueError(f"Expected array {expected_type}")
    return array["values"]


def matrix(payload):
    decoder = Decoder(payload)
    obj = decoder.item()
    if decoder.offset != len(payload):
        raise ValueError("Unconsumed trailing serialization bytes")
    if obj["class"]["name"] != "edu.duke.cs.osprey.ematrix.EnergyMatrix":
        raise ValueError("Not an EnergyMatrix")
    fields = obj["fields"]
    abstract = fields["edu.duke.cs.osprey.confspace.AbstractTupleMatrix"]
    pair = fields["edu.duke.cs.osprey.confspace.TupleMatrixDouble"]
    energy = fields["edu.duke.cs.osprey.ematrix.EnergyMatrix"]
    for name in ("higherTerms", "tupleTrees"):
        if abstract[name] is not None:
            raise ValueError(f"Non-null {name} requires a higher-order decoder")
    if energy["eRefMat"] is not None:
        raise ValueError("Non-null reference-energy object requires an explicit convention audit")
    counts = values(abstract["numConfAtPos"], "[I")
    one_offsets = values(abstract["oneBodyOffsets"], "[I")
    pair_offsets = values(abstract["pairwiseOffsets"], "[I")
    one_body = values(pair["oneBody"], "[D")
    pairwise = values(pair["pairwise"], "[D")
    if abstract["numPos"] != len(counts) or not all(n > 0 for n in counts):
        raise ValueError("Invalid position dimensions")
    expected_one = []
    expected_pair = []
    offset = 0
    for count in counts:
        expected_one.append(offset)
        offset += count
    if len(one_body) != offset or one_offsets != expected_one:
        raise ValueError("One-body lengths/offsets disagree")
    offset = 0
    for i, ni in enumerate(counts):
        for nj in counts[:i]:
            expected_pair.append(offset)
            offset += ni * nj
    if len(pairwise) != offset or pair_offsets != expected_pair or abstract["numPairwiseTerms"] != offset:
        raise ValueError("Pairwise lengths/offsets disagree")
    if any(math.isnan(x) or x == -math.inf for x in one_body + pairwise + [energy["constTerm"]]):
        raise ValueError("NaN or negative infinite energy")
    return {
        "counts": counts,
        "one_offsets": one_offsets,
        "pair_offsets": pair_offsets,
        "one_body": one_body,
        "pairwise": pairwise,
        "constant": energy["constTerm"],
        "pruning_interval": abstract["pruningInterval"],
        "class_serials": {x["name"]: x["serial"] for x in (obj["class"], obj["class"]["parent"], obj["class"]["parent"]["parent"])},
    }
