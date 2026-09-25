# Releases and crates.io publishing

The repository contains two independently publishable crates in one workspace:
`kingfisher-vectorscan-sys` (native library and FFI), followed by
`kingfisher-vectorscan` (ergonomic Rust API). Keep their versions synchronized.

The fork preserves bradlarsen/vectorscan-rs v0.0.6 history and explicit NOTICE
attribution. Local `origin` uses the personal SSH alias
`git@githubmg:micksmix/kingfisher-vectorscan.git`; public URLs use github.com.

## Build workflow

`.github/workflows/ci.yml` runs on main/codex branch pushes, pull requests, manual
runs, and release-workflow calls. It tests Linux x64/ARM64, macOS ARM64, and
Windows x64/ARM64. Unix jobs also exercise regenerated bindings and the native
unit suite; Windows jobs build and install native Vectorscan before Rust tests.
CI uses Rust 1.96.0. The inherited 1.73 manifest minimum remains unverified.

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
   bootstrap token/remove the secret.

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
