# Native certificate checker

`lean_native.build_checker(build_dir)` copies the unchanged campaign-007 Lean
sources into a fresh local Lake project, verifies Lean 4.35.0 and the exact axiom
reports of all eleven theorems, and builds a native `checker8` executable. It uses
only the already installed toolchain and bundled libraries. No new theorem,
parser or certificate semantics is introduced.

The returned metadata separates proof-audit and native-compilation time and
records source, build configuration and executable digests. `executable` is a
local runtime path; omit it from public result metadata. The binary and Lake
artifacts belong in temporary or task-local tool storage rather than Git.

`check_certificates(executable, requests, timeout=60)` accepts a batch of
`(expected_model, certificate)` pairs. It performs the existing complete-model
binding check, serializes accepted bindings, starts one native checker process,
and parses its results. It performs no build. All of that per-query work belongs
inside the measured certified-method region. A build can be reused across trials,
but its one-off cost must be reported separately. `check_lines` exposes raw decoder
controls and does not bind an external expected model.

The mathematical proof concerns the parsed model. Compiler/runtime, JSON decoding,
model translation and expected-input binding retain the campaign-007 trust
boundary, including raw duplicate-key normalization. Native compilation does not
add native-evaluation axioms to the audited correctness theorems.
