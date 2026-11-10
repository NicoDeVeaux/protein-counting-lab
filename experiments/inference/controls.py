"""Generate labeled synthetic controls; never present these as protein data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def synthetic_control(
    *, family: str, variables: int, domain_size: int, seed: int,
    interaction_scale: float = 1.0,
) -> dict:
    if family not in ("chain", "cycle", "clique", "random-sparse", "disconnected"):
        raise ValueError("Unknown control graph family")
    if variables < 1 or domain_size < 1 or interaction_scale < 0:
        raise ValueError("Positive counts and nonnegative interaction scale required")
    rng = np.random.default_rng(seed)
    edges = []
    if family in ("chain", "cycle"):
        edges = [(i, i + 1) for i in range(variables - 1)]
        if family == "cycle" and variables > 2:
            edges.append((0, variables - 1))
    elif family == "clique":
        edges = [(i, j) for i in range(variables) for j in range(i + 1, variables)]
    elif family == "random-sparse":
        edges = [(i, j) for i in range(variables) for j in range(i + 1, variables)
                 if rng.random() < min(1.0, 3.0 / max(1, variables - 1))]
    factors = [{"scope": [i], "log_values": rng.normal(size=domain_size).tolist()}
               for i in range(variables)]
    factors.extend({"scope": [i, j],
                    "log_values": (interaction_scale * rng.normal(size=(domain_size, domain_size))).tolist()}
                   for i, j in edges)
    return {
        "schema_version": 1, "kind": "synthetic_control", "log_base": "e",
        "model_id": f"synthetic-{family}-n{variables}-q{domain_size}-seed{seed}",
        "domains": [domain_size] * variables, "factors": factors,
        "metadata": {"generator": "experiments.inference.controls.synthetic_control",
                     "generator_version": 1, "seed": seed, "graph_family": family,
                     "interaction_scale": interaction_scale,
                     "interpretation": "Gaussian log-weight control; not experimental or protein energy data"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=["chain", "cycle", "clique", "random-sparse", "disconnected"], required=True)
    parser.add_argument("--variables", type=int, required=True)
    parser.add_argument("--domain-size", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--interaction-scale", type=float, default=1.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = synthetic_control(family=args.family, variables=args.variables, domain_size=args.domain_size,
                             seed=args.seed, interaction_scale=args.interaction_scale)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
