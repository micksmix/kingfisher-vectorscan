# Local preparation checks

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
