# `kingfisher-vectorscan-sys`


## Overview
This crate implements minimal Rust bindings to the [Vectorscan](https://github.com/Vectorcamp/vectorscan) fork of [Hyperscan](https://github.com/intel/hyperscan), the high-performance regular expression engine.
Published releases starting with 0.1.1 use checksum-verified GitHub release archives
for macOS x64/ARM64, Linux GNU x64/ARM64, Windows GNU x64, and Windows LLVM ARM64.
Rust, the target linker/SDK, C++ runtime libraries, and `curl` are required;
CMake and Boost are unnecessary when using an archive. Linux archives target
Ubuntu 22.04 (glibc 2.35, GCC 11 libstdc++); macOS archives target macOS 11+.
**Windows MSVC has no prebuilt archive and cannot compile the bundled source.**
It requires an externally installed compatible MSVC static library; GNU/LLVM
archives cannot be used with MSVC.

`HYPERSCAN_ROOT` selects an installed static library and headers on any platform.
Use `build-from-source` or `VECTORSCAN_BUILD_FROM_SOURCE=1` for the bundled source.
CPU specialization, native tests, and ASan force source builds. These source
options conflict with `HYPERSCAN_ROOT`. Source checkouts and targets without
archives compile the bundled source; MSVC requires a compatible external installation via `HYPERSCAN_ROOT` or a matching vcpkg layout.

For offline builds, place the original release archive in `VECTORSCAN_PREBUILT_DIR`
and set `VECTORSCAN_OFFLINE=1`. `CARGO_NET_OFFLINE=true` is also honored; Cargo's
`--offline` alone does not sandbox build-script networking. Download failures and
checksum mismatches fail explicitly. The release workflow embeds hashes in the
published crate; source checkouts contain an empty manifest.

See the [repository build guide](https://github.com/micksmix/kingfisher-vectorscan#build-requirements-and-portability)
and [Windows guide](https://github.com/micksmix/kingfisher-vectorscan/blob/main/WINDOWS.md).


## Use from Cargo.toml

```toml
[dependencies]
kingfisher-vectorscan-sys = "0.1.1"
```

Run `cargo build --release`. On the supported targets above, this automatically
fetches and links Vectorscan without compiling its C/C++ source locally. Your Rust
code and the bindings still compile normally. Prefer the high-level
`kingfisher-vectorscan` crate unless you need raw FFI.

## Dependencies for source builds

To build the bundled library yourself, change the dependency to:

```toml
[dependencies]
kingfisher-vectorscan-sys = { version = "0.1.1", features = ["build-from-source"] }
```

Install the following dependencies and run `cargo build --release`. This does
not enable MSVC source builds; see the Windows guide above.

- C/C++ compiler and Make or Ninja
- [Boost](https://boost.org) >= 1.57
- [CMake](https://cmake.org)
- Optional: [Clang](https://clang.llvm.org), when building with the `gen` feature

CI exercises Linux and macOS on x64/ARM64 and both supported Windows targets.


## Implementation Notes
This crate was originally written as part of [Nosey Parker](https://github.com/praetorian-inc/noseyparker).
It was adapted from the [pyperscan](https://github.com/vlaci/pyperscan) project, which uses Rust to expose Hyperscan to Python.
(That project is released under either the Apache 2.0 or MIT license.)

Bindings include block and streaming matching and database serialization APIs.
Other features, such as the Chimera PCRE library, test code, benchmark code, and supporting utilities are disabled.

The source of Vectorscan 5.4.13 is included as an extracted source directory in [`vectorscan/`](vectorscan/).
It comes from [the upstream release](https://github.com/VectorCamp/vectorscan/releases/tag/vectorscan%2F5.4.13),
commit `acd7363aadea43da9c5246542d9969db843dd132`. The SHA-256 of the
[source archive](https://codeload.github.com/VectorCamp/vectorscan/tar.gz/refs/tags/vectorscan/5.4.13)
is `11bfcd2dde32d8a08d1a2eebb09294b12a3fa2be140078f8091b751fa1fabd89`.

Local packaging changes preserve optional CPU-native tuning and warnings-as-errors,
and use checked-in Ragel output so consumers do not need Ragel. `src/parser/Parser.cpp`
was regenerated with Ragel 6.11 using `ragel ./src/parser/Parser.rl -o ./src/parser/Parser.cpp -T0`
from the `vectorscan/` directory. The other generated parsers have unchanged inputs.
As before, the large upstream regression data files are omitted, with their dependent
tests disabled. The Windows `std::min` type fix is now included upstream.
The page-boundary regression tests use `VirtualAlloc` on Windows and `mmap` on
Unix so the guard-page checks also run under MSYS2 CLANGARM64.


## License
This project is licensed under either of

- [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0)
  ([LICENSE-APACHE](LICENSE-APACHE))

- [MIT License](https://opensource.org/licenses/MIT)
  ([LICENSE-MIT](LICENSE-MIT))

at your option.

This project contains a vendored copy of [Vectorscan](https://github.com/Vectorcamp/vectorscan), which is released under a 3-clause BSD license ([LICENSE-VECTORSCAN](LICENSE-VECTORSCAN)).


## Contributing
Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in `kingfisher-vectorscan-sys` by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without any additional terms or conditions.
