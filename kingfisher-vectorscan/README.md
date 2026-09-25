# `kingfisher-vectorscan`

## Overview
This crate exposes a more ergonomic Rust interface on top of the native bindings to [Vectorscan](https://github.com/Vectorcamp/vectorscan) that are exposed in the [`kingfisher-vectorscan-sys`](../kingfisher-vectorscan-sys) crate.
The sys crate supplies Vectorscan 5.4.13. From release 0.1.1 onward, published
crates use verified prebuilt native archives on supported macOS, Linux GNU, and
Windows GNU/LLVM targets. Enable `build-from-source` to compile the bundled source.
See the [build guide](https://github.com/micksmix/kingfisher-vectorscan#build-requirements-and-portability)
for target runtime requirements and offline/external-library overrides.

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
