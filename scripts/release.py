"""Validate release versions and publish in dependency order; no embedded credentials."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import tomllib
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("kingfisher-vectorscan-sys", "kingfisher-vectorscan")


def release_version(tag):
    versions = []
    for package in PACKAGES:
        with (ROOT / package / "Cargo.toml").open("rb") as source:
            manifest = tomllib.load(source)
        assert manifest["package"]["name"] == package
        versions.append(manifest["package"]["version"])
        if package == "kingfisher-vectorscan":
            assert manifest["dependencies"][PACKAGES[0]]["version"] == versions[0]
    assert len(set(versions)) == 1, "Both crates must have the same version"
    assert re.fullmatch(r"v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", tag), "Expected vX.Y.Z tag"
    assert tag == f"v{versions[0]}", "Tag must match both crate versions"
    return versions[0]


def published(package, version):
    request = Request(
        f"https://crates.io/api/v1/crates/{package}/{version}",
        headers={"User-Agent": "kingfisher-vectorscan-release (github.com/micksmix/kingfisher-vectorscan)"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            data = json.load(response)
        assert not data["version"]["yanked"], "Refusing to use a yanked release"
        return True
    except HTTPError as error:
        if error.code == 404:
            return False
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--package", choices=PACKAGES)
    args = parser.parse_args()
    version = release_version(args.tag)
    if args.package is None:
        print(f"Validated release {args.tag}")
        return
    if published(args.package, version):
        print(f"{args.package} {version} already published; leaving it unchanged")
        return
    if not os.environ.get("CARGO_REGISTRY_TOKEN"):
        raise SystemExit("Configure CARGO_REGISTRY_TOKEN or crates.io Trusted Publishing")
    # Only the release manifest may differ from the tag. It is generated from
    # tested release assets and must be included in the immutable registry archive.
    changes = subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=ROOT, text=True).splitlines()
    assert set(changes) <= {"kingfisher-vectorscan-sys/prebuilt-manifest.txt"}, "Unexpected release checkout changes"
    from native import TARGETS
    lines = (ROOT / PACKAGES[0] / "prebuilt-manifest.txt").read_text().splitlines()
    entries = [line.split() for line in lines if line and not line.startswith("#")]
    assert len(entries) == len(TARGETS) and all(len(row) == 3 and row[0] == version for row in entries)
    assert {row[1] for row in entries} == set(TARGETS), "Missing release targets"
    subprocess.run(["cargo", "publish", "-p", args.package, "--allow-dirty", "--dry-run"], cwd=ROOT, check=True)
    subprocess.run(["cargo", "publish", "-p", args.package, "--allow-dirty"], cwd=ROOT, check=True)
    for _ in range(30):
        if published(args.package, version):
            return
        time.sleep(10)
    raise SystemExit("Registry did not confirm publication within five minutes; inspect before retrying")


if __name__ == "__main__":
    main()
