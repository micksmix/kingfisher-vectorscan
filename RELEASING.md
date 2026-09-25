# Releases and crates.io publishing

The repository contains two independently publishable crates in one workspace:
`kingfisher-vectorscan-sys` (native library and FFI), followed by
`kingfisher-vectorscan` (ergonomic Rust API). Keep their versions synchronized.

The fork preserves bradlarsen/vectorscan-rs v0.0.6 history and explicit NOTICE
attribution. Local `origin` uses the personal SSH alias
`git@githubmg:micksmix/kingfisher-vectorscan.git`; public URLs use github.com.

## Native archive pipeline (0.1.1+)

`ci.yml` calls `native.yml`, which builds portable static Vectorscan archives for
Linux GNU, macOS, and Windows GNU/LLVM, on x64 and ARM64 runners. Linux uses Ubuntu
22.04; macOS has deployment target 11.0. CPU-native and optional SIMD specialization
are disabled. Archives contain `lib/libhs.a`, headers, and license notices.
They deliberately do not redistribute toolchain C++ runtimes.

Every archive is tested through the Rust APIs and `cargo package`, with an invalid
CMake/C++ compiler path and offline mode, so a source fallback fails the job.
Regular CI continues to exercise source builds and the native suite. Tests use
Rust 1.96.0; the inherited 1.73 minimum remains unverified.

The tag-triggered publishing job downloads the six tested artifacts, creates a
GitHub release, embeds their SHA-256 hashes in
`kingfisher-vectorscan-sys/prebuilt-manifest.txt`, and packages/publishes the crates.
Only that generated manifest may differ from the tag when publishing. The crate
archive's checksum authenticates the manifest; consumer builds never trust a
checksum fetched alongside a GitHub asset. Hash mismatches fail closed.

A retry reuses and verifies existing GitHub release assets without overwriting
them. If a GitHub release exists but lacks a complete valid set, publication
fails; complete/recover that release before retrying. Do not replace an asset
already referenced by a published crate. A branch push only builds/tests and
uploads workflow artifacts; it does not create releases or publish crates.

Local archive testing, from the repository root:

```sh
python3 scripts/native.py build --target aarch64-apple-darwin
python3 scripts/native.py manifest
VECTORSCAN_PREBUILT_DIR="$PWD/native-archives" VECTORSCAN_OFFLINE=1 cargo test --workspace --all-targets
```

Choose your actual native Rust target. Restore the empty manifest after local
testing (`git restore kingfisher-vectorscan-sys/prebuilt-manifest.txt`); only the
release pipeline populates it for publication. Python 3.11+ is preferred; Ubuntu
22.04 jobs use the `python3-tomli` compatibility package with Python 3.10.

## First publication (API token)

1. Sign into crates.io with the intended crate-owning account and verify its email.
2. Create a short-lived token named `kingfisher-vectorscan-bootstrap` with scopes
   **publish-new** and **publish-update**. Restrict its crate pattern to
   `kingfisher-vectorscan*`. No change-owners, yank, or trusted-publishing scope
   is needed for this workflow.
3. In this GitHub repository, create an Actions environment named **crates-io**
   and store the token there as **CARGO_REGISTRY_TOKEN** (a repository Actions
   secret with that name also works). Do not commit or paste the token into chat.
4. Create/push tag **v0.1.0** at the reviewed commit to trigger **Publish crates**.
   Tag-triggered runs use the bootstrap secret while it exists, and use OIDC
   after the secret is removed. Manual runs can select the tag and check
   **bootstrap**. The workflow requires a tag matching both package versions,
   reruns CI, packages/verifies, and publishes the sys crate first.
5. After both crates exist, configure Trusted Publishing below and revoke the
   bootstrap token and delete the GitHub Actions secret.

A normal branch push never publishes. The workflow skips versions already present
on crates.io so a partial two-crate release can be retried. It fails on registry
errors and yanked versions; it does not overwrite or modify published versions.

## Subsequent releases (Trusted Publishing)

In the crates.io settings for **each** crate, add the same GitHub publisher:

| Field | Value |
| --- | --- |
| Repository owner | `micksmix` |
| Repository name | `kingfisher-vectorscan` |
| Workflow filename | `publish.yml` |
| Environment | `crates-io` |

The workflow requests short-lived OIDC credentials with
`rust-lang/crates-io-auth-action`. There is no API-token secret needed in this mode.
See https://crates.io/docs/trusted-publishing for current registry requirements.

Update both package versions, the high-level sys dependency version, workspace
version, and changelog together. Push the matching `vX.Y.Z` tag to trigger the workflow, or manually dispatch
it against that tag with **bootstrap** unchecked. Creating a GitHub release
for an already pushed tag does not trigger a second publication.

Before release, review CI results and the declared minimum Rust version. Crates.io
publication is permanent, and the sys crate must be indexed before the high-level
crate's registry dependency can be verified. Cargo publish waits for indexing;
the helper also checks registry confirmation. No credentials are stored locally
by these scripts.

## Kingfisher cutover

Kingfisher remains unchanged during this unpublished preparation, so fresh clones,
packaging, and Windows builds still have their current source and notices.

For a local integration trial, replace **both** `vectorscan-rs = "0.0.6"`
entries in Kingfisher's root Cargo.toml (workspace dependencies and direct
dependencies) with:

```toml
vectorscan-rs = { package = "kingfisher-vectorscan", version = "0.1.0", path = "../kingfisher-vectorscan/kingfisher-vectorscan" }
```

Remove the two old vectorscan entries from `[patch.crates-io]`. The Rust import
name remains `vectorscan_rs`; no consumer API changes are required. Regenerate
Cargo.lock and test the rule crate, scanner crate, and application.

After publication, remove the local `path` attribute. Before deleting
`vendor/vectorscan-rs`, complete these dependent changes together:

- Keep a copy of this fork's NOTICE in Kingfisher and update the Cargo.toml
  deb/RPM asset paths and Makefile notice-copy path.
- Move the native source acquisition/build responsibility in both Windows
  Makefile targets to a pinned archive from this repository (or a separately
  installed native library). Those targets currently read native sources from
  the old vendor tree. Do not silently drop the Windows native build step.
- Update third-party notices and any vendor-path documentation, regenerate
  Cargo.lock, and run the affected tests on Windows x64 and ARM64 as well as
  macOS/Linux.

The local dependency trial alone does not complete the Windows/packaging cutover.
