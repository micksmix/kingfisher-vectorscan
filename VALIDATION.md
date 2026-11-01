# Local preparation checks

## VS 2022 archive baseline, 2026-11-01

Prepared version: **0.1.4**, not published. Environment: VMware Fusion Windows
11 ARM64, Rust 1.99.0, VS 2022 / MSVC **14.44.35207**, and checksum-verified
**Boost 1.88.0** matching release CI. The initial correctness run used clang-cl
**19.1.5**; the accepted performance configuration uses **22.1.3**. ARM64 ran natively;
x64 ran under Windows emulation. VS 2026 / MSVC **14.51.36231** remained installed
side-by-side for newer-consumer checks; no IDE/runtime uninstall was needed.

The initial correctness run passed on both MSVC target architectures:

- Optimized native archive production with the existing engine/SIMD flags unchanged.
- Baseline-drift checks and library-hash-bound `lib/build-toolchain.json` archive metadata.
- Source and prebuilt Rust tests, scan example and independently verified sys-crate package.
- Complete public native suite and **14,162 internal native tests** per architecture.
- The same Boost 1.88 / MSVC 14.44 archives consumed with separately selected
  VS 2022 **14.44** and VS 2026 **14.51** SDK/STL environments, in toolset-keyed
  consumer target directories with deliberately invalid native C++/CMake commands.
- Selector isolation **14.44 → 14.51 → 14.44** without retaining old STL paths.

An initial transport-disconnected Boost 1.88 run was **not** counted as passed.
The successful rerun retained guest stdout/stderr logs and returned exit code zero.
An earlier Boost 1.90 local pass was superseded by the release-matching 1.88 run.

macOS ARM64 checks passed: workspace/all-target tests, Clippy with warnings denied,
optimized synthetic throughput example, and fresh verified package archives for
both crates. Release-helper tests, PowerShell parsing, actionlint and local doc links passed.
The inherited Rust 1.73 minimum, native x64 hardware and full ten-target release
CI remain outside this local verification. Published 0.1.3 assets/hashes were not changed.

Performance comparison uses the same synthetic Rust source and Rust compiler,
five alternating trials per archive/architecture, and no concurrent guest builds.
The accepted clang 22 results are recorded below; no further performance workaround
or benchmark rerun is required for this change.

The first candidate (clang-cl 19.1.5, Boost 1.88, MSVC 14.44) **failed the performance
acceptance check** despite passing correctness/ABI tests. Relative to published
0.1.3, median ARM64 throughput changed by -35.89% (no match), -36.56% (sparse),
and -12.25% (dense); x64 emulation changed by -1.74%, -3.57%, and +0.42%.
That clang 19 candidate must not be treated as release-ready or performance-equivalent.
The selected clang-cl 22.1.3 code generator keeps the same VS 2022 / 14.44
SDK/STL and unchanged optimization settings; no SIMD/STL disabling workaround is used.

The **clang-cl 22.1.3 / MSVC 14.44 / Boost 1.88** candidate passed old/new SDK
consumer checks and resolved the large throughput regression. Five alternating
optimized trials per archive/architecture produced these median MiB/s values:

| Architecture / workload | Published 0.1.3 | 14.44 + clang 22 candidate | Change |
| --- | ---: | ---: | ---: |
| ARM64 native / no match | 975.328 | 963.021 | -1.26% |
| ARM64 native / sparse | 975.884 | 977.553 | +0.17% |
| ARM64 native / dense | 423.665 | 421.597 | -0.49% |
| x64 emulated / no match | 981.360 | 980.162 | -0.12% |
| x64 emulated / sparse | 965.347 | 975.054 | +1.01% |
| x64 emulated / dense | 193.039 | 194.662 | +0.84% |

Database size was identical (**663,720 bytes**), as were matches per scan
(0 / 119 / 239,675). Median compile time was 150.965 → 150.890 ms on ARM64
and 441.779 → 447.208 ms under x64 emulation. These are local synthetic VM
measurements, not an absolute guarantee for all corpora/CPUs; no large or
consistent scan regression remained. Exact pinned-compiler native suites still
need completion before treating this candidate as fully verified.

## MSVC preparation, 2026-10-31

Validated version: **0.1.3**. Test environment: VMware Fusion,
Windows 11 ARM64, Rust 1.99.0, Visual Studio 2022 Build Tools and LLVM clang-cl
19.1.5 with standalone Boost headers. ARM64 executables ran natively; x64
executables ran under Windows emulation, not on native x64 hardware.

Passed for both `aarch64-pc-windows-msvc` and `x86_64-pc-windows-msvc`:

- Portable Microsoft-ABI source compilation and COFF `lib/hs.lib` archive generation.
- Prebuilt archive tests with deliberately invalid C++/CMake commands, the Rust
  consumer example, and sys-crate archive verification with Cargo.
- Cargo `build-from-source` tests: 10 high-level, 4 FFI layout and 3 archive tests.
- The complete public native suite through `unit_hyperscan`, including the deep
  `regression.UE_2595` case after reserving an 8 MiB executable stack.
- All **14,162 internal native tests** on each architecture.

macOS ARM64 Rust 1.99 checks also passed: workspace/all-target Rust tests, release
build with the public native suite, formatting, release-helper tests, actionlint,
and fresh Cargo package verification for both crates. The high-level package
used an explicit local sys-crate override for 0.1.3.

No native regression was removed or skipped to obtain these results. Native x64
CI, the older Rust 1.73 minimum, optional CPU/AVX/SVE specialization and the
static-CRT source path remain unverified by this local run. All ten release
archive targets must pass CI before publication; previous release assets remain
immutable. See [Windows setup](WINDOWS.md) and [release guidance](RELEASING.md).

## Initial extraction checks (historical)

Environment: macOS ARM64, Rust 1.96.0.

Passed:

- `cargo test --workspace --all-targets`: 11 high-level tests and 4 FFI layout tests.
- `cargo test -p kingfisher-vectorscan --doc`: succeeds (no doctests defined).
- `cargo run -p kingfisher-vectorscan --example scan`: pattern 0 ends at byte 5.
- `cargo fmt --all --check`.
- `cargo package -p kingfisher-vectorscan-sys --allow-dirty`: creates and independently
  compiles the crate archive (approximately 1.9 MiB compressed).
- Package file inspection confirms NOTICE and all three license files in both
  crates' package lists and the generated native parser in the sys archive.
- Local links in the new documentation resolve.
- All 937 native source files are byte-for-byte identical to Kingfisher's
  vendored snapshot (excluding macOS filesystem metadata).
- Staged whitespace check passes outside the preserved native sources.
  Native source whitespace warnings are inherited from the snapshot.

Known inherited limitation:

`cargo test --workspace --doc` explicitly forces a sys-crate doctest from generated
C documentation, which fails because an indented prose list is parsed as Rust.
The sys manifest already has `doctest = false`; use the documented high-level-only
doctest command. No generated bindings were changed to hide this inherited issue.

Not verified here:

- The inherited Rust 1.73 minimum: only the installed Rust 1.96 toolchain was used.
- CPU specialization features: not exercised in the extraction checks.
- Kingfisher integration: its working tree is unchanged until the later cutover
  described in RELEASING.md.

These checks describe the initial extraction. Remote CI and publication status
are recorded by GitHub Actions; local checks do not establish cross-platform success.

## Release automation checks

- `actionlint` passes for build and publishing workflows.
- Release tag guard accepts v0.1.0 and rejects mismatched versions/non-tag input.
- macOS ARM64 release build with `unit_hyperscan` and `gen` passes:
  all 2,997 native tests and 11 high-level Rust tests pass with regenerated bindings.
- [CI for commit 24e6b22](https://github.com/micksmix/kingfisher-vectorscan/actions/runs/36103327174)
  passes on Linux x64/ARM64, macOS ARM64, and Windows x64/ARM64.
  Unix jobs verify native tests, regenerated bindings, and the packaged sys crate.
  Windows jobs build native Vectorscan and run the Rust tests and example.
- Windows x64 CI initially exposed the missing GCC runtime search directory.
  The sys build script now obtains it from the configured compiler; the corrected
  build passed both Windows architectures without Kingfisher's Makefile flags.

## Published release

[Release run for v0.1.0](https://github.com/micksmix/kingfisher-vectorscan/actions/runs/36103574877)
completed successfully. All five platform jobs passed, and Cargo verified and
published both crates, with the sys crate first and the high-level crate resolved
against that published registry dependency. Both version 0.1.0 entries were
confirmed through the crates.io API and are not yanked.
