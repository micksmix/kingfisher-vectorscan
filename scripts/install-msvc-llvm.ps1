param([string] $InstallPath)

$ErrorActionPreference = 'Stop'
$version = '22.1.3'
if (-not $InstallPath) {
    $temporary = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [IO.Path]::GetTempPath() }
    $InstallPath = Join-Path $temporary "kingfisher-llvm-$version"
}
$compiler = Join-Path $InstallPath 'bin\clang-cl.exe'
if (Test-Path $compiler) {
    $description = & $compiler --version
    if ($LASTEXITCODE -ne 0 -or ($description -join "`n") -notmatch 'clang version 22\.1\.3(?:\s|$)') {
        throw 'Existing archive compiler directory has an unexpected LLVM version'
    }
} else {
    $arm64 = [Runtime.InteropServices.RuntimeInformation]::OSArchitecture -eq [Runtime.InteropServices.Architecture]::Arm64
    $asset = if ($arm64) { 'LLVM-22.1.3-woa64.exe' } else { 'LLVM-22.1.3-win64.exe' }
    $digest = if ($arm64) { 'c18d02a43ba31595ca99590faf3ac74c89577f3f49e903537c5bdec5100ed4d2' } else { '72ca54c3b7940615776d8994c0b918a1d8c4981bdcf13b439eaa86a1bd477001' }
    $directory = Join-Path ([IO.Path]::GetTempPath()) ('kingfisher-llvm-download-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $directory | Out-Null
    try {
        $installer = Join-Path $directory $asset
        Invoke-WebRequest "https://github.com/llvm/llvm-project/releases/download/llvmorg-$version/$asset" -OutFile $installer -UseBasicParsing
        if ((Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant() -ne $digest) { throw 'Pinned LLVM installer SHA-256 mismatch' }
        # NSIS /D is last and intentionally unquoted; the rest of the argument is the path.
        $process = Start-Process -FilePath $installer -ArgumentList @('/S', "/D=$InstallPath") -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw "LLVM installer exited $($process.ExitCode)" }
    } finally { Remove-Item -LiteralPath $directory -Recurse -Force }
    if (-not (Test-Path $compiler)) { throw 'Pinned LLVM setup did not provide clang-cl' }
    $description = & $compiler --version
    if ($LASTEXITCODE -ne 0 -or ($description -join "`n") -notmatch 'clang version 22\.1\.3(?:\s|$)') { throw 'Installed LLVM version mismatch' }
}
$env:KINGFISHER_ARCHIVE_CLANG_CL = [IO.Path]::GetFullPath($compiler)
if ($env:GITHUB_ENV) { "KINGFISHER_ARCHIVE_CLANG_CL=$env:KINGFISHER_ARCHIVE_CLANG_CL" >> $env:GITHUB_ENV }
Write-Output "Pinned archive compiler: $env:KINGFISHER_ARCHIVE_CLANG_CL"
