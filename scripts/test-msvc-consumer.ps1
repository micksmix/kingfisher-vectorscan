param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('x86_64-pc-windows-msvc', 'aarch64-pc-windows-msvc')]
    [string] $Target,
    [ValidateSet('2022', '2026')]
    [string] $VisualStudio = '2026',
    [string] $Toolset,
    [string] $ArchiveDirectory
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (-not $ArchiveDirectory) { $ArchiveDirectory = Join-Path $root 'native-archives' }
$ArchiveDirectory = [IO.Path]::GetFullPath($ArchiveDirectory)
$selection = @{ Target = $Target; VisualStudio = $VisualStudio }
if ($Toolset) { $selection.Toolset = $Toolset }
. (Join-Path $PSScriptRoot 'msvc-env.ps1') @selection
$originalTarget = $env:CARGO_TARGET_DIR
$originalCxx = $env:CXX
$originalCmake = $env:CMAKE
$originalPrebuilt = $env:VECTORSCAN_PREBUILT_DIR
$originalOffline = $env:VECTORSCAN_OFFLINE
Push-Location $root
try {
    # A fresh consumer directory forces relinking with this actual SDK/toolset,
    # instead of merely re-running a previously linked baseline executable.
    $selectedToolset = $env:VCToolsVersion.TrimEnd('\')
    $env:CARGO_TARGET_DIR = Join-Path $root "target\msvc-consumer-vs$VisualStudio-$selectedToolset"
    $env:VECTORSCAN_PREBUILT_DIR = $ArchiveDirectory
    $env:VECTORSCAN_OFFLINE = '1'
    $env:CXX = 'vectorscan-cxx-must-not-run'
    $env:CMAKE = 'vectorscan-cmake-must-not-run'
    # This library does not commit Cargo.lock; bootstrap fresh checkouts once,
    # then keep all consumer commands locked to that dependency resolution.
    if (-not (Test-Path -LiteralPath (Join-Path $root 'Cargo.lock'))) {
        & cargo generate-lockfile
        if ($LASTEXITCODE -ne 0) { throw 'MSVC baseline archive consumer lockfile generation failed' }
    }
    & cargo test --locked --workspace --all-targets
    if ($LASTEXITCODE -ne 0) { throw 'MSVC baseline archive consumer tests failed' }
    & cargo run --locked -p kingfisher-vectorscan --example scan
    if ($LASTEXITCODE -ne 0) { throw 'MSVC baseline archive consumer example failed' }
    & cargo build --locked --release -p kingfisher-vectorscan --example throughput
    if ($LASTEXITCODE -ne 0) { throw 'MSVC baseline archive optimized consumer failed' }
} finally {
    $env:CARGO_TARGET_DIR = $originalTarget
    $env:CXX = $originalCxx
    $env:CMAKE = $originalCmake
    $env:VECTORSCAN_PREBUILT_DIR = $originalPrebuilt
    $env:VECTORSCAN_OFFLINE = $originalOffline
    Pop-Location
}
