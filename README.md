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

The initial 0.1.0 release is being prepared; the crates are not published yet.

## Use locally

```toml
[dependencies]
kingfisher-vectorscan = { path = "../kingfisher-vectorscan/kingfisher-vectorscan" }
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
For a future crates.io release, use `kingfisher-vectorscan = "0.1.0"`.
Existing users can retain `vectorscan_rs` imports by aliasing the package:

```toml
vectorscan-rs = { package = "kingfisher-vectorscan", version = "0.1.0" }
```

## Build requirements and portability

On macOS and Linux, Cargo compiles the bundled C++ library. Install a C/C++
compiler, CMake, a build tool (Make or Ninja), and Boost headers (>= 1.57).
For example, `brew install cmake boost` on macOS, or
`sudo apt-get install build-essential cmake libboost-dev` on Debian/Ubuntu.
Generated Ragel parser sources and Rust FFI bindings are included.
The optional sys-crate `gen` feature requires libclang to regenerate bindings.

On Windows, Cargo currently links an **externally built** compatible static
Vectorscan/Hyperscan library. Set `HYPERSCAN_ROOT` to its installation prefix
containing `lib/hs` and headers; choose a library matching the Rust target and
C++ toolchain. The inherited automatic vcpkg discovery handles only x64 layouts;
ARM64 needs an explicit prefix. See [WINDOWS.md](WINDOWS.md) for a standalone
native build recipe. Windows x64 and ARM64 verification remains pending.

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
