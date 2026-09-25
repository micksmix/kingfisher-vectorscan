#[allow(dead_code)]
#[path = "../build_support/prebuilt.rs"]
mod prebuilt;
use flate2::{write::GzEncoder, Compression};
use sha2::{Digest, Sha256};
use std::{fs, path::Path};

fn archive(path: &Path, link: bool) {
    let mut tar = tar::Builder::new(GzEncoder::new(
        fs::File::create(path).unwrap(),
        Compression::fast(),
    ));
    for name in ["lib/libhs.a", "include/hs/hs.h"] {
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
    archive(&path, false);
    let hash = format!("{:x}", Sha256::digest(fs::read(&path).unwrap()));
    prebuilt::verify(&path, &hash).unwrap();
    prebuilt::unpack(&path, &temp.path().join("good")).unwrap();
    assert_eq!(
        fs::read(temp.path().join("good/lib/libhs.a")).unwrap(),
        b"abc"
    );
    assert!(prebuilt::verify(&path, &"0".repeat(64)).is_err());
    archive(&path, true);
    assert!(prebuilt::unpack(&path, &temp.path().join("bad")).is_err());
    assert!(!temp.path().join("outside").exists());
}
