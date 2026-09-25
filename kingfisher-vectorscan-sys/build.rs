use std::path::PathBuf;
#[cfg(feature = "unit_hyperscan")]
use std::process::Command;

#[path = "build_support/prebuilt.rs"]
mod prebuilt;

fn env(name: &str) -> String {
    std::env::var(name).unwrap_or_else(|_| panic!("`{name}` should be set in the environment"))
}

fn main() {
    for path in [
        "build.rs",
        "build_support",
        "prebuilt-manifest.txt",
        "vectorscan",
        "src/bindings.rs",
        "wrapper.h",
    ] {
        println!("cargo:rerun-if-changed={path}");
    }
    for name in [
        "HYPERSCAN_ROOT",
        "VCPKG_ROOT",
        "TEMP",
        "VECTORSCAN_BUILD_FROM_SOURCE",
        "VECTORSCAN_PREBUILT_DIR",
        "VECTORSCAN_OFFLINE",
        "CARGO_NET_OFFLINE",
        "CXXSTDLIB",
    ] {
        println!("cargo:rerun-if-env-changed={name}");
    }
    let target = env("TARGET");
    let out = PathBuf::from(env("OUT_DIR"));
    let source = cfg!(feature = "build-from-source")
        || cfg!(feature = "cpu_native")
        || cfg!(feature = "simd_specialization")
        || cfg!(feature = "unit_hyperscan")
        || cfg!(feature = "asan")
        || std::env::var("VECTORSCAN_BUILD_FROM_SOURCE").as_deref() == Ok("1");
    if (cfg!(feature = "cpu_native") || cfg!(feature = "simd_specialization"))
        && env("HOST") != target
    {
        panic!("CPU specialization requires a native build (HOST must equal TARGET)");
    }
    let external = std::env::var_os("HYPERSCAN_ROOT").map(PathBuf::from);
    assert!(
        !(source && external.is_some()),
        "Source-build options conflict with HYPERSCAN_ROOT; unset it to compile the bundled source"
    );
    let root = if let Some(root) = external {
        root
    } else if !source {
        match prebuilt::install(include_str!("prebuilt-manifest.txt"), &env("CARGO_PKG_VERSION"), &target, &out) {
            Ok(Some(root)) => root,
            Ok(None) => find_vcpkg(&target).unwrap_or_else(|| build_source(&target)),
            Err(error) => panic!("Prebuilt Vectorscan: {error}. Use VECTORSCAN_PREBUILT_DIR for a verified local archive, HYPERSCAN_ROOT for an installed library, or VECTORSCAN_BUILD_FROM_SOURCE=1"),
        }
    } else {
        build_source(&target)
    };
    assert!(
        root.join("lib/libhs.a").is_file()
            || root.join("lib/hs.lib").is_file()
            || root.join("lib64/libhs.a").is_file(),
        "No static hs library in {}",
        root.display()
    );
    println!(
        "cargo:rustc-link-search=native={}",
        root.join("lib").display()
    );
    println!(
        "cargo:rustc-link-search=native={}",
        root.join("lib64").display()
    );
    println!("cargo:rustc-link-lib=static=hs");
    link_runtime(&target);
    #[cfg(feature = "bindgen")]
    bindgen::Builder::default()
        .allowlist_function("hs_.*")
        .allowlist_type("hs_.*")
        .allowlist_var("HS_.*")
        .header("wrapper.h")
        .clang_arg(format!("--target={target}"))
        .clang_arg(format!("-I{}", root.join("include").display()))
        .generate()
        .expect("Unable to generate bindings")
        .write_to_file(out.join("bindings.rs"))
        .expect("Failed to write bindings");
    #[cfg(not(feature = "bindgen"))]
    std::fs::copy("src/bindings.rs", out.join("bindings.rs")).expect("Failed to copy bindings");
}

// Preserve external MSVC installations without ever selecting MSVC libraries for
// a GNU/LLVM target or selecting x64 libraries for ARM64.
fn find_vcpkg(target: &str) -> Option<PathBuf> {
    let architecture = match target {
        "x86_64-pc-windows-msvc" => "x64",
        "aarch64-pc-windows-msvc" => "arm64",
        _ => return None,
    };
    let roots = [
        std::env::var_os("VCPKG_ROOT").map(PathBuf::from),
        std::env::var_os("TEMP").map(|path| PathBuf::from(path).join("vcpkg")),
        Some(PathBuf::from(r"C:\vcpkg")),
        Some(PathBuf::from(r"C:\dev\vcpkg")),
    ];
    for root in roots.into_iter().flatten() {
        for triplet in [
            format!("{architecture}-windows-static"),
            format!("{architecture}-windows"),
        ] {
            let prefix = root.join("installed").join(triplet);
            println!(
                "cargo:rerun-if-changed={}",
                prefix.join("lib/hs.lib").display()
            );
            if prefix.join("lib/hs.lib").is_file() {
                return Some(prefix);
            }
        }
    }
    None
}

fn link_runtime(target: &str) {
    if target.ends_with("-msvc") {
        return;
    }
    if target.ends_with("-windows-gnullvm") || target.ends_with("-windows-gnu") {
        // Rust needs the target linker toolchain already. Ask its C driver for
        // each archive: the Vectorscan prefix need not be the toolchain prefix.
        // In particular, rustc must find static runtimes before invoking a linker.
        let libraries: &[&str] = if target.ends_with("-gnullvm") {
            &["c++", "c++abi", "unwind"]
        } else {
            &["stdc++", "gcc", "winpthread"]
        };
        let compiler = cc::Build::new().get_compiler();
        for lib in libraries {
            let output = compiler
                .to_command()
                .arg(format!("-print-file-name=lib{lib}.a"))
                .output()
                .expect("Failed to locate Windows target runtime");
            assert!(output.status.success(), "Runtime query failed for {lib}");
            let runtime = PathBuf::from(String::from_utf8(output.stdout).unwrap().trim());
            assert!(runtime.is_file(), "Missing target runtime {}. Install matching MSYS2 runtime/development libraries and set CC to the target's C driver", runtime.display());
            println!(
                "cargo:rustc-link-search=native={}",
                runtime.parent().unwrap().display()
            );
            println!("cargo:rustc-link-lib=static={lib}");
        }
    } else {
        let default = if target.contains("apple") || target.contains("freebsd") {
            "c++"
        } else {
            "stdc++"
        };
        let runtime = std::env::var("CXXSTDLIB").unwrap_or_else(|_| default.into());
        if !runtime.is_empty() {
            println!("cargo:rustc-link-lib={runtime}");
        }
    }
}

fn build_source(target: &str) -> PathBuf {
    assert!(!target.ends_with("-msvc"), "Bundled source builds do not support MSVC; set HYPERSCAN_ROOT to a compatible MSVC static library, or use a supported Windows GNU/LLVM Rust target");
    let vectorscan_src_dir = PathBuf::from(env("CARGO_MANIFEST_DIR")).join("vectorscan");
    let out_dir = PathBuf::from(env("OUT_DIR"));
    let include_dir = out_dir.join("include");
    let mut cfg = cmake::Config::new(&vectorscan_src_dir);

    macro_rules! cfg_define_feature {
        ($cmake_feature: tt, $cargo_feature: tt) => {
            cfg.define(
                $cmake_feature,
                if cfg!(feature = $cargo_feature) {
                    "ON"
                } else {
                    "OFF"
                },
            )
        };
    }

    // Match the established Windows native build recipe even in Rust debug
    // builds. Unoptimized MinGW builds of Vectorscan 5.4.13 can emit duplicate
    // SuperVector copy-constructor definitions; the optimized build links cleanly.
    let profile = if target.contains("windows") {
        "Release"
    } else {
        match env("OPT_LEVEL").as_str() {
            "0" => "Debug",
            "s" | "z" => "MinSizeRel",
            _ => "Release",
        }
    };

    cfg.profile(profile)
        .define("CMAKE_INSTALL_INCLUDEDIR", &include_dir)
        .define("CMAKE_VERBOSE_MAKEFILE", "ON")
        .define("BUILD_SHARED_LIBS", "OFF")
        .define("BUILD_STATIC_LIBS", "ON")
        .define("FAT_RUNTIME", "OFF")
        .define("WARNINGS_AS_ERRORS", "OFF")
        .define("BUILD_EXAMPLES", "OFF")
        .define("BUILD_BENCHMARKS", "OFF")
        .define("BUILD_DOC", "OFF")
        .define("BUILD_TOOLS", "OFF");

    cfg_define_feature!("BUILD_UNIT", "unit_hyperscan");
    cfg_define_feature!("USE_CPU_NATIVE", "cpu_native");

    if cfg!(feature = "asan") {
        cfg.define("SANITIZE", "address");
    }

    if cfg!(feature = "simd_specialization") {
        macro_rules! x86_64_feature {
            ($feature: tt) => {{
                #[cfg(target_arch = "x86_64")]
                if std::arch::is_x86_feature_detected!($feature) {
                    "ON"
                } else {
                    "OFF"
                }
                #[cfg(not(target_arch = "x86_64"))]
                "OFF"
            }};
        }

        macro_rules! aarch64_feature {
            ($feature: tt) => {{
                #[cfg(target_arch = "aarch64")]
                if std::arch::is_aarch64_feature_detected!($feature) {
                    "ON"
                } else {
                    "OFF"
                }
                #[cfg(not(target_arch = "aarch64"))]
                "OFF"
            }};
        }

        cfg.define("BUILD_AVX2", x86_64_feature!("avx2"));
        // XXX use avx512vbmi as a proxy for this, as it's not clear which particular avx512
        // instructions are needed
        cfg.define("BUILD_AVX512", x86_64_feature!("avx512vbmi"));
        cfg.define("BUILD_AVX512VBMI", x86_64_feature!("avx512vbmi"));

        cfg.define("BUILD_SVE", aarch64_feature!("sve"));
        cfg.define("BUILD_SVE2", aarch64_feature!("sve2"));
        cfg.define("BUILD_SVE2_BITPERM", aarch64_feature!("sve2-bitperm"));
    } else {
        cfg.define("BUILD_AVX2", "OFF")
            .define("BUILD_AVX512", "OFF")
            .define("BUILD_AVX512VBMI", "OFF")
            .define("BUILD_SVE", "OFF")
            .define("BUILD_SVE2", "OFF")
            .define("BUILD_SVE2_BITPERM", "OFF");
    }

    // Under cargo-zigbuild for x86_64-unknown-linux-musl, Vectorscan's
    // configure-time probes can incorrectly miss posix_memalign/unistd.
    // Scope this workaround to musl targets only to avoid impacting
    // unrelated native dependencies.
    if target.ends_with("-musl") {
        cfg.define("HAVE_UNISTD_H", "1")
            .define("HAVE_POSIX_MEMALIGN", "1");
    }

    if target.contains("windows") {
        let processor = if target.starts_with("aarch64") {
            "ARM64"
        } else {
            "AMD64"
        };
        cfg.define("CMAKE_SYSTEM_NAME", "Windows")
            .define("CMAKE_SYSTEM_PROCESSOR", processor);
    }
    cfg.define("CMAKE_POSITION_INDEPENDENT_CODE", "ON");
    let dst = cfg.build();
    #[cfg(feature = "unit_hyperscan")]
    {
        let name = if target.contains("windows") {
            "unit-hyperscan.exe"
        } else {
            "unit-hyperscan"
        };
        let result = Command::new(out_dir.join("build/bin").join(name))
            .status()
            .expect("Unable to run native tests");
        assert!(result.success(), "Native tests failed");
    }
    dst
}
