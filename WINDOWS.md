# Windows native library

## MSVC ABI targets (0.1.3)

The **0.1.3** release adds native source builds and
checksum-pinned archive targets for `x86_64-pc-windows-msvc` and
`aarch64-pc-windows-msvc`. Earlier published versions still require an external
MSVC installation; their immutable archives are not changed.

Vectorscan uses GNU language extensions, so source builds use **LLVM clang-cl**
with the **Microsoft SDK, STL and ABI**, not `cl.exe`. The resulting static
`lib/hs.lib` can be consumed by MSVC Rust projects and Node-API addons. MinGW
GNU/LLVM archives are not MSVC-compatible and must never be substituted.

Install Visual Studio 2022 C++ Build Tools, its x64/ARM64 tools and LLVM/Clang
components, a Windows SDK, CMake, Ninja and standalone Boost headers. Do not add
a MinGW include root as Boost's include directory: its CRT headers contaminate
Microsoft builds. Copy only `boost/` to a separate header root if reusing an
MSYS2 Boost installation.

From a PowerShell session in this checkout:

```powershell
rustup target add aarch64-pc-windows-msvc x86_64-pc-windows-msvc
$env:BOOST_ROOT = 'C:\native\boost_1_88_0'
. ./scripts/msvc-env.ps1 -Target aarch64-pc-windows-msvc
cargo test --workspace --all-targets --features build-from-source
```

Use `x86_64-pc-windows-msvc` for x64. `msvc-env.ps1` selects the target Microsoft
SDK environment and clang-cl/Ninja; it does not install dependencies. Cargo's
MSVC source path defaults to Ninja and clang-cl, selecting the target rather than
the host architecture. Windows native code is built in Release even for Rust
debug builds. Native tests use `kingfisher-vectorscan-sys/unit_hyperscan`.

Native executable/test targets reserve an 8 MiB stack, matching common Unix
defaults for deeply recursive compiler regression cases. A static library cannot
set its caller's thread stack: embedders compiling complex custom patterns must
configure an adequate worker stack themselves. The Kingfisher Node binding does
so for rule compilation.

Release archives use the standard dynamic Microsoft CRT (`/MD`); consumers need
the compatible Microsoft C++ runtime. A Rust `crt-static` consumer selects a
matching `/MT` source build rather than mixing the archive's CRT. A supplied
`HYPERSCAN_ROOT` installation must already match the architecture and CRT.
External installations and architecture-specific vcpkg discovery remain supported.

To build a separate prefix or verify a complete MSVC workflow:

```powershell
python scripts/native.py build --target aarch64-pc-windows-msvc --prefix C:\native\vectorscan-arm64
./scripts/test-msvc.ps1 -Target aarch64-pc-windows-msvc -NativeSuite
```

The verification script checks archive use with deliberately invalid C++/CMake
commands, packaged-crate verification, source builds and the native suite. It
restores the original local manifest afterward. CI has separate x64 and ARM64
MSVC jobs in addition to GNU/LLVM jobs. Fusion ARM64 tests and x64 emulation
are not a substitute for native x64 CI.

## Use prebuilt archives from Cargo.toml

```toml
[dependencies]
kingfisher-vectorscan = "0.1.3"
```

Published 0.1.1+ GNU/LLVM crates download and verify the matching static Vectorscan archive.
MSVC archives start with the 0.1.3 release.
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
kingfisher-vectorscan = { version = "0.1.3", features = ["build-from-source"] }
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
