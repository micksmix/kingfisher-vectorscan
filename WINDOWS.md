# Windows native library

Published 0.1.1+ crates download and verify the matching static Vectorscan archive
for `x86_64-pc-windows-gnu` (MSYS2 MINGW64) or
`aarch64-pc-windows-gnullvm` (MSYS2 CLANGARM64). Select the Rust target explicitly
with `--target` if your default is MSVC. Keep the matching linker and C++ runtime
libraries installed and on their normal search paths. These are not MSVC archives.
CMake and Boost are only needed to build Vectorscan from source.

Set `VECTORSCAN_PREBUILT_DIR` to use a downloaded release archive offline, or
`HYPERSCAN_ROOT` to link your own compatible static installation. For MSVC,
`HYPERSCAN_ROOT` must contain MSVC-compatible `lib/hs.lib` and headers; no automatic
cross-ABI substitution is attempted. The build script also checks standard vcpkg locations using the MSVC target
architecture. It never selects MSVC libraries for a GNU/LLVM target.

Source checkouts have no release checksums yet and need the native build tools.
The `build-from-source` feature (or `VECTORSCAN_BUILD_FROM_SOURCE=1`) also compiles
the bundled source. Set `CC`, `CXX`, and `CMAKE_GENERATOR=MinGW Makefiles` for the
chosen environment. Do not combine source options with `HYPERSCAN_ROOT`.
The following external-install recipe remains useful for custom native builds.

From an MSYS2 MINGW64 shell (x64) or CLANGARM64 shell (ARM64), install the matching
C/C++ toolchain, CMake, Make, and Boost packages. From this repository root:

```sh
cmake -S kingfisher-vectorscan-sys/vectorscan -B native-build \
  -G 'MinGW Makefiles' \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON \
  -DBUILD_UNIT=OFF -DBUILD_TOOLS=OFF -DFAT_RUNTIME=OFF \
  -DCMAKE_INSTALL_PREFIX="$MINGW_PREFIX"
cmake --build native-build --parallel
cmake --install native-build
export HYPERSCAN_ROOT="$(cygpath -m "$MINGW_PREFIX")"
cargo test --workspace --all-targets
```

Use Rust target `x86_64-pc-windows-gnu` in MINGW64 and
`aarch64-pc-windows-gnullvm` in CLANGARM64. Set that target explicitly if it is
not your active Rust toolchain's default. This build flow is verified by CI on both Windows architectures, with explicit
compiler and architecture settings in `.github/workflows/ci.yml`.
The build script selects static C++ runtime libraries by target environment.
MSVC is a separate configuration requiring compatible MSVC native libraries.

For MinGW GCC, the build script queries the configured C compiler/linker driver for
`libgcc.a` and adds its versioned directory to Rust’s native library search path.
Set `CC` if the intended GCC driver is not the default one on PATH.
