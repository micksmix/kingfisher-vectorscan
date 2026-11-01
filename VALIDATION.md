# Local preparation checks

## MSVC preparation, 2026-10-31

Prepared version: **0.1.3**, not yet published. Test environment: VMware Fusion,
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
used an explicit local sys-crate override because 0.1.3 is not published yet.

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
