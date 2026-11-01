param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('x86_64-pc-windows-msvc', 'aarch64-pc-windows-msvc')]
    [string] $Target,
    [switch] $NativeSuite,
    [ValidateSet('2022', '2026')]
    [string] $VisualStudio = '2022',
    [string] $Toolset = '14.44',
    [string] $ArchiveDirectory,
    [string] $ClangCl
)

$ErrorActionPreference = 'Stop'
if (-not $ClangCl) { $ClangCl = $env:KINGFISHER_ARCHIVE_CLANG_CL }
. (Join-Path $PSScriptRoot 'msvc-env.ps1') -Target $Target -VisualStudio $VisualStudio -Toolset $Toolset -ClangCl $ClangCl
$root = Split-Path $PSScriptRoot -Parent
if (-not $ArchiveDirectory) { $ArchiveDirectory = Join-Path $root 'native-archives' }
$ArchiveDirectory = [IO.Path]::GetFullPath($ArchiveDirectory)
Push-Location $root
$manifest = Join-Path $root 'kingfisher-vectorscan-sys\prebuilt-manifest.txt'
$originalManifest = [IO.File]::ReadAllBytes($manifest)
try {
    & python -m unittest discover -s scripts -p 'test_*.py'
    if ($LASTEXITCODE -ne 0) { throw 'Native release helper tests failed' }
    & python scripts/native.py build --target $Target --prefix (Join-Path $root "native-install\$Target") --archives $ArchiveDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Native Microsoft ABI build failed' }
    & python scripts/native.py manifest --archives $ArchiveDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Local archive manifest generation failed' }
    $env:VECTORSCAN_PREBUILT_DIR = $ArchiveDirectory
    $env:VECTORSCAN_OFFLINE = '1'
    $env:CXX = 'vectorscan-cxx-must-not-run'
    $env:CMAKE = 'vectorscan-cmake-must-not-run'
    & cargo test --workspace --all-targets
    if ($LASTEXITCODE -ne 0) { throw 'MSVC prebuilt Rust tests failed' }
    & cargo run -p kingfisher-vectorscan --example scan
    if ($LASTEXITCODE -ne 0) { throw 'MSVC prebuilt consumer example failed' }
    & cargo package -p kingfisher-vectorscan-sys --allow-dirty
    if ($LASTEXITCODE -ne 0) { throw 'MSVC sys crate package verification failed' }
    $env:CXX = $env:CC
    Remove-Item Env:CMAKE
    & cargo test --workspace --all-targets --features build-from-source
    if ($LASTEXITCODE -ne 0) { throw 'MSVC Cargo source build tests failed' }
    if ($NativeSuite) {
        & cargo test --workspace --all-targets --release --features kingfisher-vectorscan-sys/unit_hyperscan
        if ($LASTEXITCODE -ne 0) { throw 'MSVC native unit suite failed' }
    }
} finally {
    [IO.File]::WriteAllBytes($manifest, $originalManifest)
    Pop-Location
}
