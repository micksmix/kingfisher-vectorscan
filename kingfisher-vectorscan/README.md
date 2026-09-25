# `kingfisher-vectorscan`

## Overview
This crate exposes a more ergonomic Rust interface on top of the native bindings to [Vectorscan](https://github.com/Vectorcamp/vectorscan) that are exposed in the [`kingfisher-vectorscan-sys`](../kingfisher-vectorscan-sys) crate.
The sys crate supplies Vectorscan 5.4.13. From release 0.1.1 onward, published
crates use verified prebuilt native archives on supported macOS, Linux GNU, and
Windows GNU/LLVM targets. Enable `build-from-source` to compile the bundled source.
See the [build guide](https://github.com/micksmix/kingfisher-vectorscan#build-requirements-and-portability)
for target runtime requirements and offline/external-library overrides.

## Use from Cargo.toml

```toml
[dependencies]
kingfisher-vectorscan = "0.1.1"
```

Run `cargo build --release`. On supported targets, Cargo downloads and verifies
the native library automatically; you do not compile Vectorscan locally and do
not need CMake or Boost. Cargo still compiles your Rust application and bindings.
You need Rust, `curl`, the target linker/SDK, and C++ runtime development/linker libraries.
Supported targets are Linux GNU x64/ARM64 (glibc 2.35+, GCC 11-compatible libstdc++),
macOS x64/ARM64 (macOS 11+), Windows `x86_64-pc-windows-gnu` (MSYS2 MINGW64),
and Windows `aarch64-pc-windows-gnullvm` (MSYS2 CLANGARM64).

**Windows MSVC is external-library only:** there are no MSVC prebuilt archives,
and the bundled source does not support MSVC. Default Windows Rust installations
usually select MSVC. Choose a supported GNU/LLVM target or provide a compatible
MSVC static library via `HYPERSCAN_ROOT` or vcpkg; GNU/LLVM archives cannot be
linked into MSVC projects. See the [Windows guide](https://github.com/micksmix/kingfisher-vectorscan/blob/main/WINDOWS.md).

## Build the native library yourself

```toml
[dependencies]
kingfisher-vectorscan = { version = "0.1.1", features = ["build-from-source"] }
```

Install a C/C++ compiler, CMake, Make or Ninja, and Boost headers, then run
`cargo build --release`. On macOS, install Xcode Command Line Tools and
`brew install cmake boost`; on Debian/Ubuntu, install
`build-essential cmake libboost-dev`. Windows GNU/LLVM setup is in the Windows
guide above. This feature does not support MSVC. The environment variable
`VECTORSCAN_BUILD_FROM_SOURCE=1` is an alternative to the feature.

This crate was originally written as part of [Nosey Parker](https://github.com/praetorian-inc/noseyparker).
This crate was adapted from the [pyperscan](https://github.com/vlaci/pyperscan) project, which uses Rust to expose [Hyperscan](https://github.com/intel/hyperscan) to Python.
(That project is released under either the Apache 2.0 or MIT license.)


## License
This project is licensed under either of

- [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0)
  ([LICENSE-APACHE](LICENSE-APACHE))

- [MIT License](https://opensource.org/licenses/MIT)
  ([LICENSE-MIT](LICENSE-MIT))

at your option.


## Contributing
Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in `kingfisher-vectorscan` by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without any additional terms or conditions.
