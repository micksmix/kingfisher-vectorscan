param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('x86_64-pc-windows-msvc', 'aarch64-pc-windows-msvc')]
    [string] $Target
)

$ErrorActionPreference = 'Stop'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path $vswhere)) { throw 'Install Visual Studio C++ Build Tools and LLVM clang-cl first' }
$installation = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $installation) { throw 'Visual Studio C++ Build Tools were not found' }
$architecture = if ($Target.StartsWith('aarch64')) { 'arm64' } else { 'amd64' }
$devcmd = Join-Path $installation 'Common7\Tools\VsDevCmd.bat'
# Capture, rather than print, the environment: runner environments can contain secrets.
$environment = & cmd.exe /d /s /c "`"$devcmd`" -no_logo -arch=$architecture -host_arch=amd64 >nul && set"
if ($LASTEXITCODE -ne 0) { throw 'Unable to initialize the Microsoft target SDK environment' }
foreach ($line in $environment) {
    $parts = $line -split '=', 2
    if ($parts.Count -eq 2 -and $parts[0]) {
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
}
$llvm = @(
    (Join-Path $installation 'VC\Tools\Llvm\ARM64\bin'),
    (Join-Path $installation 'VC\Tools\Llvm\x64\bin'),
    (Join-Path $installation 'VC\Tools\Llvm\bin'),
    (Join-Path $env:ProgramFiles 'LLVM\bin')
) | Where-Object { Test-Path (Join-Path $_ 'clang-cl.exe') } | Select-Object -First 1
if (-not $llvm) { throw 'Install the Visual Studio LLVM/Clang component or LLVM for Windows' }
$env:PATH = "$llvm;$env:PATH"
$env:CC = 'clang-cl'
$env:CXX = 'clang-cl'
$env:CARGO_BUILD_TARGET = $Target
$env:CMAKE_GENERATOR = 'Ninja'
& clang-cl --version
if ($LASTEXITCODE -ne 0) { throw 'clang-cl is not executable' }
