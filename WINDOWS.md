# Windows native library

## MSVC limitation

**There are no MSVC prebuilt archives, and the bundled Vectorscan source does
not support MSVC.** This includes `x86_64-pc-windows-msvc` and
`aarch64-pc-windows-msvc`, which are commonly the default Rust targets on Windows.
The `build-from-source` feature does not remove this limitation.

Use a supported GNU/LLVM target below, or supply an independently built,
MSVC-compatible static library and headers via `HYPERSCAN_ROOT` (with
`lib/hs.lib` and `include/hs/hs.h`). The build script also checks standard vcpkg
locations for the MSVC target architecture. Discovery does not build an MSVC
library for you. GNU/LLVM archives cannot be linked into an MSVC project.

## Use prebuilt archives from Cargo.toml

```toml
[dependencies]
kingfisher-vectorscan = "0.1.1"
```

Published 0.1.1+ crates download and verify the matching static Vectorscan archive.
Cargo still compiles the Rust code, but Vectorscan needs no local C/C++ compilation,
CMake, or Boost. Keep the matching linker and static C++ runtime libraries installed.
The MSYS2 toolchain packages below provide these together with compiler drivers.

For x64, run in an **MSYS2 MINGW64** shell:

```sh
pacman -S --needed mingw-w64-x86_64-toolchain
rustup target add x86_64-pc-windows-gnu
CC=gcc cargo build --release --target x86_64-pc-windows-gnu
```

For ARM64, run in an **MSYS2 CLANGARM64** shell:

```sh
pacman -S --needed mingw-w64-clang-aarch64-toolchain
rustup target add aarch64-pc-windows-gnullvm
CC=clang cargo build --release --target aarch64-pc-windows-gnullvm
```

Install Rust/rustup first and make it available in the MSYS2 shell. Select the
target explicitly even when the active Rust toolchain defaults to MSVC.
`curl.exe`, supplied with current Windows installations, is used for downloads.
The build script queries the configured C compiler/linker driver for each static
C++ runtime archive. No C++ compilation is performed for prebuilt Vectorscan.

For offline builds, set `VECTORSCAN_PREBUILT_DIR` to a directory containing the
original release archive and set `VECTORSCAN_OFFLINE=1`. Archive checksums are
still verified. Use Windows paths (for example `C:/native-archives`) for these
variables in MSYS2, or convert with `cygpath -m`.

## Building from source

To build Vectorscan yourself in a consuming project:

```toml
[dependencies]
kingfisher-vectorscan = { version = "0.1.1", features = ["build-from-source"] }
```

For x64, in the **MINGW64** shell:

```sh
pacman -S --needed mingw-w64-x86_64-toolchain mingw-w64-x86_64-cmake mingw-w64-x86_64-boost make
rustup target add x86_64-pc-windows-gnu
CC=gcc CXX=g++ CMAKE_GENERATOR='MinGW Makefiles' \
  cargo build --release --target x86_64-pc-windows-gnu
```

For ARM64, in the **CLANGARM64** shell:

```sh
pacman -S --needed mingw-w64-clang-aarch64-toolchain mingw-w64-clang-aarch64-cmake mingw-w64-clang-aarch64-boost make
rustup target add aarch64-pc-windows-gnullvm
CC=clang CXX=clang++ CMAKE_GENERATOR='MinGW Makefiles' \
  cargo build --release --target aarch64-pc-windows-gnullvm
```

Alternatively, set `VECTORSCAN_BUILD_FROM_SOURCE=1` instead of enabling the
feature. Source checkouts already select source builds because their release
manifest is empty. Do not combine source options with `HYPERSCAN_ROOT`.
Windows source builds use an optimized native Release configuration even when
Rust uses debug mode, avoiding duplicate template symbols in unoptimized MinGW
builds. CI exercises both Windows architectures for source and prebuilt builds.

### Build a separate native installation

From this repository root, with the matching dependencies above plus Python,
use the same packaging script as CI:

```sh
# MINGW64 x64:
CC=gcc CXX=g++ python3 scripts/native.py build --target x86_64-pc-windows-gnu
# Or CLANGARM64 ARM64:
CC=clang CXX=clang++ python3 scripts/native.py build --target aarch64-pc-windows-gnullvm
```

The script creates a native installation under `native-install` and
an archive under `native-archives`. Set `HYPERSCAN_ROOT` to the absolute Windows
path of that installation to use your own build. Disable `build-from-source`
and unset `VECTORSCAN_BUILD_FROM_SOURCE` when using this external installation.
Your own archive will not match the checksums for official release assets;
use the installation override rather than `VECTORSCAN_PREBUILT_DIR` for it.
