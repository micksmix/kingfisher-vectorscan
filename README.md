# kingfisher-vectorscan

General-purpose Rust bindings maintained for Kingfisher, built on [Vectorscan](https://github.com/Vectorcamp/vectorscan),
a high-performance regular expression engine derived from Hyperscan.

This is a modified fork of [Bradford Larsen's vectorscan-rs v0.0.6](https://github.com/bradlarsen/vectorscan-rs/releases/tag/v0.0.6),
extracted from Kingfisher's vendored implementation. It has no Kingfisher dependency
and can be used in any Rust application that needs block or streaming regex matching.
See [NOTICE](NOTICE) for attribution and exact source commits.

One repository contains two crates, initially versioned `0.1.0`:

- [`kingfisher-vectorscan`](kingfisher-vectorscan): ergonomic bindings, block and streaming scanners,
  and block database serialization/deserialization.
- [`kingfisher-vectorscan-sys`](kingfisher-vectorscan-sys): raw FFI bindings and native build support,
  including vendored Vectorscan 5.4.13.

Version 0.1.0 is published on crates.io:
[kingfisher-vectorscan](https://crates.io/crates/kingfisher-vectorscan/0.1.0) and
[kingfisher-vectorscan-sys](https://crates.io/crates/kingfisher-vectorscan-sys/0.1.0).

## Usage

```toml
[dependencies]
kingfisher-vectorscan = "0.1.0"
```

```rust
use kingfisher_vectorscan::{BlockDatabase, BlockScanner, Flag, Pattern, Scan};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let database = BlockDatabase::new(vec![
        Pattern::new(b"hello".to_vec(), Flag::default(), None),
    ])?;
    let mut scanner = BlockScanner::new(&database)?;
    scanner.scan(b"hello world", |id, _from, to, _flags| {
        println!("Pattern {id} matched, ending at byte {to}");
        Scan::Continue
    })?;
    Ok(())
}
```

Run the same example with `cargo run -p kingfisher-vectorscan --example scan`.
Existing users can retain `vectorscan_rs` imports by aliasing the package:

```toml
vectorscan-rs = { package = "kingfisher-vectorscan", version = "0.1.0" }
```

## Build requirements and portability

Starting with the planned 0.1.1 release, published crates use prebuilt static
Vectorscan archives from the matching GitHub release on these targets:

| Target | Native runtime requirements |
| --- | --- |
| `x86_64-unknown-linux-gnu`, `aarch64-unknown-linux-gnu` | Ubuntu 22.04 / glibc 2.35 baseline, GCC 11-compatible libstdc++ |
| `x86_64-apple-darwin`, `aarch64-apple-darwin` | macOS 11+, Apple SDK/linker and system libc++ |
| `x86_64-pc-windows-gnu` | MSYS2 MINGW64 linker and static GNU C++ runtime libraries |
| `aarch64-pc-windows-gnullvm` | MSYS2 CLANGARM64 linker and static libc++/libc++abi/unwind libraries |

A normal published-crate build downloads the archive with `curl` (included in
macOS/Windows; install it on Linux) and verifies a SHA-256 hash embedded in the
crate before extracting it under Cargo's `OUT_DIR`. It needs no CMake, Boost,
Ragel, or Vectorscan compilation. Rust and the target's linker, SDK, and C++
runtime libraries are still required. This does not eliminate native build
requirements of other dependencies in an application such as Kingfisher.
Windows MSVC and Linux musl do not have release archives; see [WINDOWS.md](WINDOWS.md)
for Windows target selection and external MSVC libraries.

Build selection and overrides:

- Set `HYPERSCAN_ROOT` to use an installed compatible static library and headers
  on any platform. This takes precedence over downloading.
- Enable `build-from-source` on either crate, or set
  `VECTORSCAN_BUILD_FROM_SOURCE=1`, to compile the bundled Vectorscan source.
  CPU specialization, native unit tests, and ASan features also require source.
  Source options conflict with `HYPERSCAN_ROOT` to avoid silently ignoring them.
- Set `VECTORSCAN_PREBUILT_DIR` to a directory containing the original release
  archive for your target. Its embedded checksum is still enforced.
- Set `VECTORSCAN_OFFLINE=1` (or `CARGO_NET_OFFLINE=true`) to prohibit archive
  downloads. Prepopulate `VECTORSCAN_PREBUILT_DIR` or use an installed library
  or source build. Cargo's `--offline` flag alone does not sandbox build-script
  networking, and `cargo fetch` does not download these native release assets.

Source checkouts have an empty release manifest and build from source. The
publishing workflow fills the manifest from tested assets before packaging.
Unsupported targets also use source builds, except MSVC, which requires an
explicit `HYPERSCAN_ROOT`. A missing download or checksum failure is a hard error
with override instructions; it never silently switches to compiling C++.

Source builds need a C/C++ compiler, CMake, Make or Ninja, and Boost headers
(>= 1.57). For example, Xcode Command Line Tools plus `brew install cmake boost`
on macOS, or `sudo apt-get install build-essential cmake libboost-dev` on Debian/
Ubuntu. The optional sys-crate `gen` feature additionally needs libclang.

Default builds disable optional SIMD specialization. `cpu_native`,
`simd_specialization`, and `fast_nonportable` may produce binaries that only run
on CPUs compatible with the build machine. Database serialization is also tied
to native library and CPU compatibility; it is not a portable interchange format.
Both this fork and upstream declare `links = "hs"`, so Cargo cannot include their
sys crates together in one dependency graph.

The inherited manifest declares Rust 1.73; that minimum has not been revalidated
for this fork's current dependency resolution. Local verification uses Rust 1.96.

## Development and release preparation

```sh
cargo test --workspace --all-targets
cargo test -p kingfisher-vectorscan --doc
cargo package -p kingfisher-vectorscan-sys --allow-dirty
```

See [RELEASING.md](RELEASING.md) for publication order, GitHub fork setup, and
Kingfisher migration. Branch CI builds/tests only; the separate release workflow
publishes after its required tests pass and publishing authentication is configured.

## License

Rust bindings: [Apache-2.0](LICENSE-APACHE) OR [MIT](LICENSE-MIT).
Bundled native Vectorscan: [BSD-3-Clause](LICENSE-VECTORSCAN), with additional
third-party notices in [NOTICE](NOTICE). Both crate archives include these notices.
