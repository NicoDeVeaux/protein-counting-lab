# Established comparator adapter, version 2

This version corrects one resource-setting error in the preserved version-1 adapter. It uses the same pyagrum 3.3.2 engine, normalization, conditional-query normalizer identity, input schema, and locked runtime at `experiments/established/`.

```sh
experiments/established/.venv/bin/python -m experiments.established_v2 MODEL.json --max-table-bytes 134217728 --output RESULT.json
```

The Python `setMaxMemory` documentation says gigabytes, but the pinned C++ `ScheduledInference` and `Scheduler` implementations use **MiB**: the value is multiplied by 1,048,576 bytes. Version 1 passed `1`, unintentionally imposing a 1 MiB native scheduling budget. Version 2 passes **1024 MiB**, matching the original intended 1 GiB setting. The parent's 128/512 MiB external process-RSS limits and per-table limits remain controlling; the native setting is not an RSS guarantee.

The original 828-trial campaign, including 15 `std::bad_alloc` failures, remains unchanged. Bounded post hoc diagnostics on all four distinct affected inputs reproduce the failure with `1`; all four complete with `1024` or default native settings under the 512 MiB, 20-second external watchdog. Those diagnostics identify an adapter confound and do not replace any campaign rows.

`source_proof.json` records pinned source URLs, hashes, diagnostic evidence, and the exact amendment. `tests/test_established_pyagrum_v2.py` repeats the synthetic correctness suite and adds a moderate-clique regression that fails with version 1 and succeeds with version 2.

No full corrected matrix is run by this adapter-preparation task. Its matched rerun requires a separate frozen amendment/manifest. Numerical results remain binary64 approximations, not outward-rounded interval certificates. The parent must continue retaining conversion failures, watchdog terminations, and independent accuracy checks.
