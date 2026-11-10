"""Hash numerical targets separately from metadata and measured preparation costs."""

import hashlib
import struct
import time

import numpy as np

from experiments.structure import simplify_model


def target_fingerprint(model):
    digest = hashlib.sha256(b"campaign003-numerical-target-v1\0")

    def integers(values):
        digest.update(struct.pack(">Q", len(values)))
        for value in values:
            digest.update(struct.pack(">Q", value))

    integers(model.domains)
    digest.update(struct.pack(">Q", len(model.factors)))
    for factor in model.factors:
        integers(factor.scope)
        integers(factor.values.shape)
        digest.update(np.asarray(factor.values, dtype="<f8").tobytes(order="C"))
    return digest.hexdigest()


def prepare_model(model, representation):
    started = time.perf_counter()
    cpu_started = time.process_time()
    propagation_seconds = 0.0
    propagation_cpu_seconds = 0.0
    proof = None
    if representation == "propagated":
        from experiments.zero_support import propagate_model

        phase = time.perf_counter()
        cpu_phase = time.process_time()
        model, proof = propagate_model(model, simplify=False)
        propagation_seconds = time.perf_counter() - phase
        propagation_cpu_seconds = time.process_time() - cpu_phase
    elif representation != "simplified":
        raise ValueError("Unknown representation")
    phase = time.perf_counter()
    cpu_phase = time.process_time()
    prepared, transformations = simplify_model(model)
    simplification_seconds = time.perf_counter() - phase
    simplification_cpu_seconds = time.process_time() - cpu_phase
    phase = time.perf_counter()
    cpu_phase = time.process_time()
    fingerprint = target_fingerprint(prepared)
    validation_seconds = time.perf_counter() - phase
    validation_cpu_seconds = time.process_time() - cpu_phase
    return prepared, {
        "representation": representation,
        "target_sha256": fingerprint,
        "propagation_seconds": propagation_seconds,
        "propagation_cpu_seconds": propagation_cpu_seconds,
        "simplification_seconds": simplification_seconds,
        "simplification_cpu_seconds": simplification_cpu_seconds,
        "target_validation_seconds": validation_seconds,
        "target_validation_cpu_seconds": validation_cpu_seconds,
        "preparation_seconds": time.perf_counter() - started,
        "preparation_cpu_seconds": time.process_time() - cpu_started,
        "propagation_proof": proof,
        "algebra_transformations": transformations,
    }
