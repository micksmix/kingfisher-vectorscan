# Fork 0.1.0

- Discover the MinGW GCC runtime archive without application-specific linker flags.

- Add Linux/macOS/Windows build workflows and a two-crate release workflow
  with initial API-token publishing and subsequent crates.io Trusted Publishing.

- Extract Kingfisher's vendored bindings into independent `kingfisher-vectorscan`
  and `kingfisher-vectorscan-sys` packages.
- Preserve Vectorscan 5.4.13 and the existing portability and serialization changes.
- Include upstream provenance and license notices in both distributable crates.

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## Unreleased (Kingfisher vendored changes)

- Updated the native Vectorscan source from 5.4.12 to 5.4.13 for both Rust crates;
  the Rust API and upstream crate versions remain 0.0.6.
- Preserved local build portability patches and regenerated the regex parser.
- Made native guard-page regression tests portable to Windows using `VirtualAlloc`.
- Track native sources and bindings in Cargo's build-script inputs so incremental
  builds pick up vendored engine upgrades.

## [v0.0.6](https://github.com/bradlarsen/vectorscan-rs/releases/v0.0.6) (2026-03-12)

### Changes
- Upgraded vendored version of Vectorscan from 5.4.11 to 5.4.12 ([#11](https://github.com/bradlarsen/vectorscan-rs/pull/11)).

- Vectorscan is now redistributed as an extracted source directory within the vectorscan-rs-sys tree.
  This replaces the previous pristine tarball + build-time `patch` approach.
  This change was necessary to keep the crate size below the 10MB limit imposed by Crates.io.

- Updated GitHub Actions `checkout` and `upload-artifact` steps to the latest versions.

### Fixes
- Fixed a typo in the build script that caused the `cpu_native` feature to not work ([#12](https://github.com/bradlarsen/vectorscan-rs/pull/12)).


## [v0.0.5](https://github.com/bradlarsen/vectorscan-rs/releases/v0.0.5) (2024-12-09)

### Additions
- Added `BlockDatabase::size` and `StreamingDatabase::size`, which return the size in bytes of the database.
- Added `StreamingDatabase::stream_size`, which returns the size in bytes of a stream for the database.
- A new `asan` feature enables Address Sanitizer in the vendored version of `vectorscan`.


## [v0.0.4](https://github.com/bradlarsen/vectorscan-rs/releases/v0.0.4) (2024-11-07)

### Additions
- The streaming APIs are now exposed ([#5](https://github.com/bradlarsen/vectorscan-rs/pull/5)).

- Documentation has been added for many of the Rust APIs ([#5](https://github.com/bradlarsen/vectorscan-rs/pull/5)).

### Fixes
- Debug builds are fixed on macOS using Xcode 15.


## [v0.0.3](https://github.com/bradlarsen/vectorscan-rs/releases/v0.0.3) (2024-08-21)

### Additions
- Several additional Hyperscan functions are exposed, and exposed types implement more traits ([#3](https://github.com/bradlarsen/vectorscan-rs/pull/3)).
  Specifically, the `Flag`, `Pattern`, `ScanMode`, `Scratch`, and `BlockDatabase` types now implement `Clone`, `Debug`, `Send`, and `Sync`.


## [v0.0.2](https://github.com/bradlarsen/vectorscan-rs/releases/v0.0.2) (2024-04-18)

### Additions
- A new `unit_hyperscan` feature causes the Vectorscan unit test suite to be built and run at crate build time ([#2](https://github.com/bradlarsen/vectorscan-rs/pull/2)).

### Fixes
- The compilation of the vendored version of `vectorscan` no longer uses the `-march=native` C and C++ compiler option when the `cpu_native` feature is not specified ([#1](https://github.com/bradlarsen/vectorscan-rs/pull/1)).
  Previously, `-march=native` was used unconditionally, which could cause non-portable code to be generated, leading to `SIGILL` crashes at runtime.


## [v0.0.1](https://github.com/bradlarsen/vectorscan-rs/releases/v0.0.1) (2024-04-04)

This is the initial release of the `vectorscan-rs` and `vectorscan-rs-sys` crates.
These crates were extracted from the [Nosey Parker project](https://github.com/praetorian-inc/noseyparker).

The `vectorscan-rs-sys` crate builds a vendored copy of [Vectorscan](https://github.com/Vectorcamp/vectorscan) 5.4.11.
The `vectorscan-rs` crate provides minimal Rust bindings to Vectorscan's block-based matching APIs.
