param(
    [string] $InstallPath = (Join-Path $env:ProgramFiles 'Kingfisher VS2022 Build Tools')
)

$ErrorActionPreference = 'Stop'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$components = @('Microsoft.VisualStudio.Component.VC.Tools.x86.x64', 'Microsoft.VisualStudio.Component.VC.Tools.ARM64')
if (Test-Path $vswhere) {
    $installation = & $vswhere -latest -products '*' -version '[17.0,18.0)' -requires $components -property installationPath
    if ($installation -and (Get-ChildItem (Join-Path $installation 'VC\Tools\MSVC') -Directory -Filter '14.44.*')) {
        Write-Output 'VS 2022 / MSVC 14.44 archive baseline is already installed'
        return
    }
}

$directory = Join-Path ([IO.Path]::GetTempPath()) ('kingfisher-vs2022-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $directory | Out-Null
try {
    $installer = Join-Path $directory 'vs_buildtools.exe'
    # The version-specific VS 2022 channel cannot roll forward to VS 2026.
    Invoke-WebRequest 'https://aka.ms/vs/17/release/vs_buildtools.exe' -OutFile $installer -UseBasicParsing
    $signature = Get-AuthenticodeSignature $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') {
        throw 'Microsoft signature verification failed for the VS 2022 installer'
    }
    $arguments = @('--quiet', '--wait', '--norestart', '--nocache', '--installPath', "`"$InstallPath`"",
        '--add', 'Microsoft.VisualStudio.Workload.VCTools')
    foreach ($component in $components) { $arguments += @('--add', $component) }
    $arguments += @('--add', 'Microsoft.VisualStudio.Component.VC.Llvm.Clang',
        '--add', 'Microsoft.VisualStudio.Component.Windows11SDK.26100')
    $process = Start-Process -FilePath $installer -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) { throw "VS 2022 setup failed with exit code $($process.ExitCode)" }
    if ($process.ExitCode -eq 3010) { Write-Output 'VS 2022 setup requests a restart; no automatic restart was performed' }
    $installation = & $vswhere -latest -products '*' -version '[17.0,18.0)' -requires $components -property installationPath
    if (-not $installation -or -not (Get-ChildItem (Join-Path $installation 'VC\Tools\MSVC') -Directory -Filter '14.44.*')) {
        throw 'VS 2022 setup did not provide the required MSVC 14.44 toolset'
    }
} finally {
    Remove-Item -LiteralPath $directory -Recurse -Force
}
