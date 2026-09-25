# `kingfisher-vectorscan-sys`


## Overview
This crate implements minimal Rust bindings to the [Vectorscan](https://github.com/Vectorcamp/vectorscan) fork of [Hyperscan](https://github.com/intel/hyperscan), the high-performance regular expression engine.
On macOS/Linux this crate builds vendored Vectorscan from source. On Windows it links an externally installed library using `HYPERSCAN_ROOT`.


## Dependencies
- [Boost](https://boost.org) >= 1.57
- [CMake](https://cmake.org)
- Optional: [Clang](https://clang.llvm.org), when building with the `bindgen` feature

This has been tested on x86_64 Linux, x86_64 macOS, and aarch64 macOS.


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
