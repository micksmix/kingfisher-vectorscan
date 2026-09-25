//! Release archives are authenticated by hashes embedded in the immutable crate.
use flate2::read::GzDecoder;
use sha2::{Digest, Sha256};
use std::{
    collections::HashSet,
    fs,
    io::{Read, Write},
    path::{Component, Path, PathBuf},
    process::Command,
};

const MAX_ARCHIVE: u64 = 128 * 1024 * 1024;
const MAX_UNPACKED: u64 = 512 * 1024 * 1024;

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

pub fn checksum(manifest: &str, version: &str, target: &str) -> Result<Option<String>> {
    let mut seen = HashSet::new();
    let mut found = None;
    for line in manifest
        .lines()
        .filter(|line| !line.trim().is_empty() && !line.starts_with('#'))
    {
        let fields: Vec<_> = line.split_whitespace().collect();
        if fields.len() != 3
            || fields[0] != version
            || !fields[1]
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || c == b'-' || c == b'_')
            || fields[2].len() != 64
            || !fields[2].bytes().all(|c| c.is_ascii_hexdigit())
            || !seen.insert(fields[1])
        {
            return Err("invalid, duplicate, or wrong-version prebuilt manifest entry".into());
        }
        if fields[1] == target {
            found = Some(fields[2].to_ascii_lowercase());
        }
    }
    Ok(found)
}

pub fn verify(path: &Path, expected: &str) -> Result<()> {
    let file = fs::File::open(path)?;
    if file.metadata()?.len() > MAX_ARCHIVE {
        return Err("archive exceeds size limit".into());
    }
    let mut hash = Sha256::new();
    std::io::copy(&mut file.take(MAX_ARCHIVE + 1), &mut hash)?;
    if format!("{:x}", hash.finalize()) != expected {
        return Err("archive SHA-256 mismatch".into());
    }
    Ok(())
}

pub fn unpack(path: &Path, destination: &Path) -> Result<()> {
    fs::create_dir_all(destination)?;
    let mut archive = tar::Archive::new(GzDecoder::new(fs::File::open(path)?));
    let mut size = 0u64;
    let mut seen = HashSet::new();
    for entry in archive.entries()? {
        let mut entry = entry?;
        let path = entry.path()?.into_owned();
        let safe_root = matches!(path.components().next(), Some(Component::Normal(p)) if p == "lib" || p == "include" || p == "licenses");
        if !safe_root
            || !path.components().all(|c| matches!(c, Component::Normal(_)))
            || !seen.insert(path.clone())
            || !(entry.header().entry_type().is_file() || entry.header().entry_type().is_dir())
        {
            return Err(format!("unsafe archive entry: {}", path.display()).into());
        }
        size = size
            .checked_add(entry.size())
            .ok_or("archive size overflow")?;
        if size > MAX_UNPACKED {
            return Err("unpacked archive exceeds size limit".into());
        }
        if !entry.unpack_in(destination)? {
            return Err("archive path escapes destination".into());
        }
    }
    if !destination.join("lib/libhs.a").is_file() || !destination.join("include/hs/hs.h").is_file()
    {
        return Err("archive is missing Vectorscan library or headers".into());
    }
    Ok(())
}

pub fn install(manifest: &str, version: &str, target: &str, out: &Path) -> Result<Option<PathBuf>> {
    let Some(hash) = checksum(manifest, version, target)? else {
        return Ok(None);
    };
    let name = format!("vectorscan-{version}-{target}.tar.gz");
    let cache = out.join(&name);
    println!("cargo:rerun-if-env-changed=VECTORSCAN_PREBUILT_DIR");
    if let Some(directory) = std::env::var_os("VECTORSCAN_PREBUILT_DIR") {
        let local = PathBuf::from(directory).join(&name);
        println!("cargo:rerun-if-changed={}", local.display());
        verify(&local, &hash)?;
        fs::copy(local, &cache)?;
    } else if !cache.is_file() {
        if ["VECTORSCAN_OFFLINE", "CARGO_NET_OFFLINE"]
            .iter()
            .any(|key| matches!(std::env::var(key).as_deref(), Ok("1" | "true")))
        {
            return Err("offline mode requested but release archive is not cached".into());
        }
        let url = format!(
            "https://github.com/micksmix/kingfisher-vectorscan/releases/download/v{version}/{name}"
        );
        let partial = out.join(format!("{name}.partial"));
        // curl is provided by macOS and Windows, and is a small Linux prerequisite.
        // Avoid adding another native TLS build dependency merely to fetch native code.
        let curl = if cfg!(windows) { "curl.exe" } else { "curl" };
        let status = Command::new(curl)
            .args([
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--proto",
                "=https",
                "--proto-redir",
                "=https",
                "--retry",
                "3",
                "--connect-timeout",
                "20",
                "--max-time",
                "300",
                "--max-filesize",
                "134217728",
                "--output",
            ])
            .arg(&partial)
            .arg(&url)
            .status()
            .map_err(|error| format!("cannot run {curl}: {error}"))?;
        if !status.success() {
            let _ = fs::remove_file(&partial);
            return Err(format!("download failed: {url}").into());
        }
        if let Err(error) = verify(&partial, &hash) {
            let _ = fs::remove_file(&partial);
            return Err(error);
        }
        fs::rename(partial, &cache)?;
    }
    verify(&cache, &hash)?;
    let root = out.join("prebuilt");
    if root.exists() {
        fs::remove_dir_all(&root)?;
    }
    fs::create_dir_all(&root)?;
    unpack(&cache, &root)?;
    // Make the selected path visible with cargo -vv, including offline installs.
    writeln!(
        std::io::stderr(),
        "Using verified Vectorscan release archive for {target}"
    )?;
    Ok(Some(root))
}
