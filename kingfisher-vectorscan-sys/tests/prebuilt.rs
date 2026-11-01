#[allow(dead_code)]
#[path = "../build_support/prebuilt.rs"]
mod prebuilt;
use flate2::{write::GzEncoder, Compression};
use sha2::{Digest, Sha256};
use std::{fs, path::Path};

fn archive(path: &Path, library: &str, link: bool) {
    let mut tar = tar::Builder::new(GzEncoder::new(
        fs::File::create(path).unwrap(),
        Compression::fast(),
    ));
    for name in [library, "include/hs/hs.h"] {
        let mut header = tar::Header::new_gnu();
        header.set_mode(0o644);
        if link {
            header.set_entry_type(tar::EntryType::Symlink);
            header.set_link_name("../../outside").unwrap();
            header.set_size(0);
            header.set_cksum();
            tar.append_data(&mut header, name, &[][..]).unwrap();
        } else {
            header.set_size(3);
            header.set_cksum();
            tar.append_data(&mut header, name, &b"abc"[..]).unwrap();
        }
    }
    tar.into_inner().unwrap().finish().unwrap();
}

#[test]
fn manifest_is_versioned_and_selects_target_not_host() {
    let hash = "a".repeat(64);
    let manifest = format!("0.1.1 x86_64-pc-windows-gnu {hash}\n");
    assert_eq!(
        prebuilt::checksum(&manifest, "0.1.1", "x86_64-pc-windows-gnu").unwrap(),
        Some(hash)
    );
    assert!(
        prebuilt::checksum(&manifest, "0.1.1", "aarch64-apple-darwin")
            .unwrap()
            .is_none()
    );
    assert!(prebuilt::checksum(&manifest, "0.1.2", "x86_64-pc-windows-gnu").is_err());
    assert!(prebuilt::checksum(&manifest.repeat(2), "0.1.1", "x86_64-pc-windows-gnu").is_err());
    assert!(prebuilt::checksum("0.1.1 bad short", "0.1.1", "bad").is_err());
}

#[test]
fn archive_integrity_and_extraction() {
    let temp = tempfile::tempdir().unwrap();
    let path = temp.path().join("native.tar.gz");
    archive(&path, "lib/libhs.a", false);
    let hash = format!("{:x}", Sha256::digest(fs::read(&path).unwrap()));
    prebuilt::verify(&path, &hash).unwrap();
    prebuilt::unpack(&path, &temp.path().join("good")).unwrap();
    assert_eq!(
        fs::read(temp.path().join("good/lib/libhs.a")).unwrap(),
        b"abc"
    );
    assert!(prebuilt::verify(&path, &"0".repeat(64)).is_err());
    archive(&path, "lib/libhs.a", true);
    assert!(prebuilt::unpack(&path, &temp.path().join("bad")).is_err());
    assert!(!temp.path().join("outside").exists());
}

#[test]
fn msvc_archives_use_a_distinct_library_format() {
    for target in ["x86_64-pc-windows-msvc", "aarch64-pc-windows-msvc"] {
        assert_eq!(prebuilt::library_path(target), "lib/hs.lib");
        let temp = tempfile::tempdir().unwrap();
        let path = temp.path().join("native.tar.gz");
        archive(&path, prebuilt::library_path(target), false);
        let root = temp.path().join("native");
        prebuilt::unpack(&path, &root).unwrap();
        assert_eq!(fs::read(root.join("lib/hs.lib")).unwrap(), b"abc");
        assert!(!root.join("lib/libhs.a").exists());
    }
    assert_eq!(
        prebuilt::library_path("x86_64-pc-windows-gnu"),
        "lib/libhs.a"
    );
    assert_eq!(
        prebuilt::library_path("aarch64-pc-windows-gnullvm"),
        "lib/libhs.a"
    );
}
