# Windows native library

The sys crate inherits Kingfisher's external-library linkage. It does not invoke
Kingfisher or require its repository, but Windows users must install the native
library before building the Rust crates.

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
not your active Rust toolchain's default. The recipe is adapted from the
Kingfisher build; it has not been executed for this standalone fork.
The build script selects static C++ runtime libraries by target environment.
MSVC is a separate configuration requiring compatible MSVC native libraries.

For MinGW GCC, the build script queries the configured C++ compiler for
`libgcc.a` and adds its versioned directory to Rust’s native library search path.
Set `CXX` if the intended compiler is not the default one on PATH.
