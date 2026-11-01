param(
    [Parameter(Mandatory = $true)]
    [string] $Installation,
    [Parameter(Mandatory = $true)]
    [string] $ProgramFiles,
    [System.Runtime.InteropServices.Architecture] $HostArchitecture =
        [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
)

# Select the compiler executable for the host, not the Rust target: clang-cl can cross-compile.
@(
    if ($HostArchitecture -eq [System.Runtime.InteropServices.Architecture]::Arm64) {
        (Join-Path $Installation 'VC\Tools\Llvm\ARM64\bin')
    }
    (Join-Path $Installation 'VC\Tools\Llvm\x64\bin'),
    (Join-Path $Installation 'VC\Tools\Llvm\bin'),
    (Join-Path $ProgramFiles 'LLVM\bin')
) | Where-Object { Test-Path (Join-Path $_ 'clang-cl.exe') } | Select-Object -First 1
