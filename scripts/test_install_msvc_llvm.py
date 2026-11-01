"""Exercise LLVM installer cleanup without downloading or running an installer."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

POWERSHELL = shutil.which('pwsh') or shutil.which('powershell.exe')

# Mock only the external installer operations. The real script still performs
# its checksum, exit-code, compiler-presence, version and environment checks.
INSTALLER_HARNESS = r"""
param([string] $Installer, [string] $Root, [int] $CleanupFailures, [string] $Scenario)
$ErrorActionPreference = 'Stop'
$global:llvmTest = @{ CleanupAttempts = 0; Sleeps = 0; Warnings = @(); CompilerCalls = 0 }
$env:KINGFISHER_ARCHIVE_CLANG_CL = $null
$env:GITHUB_ENV = Join-Path $Root 'github-env'
[IO.File]::WriteAllText($env:GITHUB_ENV, '')
$installation = Join-Path $Root 'LLVM install'
$global:llvmTest.MockCompiler = Join-Path $installation 'bin/clang-cl.ps1'

function Join-Path {
    param([string] $Path, [string] $ChildPath)
    # A portable PowerShell compiler stub avoids executing a Windows binary.
    if ($ChildPath -eq 'bin\clang-cl.exe') { $ChildPath = 'bin/clang-cl.ps1' }
    if ($ChildPath -like 'kingfisher-llvm-download-*') { $Path = $Root }
    Microsoft.PowerShell.Management\Join-Path $Path $ChildPath
}
function Invoke-WebRequest {
    param($Uri, $OutFile, [switch] $UseBasicParsing)
    if ($Scenario -eq 'download-error') { throw 'Mock LLVM download failed' }
    [IO.File]::WriteAllText($OutFile, 'mock installer')
}
function Get-FileHash {
    param($Path, $Algorithm)
    $hash = if ($Scenario -eq 'bad-checksum') { '0' * 64 }
        elseif ($Path -like '*woa64.exe') { 'c18d02a43ba31595ca99590faf3ac74c89577f3f49e903537c5bdec5100ed4d2' }
        else { '72ca54c3b7940615776d8994c0b918a1d8c4981bdcf13b439eaa86a1bd477001' }
    [pscustomobject]@{ Hash = $hash }
}
function Start-Process {
    param($FilePath, $ArgumentList, [switch] $Wait, [switch] $PassThru)
    if (-not $Wait -or -not $PassThru) { throw 'Installer must be waited for' }
    if ($Scenario -eq 'installer-error') { return [pscustomobject]@{ ExitCode = 42 } }
    if ($Scenario -ne 'missing-compiler') {
        $null = [IO.Directory]::CreateDirectory((Split-Path $global:llvmTest.MockCompiler))
        $version = if ($Scenario -eq 'wrong-version') { '19.1.5' } else { '22.1.3' }
        $content = '$global:llvmTest.CompilerCalls++; $global:LASTEXITCODE = 0; "clang version {0}"' -f $version
        [IO.File]::WriteAllText($global:llvmTest.MockCompiler, $content)
    }
    [pscustomobject]@{ ExitCode = 0 }
}
function Remove-Item {
    [CmdletBinding()]
    param([string] $LiteralPath, [switch] $Recurse, [switch] $Force)
    $global:llvmTest.CleanupAttempts++
    if ($global:llvmTest.CleanupAttempts -le $CleanupFailures) {
        throw [UnauthorizedAccessException]::new('Mock installer is still locked')
    }
    Microsoft.PowerShell.Management\Remove-Item -LiteralPath $LiteralPath -Recurse -Force -ErrorAction Stop
}
function Start-Sleep {
    param([int] $Seconds)
    $global:llvmTest.Sleeps++
}
function Write-Warning {
    param([string] $Message)
    $global:llvmTest.Warnings += $Message
}
$failure = $null
try { $null = & $Installer -InstallPath $installation }
catch { $failure = $_.Exception.Message }
[pscustomobject]@{
    error = $failure
    cleanup_attempts = $global:llvmTest.CleanupAttempts
    sleeps = $global:llvmTest.Sleeps
    warnings = @($global:llvmTest.Warnings)
    compiler_calls = $global:llvmTest.CompilerCalls
    compiler = $env:KINGFISHER_ARCHIVE_CLANG_CL
    github_env = [IO.File]::ReadAllText($env:GITHUB_ENV)
} | ConvertTo-Json -Compress
"""


@unittest.skipUnless(POWERSHELL, 'PowerShell is required for LLVM installer tests')
class MsvcLlvmInstallerTests(unittest.TestCase):
    def install(self, cleanup_failures, scenario='success'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            harness = root / 'installer-test.ps1'
            harness.write_text(INSTALLER_HARNESS)
            result = subprocess.run([
                POWERSHELL, '-NoProfile', '-NonInteractive', '-File', str(harness),
                '-Installer', str(Path(__file__).with_name('install-msvc-llvm.ps1').resolve()),
                '-Root', str(root), '-CleanupFailures', str(cleanup_failures), '-Scenario', scenario,
            ], check=True, capture_output=True, text=True, timeout=30)
            return json.loads(result.stdout)

    def test_cleanup_retries_transient_installer_locks(self):
        for failures in (0, 2):
            with self.subTest(failures=failures):
                result = self.install(failures)
                self.assertIsNone(result['error'])
                self.assertEqual(result['cleanup_attempts'], failures + 1)
                self.assertEqual(result['sleeps'], failures)
                self.assertEqual(result['warnings'], [])
                self.assertEqual(result['compiler_calls'], 1)
                self.assertIn(f"KINGFISHER_ARCHIVE_CLANG_CL={result['compiler']}", result['github_env'])

    def test_persistent_cleanup_lock_warns_without_failing_installation(self):
        result = self.install(100)
        self.assertIsNone(result['error'])
        self.assertEqual(result['cleanup_attempts'], 5)
        self.assertEqual(result['sleeps'], 4)
        self.assertEqual(len(result['warnings']), 1)
        self.assertIn('Mock installer is still locked', result['warnings'][0])
        self.assertEqual(result['compiler_calls'], 1)
        self.assertIn(f"KINGFISHER_ARCHIVE_CLANG_CL={result['compiler']}", result['github_env'])

    def test_cleanup_does_not_mask_installation_or_validation_errors(self):
        cases = {
            'download-error': 'Mock LLVM download failed',
            'bad-checksum': 'Pinned LLVM installer SHA-256 mismatch',
            'installer-error': 'LLVM installer exited 42',
            'missing-compiler': 'Pinned LLVM setup did not provide clang-cl',
            'wrong-version': 'Installed LLVM version mismatch',
        }
        for scenario, error in cases.items():
            with self.subTest(scenario=scenario):
                result = self.install(100, scenario)
                self.assertEqual(result['error'], error)
                self.assertEqual(result['cleanup_attempts'], 5)
                self.assertEqual(result['sleeps'], 4)
                self.assertEqual(len(result['warnings']), 1)
                self.assertFalse(result['compiler'])
                self.assertEqual(result['github_env'], '')


if __name__ == '__main__':
    unittest.main()
