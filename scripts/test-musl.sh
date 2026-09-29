#!/bin/sh
# Run inside the native-architecture Rust Alpine container from native.yml.
set -eu
apk add --no-cache cmake make g++ boost-dev python3 linux-headers binutils
export CC=gcc CXX=g++
export CARGO_BUILD_TARGET="${NATIVE_TARGET:?Set the musl Rust target}"
export CARGO_TARGET_DIR=/src/target-musl
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-4}"
rustup target add "$NATIVE_TARGET"
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/native.py build --target "$NATIVE_TARGET"
python3 scripts/native.py manifest

# An unavailable C++ compiler and CMake prove consumers use the archive.
# CC remains available to locate the target's static C++ runtime.
export VECTORSCAN_PREBUILT_DIR=/src/native-archives VECTORSCAN_OFFLINE=1
export CXX=vectorscan-cxx-must-not-run CMAKE=vectorscan-cmake-must-not-run
cargo test --workspace --all-targets
cargo run -p kingfisher-vectorscan --example scan
cargo package -p kingfisher-vectorscan-sys --allow-dirty
binary="$CARGO_TARGET_DIR/$NATIVE_TARGET/debug/examples/scan"
if readelf -l "$binary" | grep -q INTERP || readelf -d "$binary" | grep -q NEEDED; then
    echo 'musl example unexpectedly requires a dynamic loader or shared library' >&2
    exit 1
fi

# Keep the explicit source-build escape hatch working too.
export CXX=g++ CMAKE=cmake
cargo test --workspace --all-targets --features build-from-source
