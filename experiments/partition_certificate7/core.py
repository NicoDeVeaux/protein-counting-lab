"""Export the actual prefix producer's cuts without changing campaign 006."""

from experiments.certified_rank6.core import Model, PartitionBounds


FIELDS = {"n", "factors", "cut", "lower", "upper"}


def model_payload(model):
    if not isinstance(model, Model):
        raise TypeError("expected an immutable finite Model")

    def encode(factor, level=0, offset=0):
        if level == len(factor.scope):
            return ["c", factor.values[offset]]
        width = 1 << (len(factor.scope) - level - 1)
        return ["b", factor.scope[level], encode(factor, level + 1, offset),
                encode(factor, level + 1, offset + width)]

    return {"n": model.n, "factors": [encode(factor) for factor in model.key[1]]}


def build_certificate(model, max_expansions=16):
    """Record actual one-step refinements, retaining exact closed subtrees."""
    if type(max_expansions) is not int or max_expansions < 0:
        raise ValueError("expansion budget must be a nonnegative integer")
    producer = PartitionBounds(model)
    splits = set()
    for _ in range(max_expansions):
        if not producer.heap:
            break
        prefix = producer.heap[0][1]
        if producer.refine(1) != 1:
            raise AssertionError("a recorded split must refine exactly one prefix")
        splits.add(prefix)

    def encode_cut(prefix=()):
        if prefix not in splits:
            return 0
        return [encode_cut(prefix + (0,)), encode_cut(prefix + (1,))]

    return {**model_payload(model), "cut": encode_cut(),
            "lower": producer.lower, "upper": producer.upper}


def check_binding(model, certificate):
    """Bind the submitted descriptor to the caller's complete canonical model."""
    if not isinstance(model, Model):
        raise TypeError("expected an immutable finite Model")
    if type(certificate) is not dict or set(certificate) != FIELDS:
        return False
    n = certificate["n"]
    if type(n) is not int or n != model.n:
        return False
    for name in ("lower", "upper"):
        if type(certificate[name]) is not int or certificate[name] < 0:
            return False
    if certificate["lower"] > certificate["upper"]:
        return False

    def valid_factor(tree):
        if type(tree) is not list or not tree or type(tree[0]) is not str:
            return False
        if len(tree) == 2 and tree[0] == "c":
            return type(tree[1]) is int and tree[1] >= 0
        if len(tree) == 4 and tree[0] == "b":
            return (type(tree[1]) is int and 0 <= tree[1] < n
                    and valid_factor(tree[2]) and valid_factor(tree[3]))
        return False

    def valid_cut(tree, remaining):
        if type(tree) is int:
            return tree == 0
        return (type(tree) is list and len(tree) == 2 and remaining > 0
                and valid_cut(tree[0], remaining - 1)
                and valid_cut(tree[1], remaining - 1))

    factors = certificate["factors"]
    return (type(factors) is list and all(valid_factor(f) for f in factors)
            and valid_cut(certificate["cut"], n)
            and factors == model_payload(model)["factors"])
