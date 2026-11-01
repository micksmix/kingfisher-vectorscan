param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('x86_64-pc-windows-msvc', 'aarch64-pc-windows-msvc')]
    [string] $Target,
    [ValidateSet('2022', '2026')]
    [string] $VisualStudio,
    [ValidatePattern('^14\.[0-9]+(?:\.[0-9]+)?$')]
    [string] $Toolset,
    [string] $ClangCl
)

$ErrorActionPreference = 'Stop'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path $vswhere)) { throw 'Install Visual Studio C++ Build Tools and LLVM clang-cl first' }
$arguments = @('-latest', '-products', '*', '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath')
if ($VisualStudio) {
    $range = if ($VisualStudio -eq '2022') { '[17.0,18.0)' } else { '[18.0,19.0)' }
    $arguments += @('-version', $range)
}
$installation = & $vswhere @arguments
if (-not $installation) { throw 'Visual Studio C++ Build Tools were not found' }
# VsDevCmd can inherit VCToolsVersion/INCLUDE/LIB from a previous IDE session.
# Select even the default toolset explicitly and reset only SDK-owned state.
if (-not $Toolset) {
    $defaultToolset = Join-Path $installation 'VC\Auxiliary\Build\Microsoft.VCToolsVersion.default.txt'
    $Toolset = (Get-Content -LiteralPath $defaultToolset -Raw).Trim()
}
if ($env:__VSCMD_PREINIT_PATH) { $env:PATH = $env:__VSCMD_PREINIT_PATH }
foreach ($name in @('VSCMD_VER', 'VCToolsVersion', 'VCToolsInstallDir', 'VCToolsRedistDir',
        'VSINSTALLDIR', 'VCINSTALLDIR', 'VCIDEInstallDir', 'VisualStudioVersion',
        'INCLUDE', 'LIB', 'LIBPATH', 'WindowsSdkDir', 'WindowsSDKVersion',
        'WindowsSDKLibVersion', 'WindowsSDK_ExecutablePath_x64', 'WindowsSDK_ExecutablePath_x86')) {
    [Environment]::SetEnvironmentVariable($name, $null, 'Process')
}
$architecture = if ($Target.StartsWith('aarch64')) { 'arm64' } else { 'amd64' }
$devcmd = Join-Path $installation 'Common7\Tools\VsDevCmd.bat'
# Capture, rather than print, the environment: runner environments can contain secrets.
$versionArgument = " -vcvars_ver=$Toolset"
$environment = & cmd.exe /d /s /c "`"$devcmd`" -no_logo -arch=$architecture -host_arch=amd64$versionArgument >nul && set"
if ($LASTEXITCODE -ne 0) { throw 'Unable to initialize the Microsoft target SDK environment' }
foreach ($line in $environment) {
    $parts = $line -split '=', 2
    if ($parts.Count -eq 2 -and $parts[0]) {
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
}
if ($Toolset -and $env:VCToolsVersion.TrimEnd('\') -ne $Toolset -and -not $env:VCToolsVersion.TrimEnd('\').StartsWith("$Toolset.")) {
    throw "Requested MSVC $Toolset, but the developer environment selected $($env:VCToolsVersion)"
}
if ($VisualStudio -eq '2022' -and -not $env:VisualStudioVersion.StartsWith('17.')) {
    throw 'Archive baseline requires the Visual Studio 2022 developer environment'
}
if ($VisualStudio -eq '2026' -and -not $env:VisualStudioVersion.StartsWith('18.')) {
    throw 'Requested the Visual Studio 2026 developer environment'
}
$stl = Join-Path $env:VCToolsInstallDir 'include'
if (-not (Test-Path (Join-Path $stl 'vector'))) { throw 'Selected MSVC STL headers were not found' }
if (-not (($env:INCLUDE -split ';').TrimEnd('\') -contains $stl.TrimEnd('\'))) {
    throw 'INCLUDE does not use the selected MSVC STL headers'
}
Write-Output "Microsoft SDK/STL selected: VS $($env:VisualStudioVersion), MSVC $($env:VCToolsVersion), target $Target"
if ($ClangCl) {
    if (-not (Test-Path -LiteralPath $ClangCl -PathType Leaf)) { throw 'Requested clang-cl executable was not found' }
    $llvm = Split-Path ([IO.Path]::GetFullPath($ClangCl)) -Parent
} else {
    $llvm = & (Join-Path $PSScriptRoot 'find-msvc-llvm.ps1') -Installation $installation -ProgramFiles $env:ProgramFiles
}
if (-not $llvm) { throw 'Install the Visual Studio LLVM/Clang component or LLVM for Windows' }
$env:PATH = "$llvm;$env:PATH"
$env:CC = Join-Path $llvm 'clang-cl.exe'
$env:CXX = $env:CC
$env:CARGO_BUILD_TARGET = $Target
$env:CMAKE_GENERATOR = 'Ninja'
& clang-cl --version
if ($LASTEXITCODE -ne 0) { throw 'clang-cl is not executable' }
