"""Exercise consumer lockfile handling with real Cargo resolution, not native builds."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

POWERSHELL = shutil.which('pwsh') or shutil.which('powershell.exe')
CARGO = shutil.which('cargo')
CONSUMER_COMMANDS = [
    'test --locked --workspace --all-targets',
    'run --locked -p kingfisher-vectorscan --example scan',
    'build --locked --release -p kingfisher-vectorscan --example throughput',
]

CONSUMER_HARNESS = r"""
param([string] $Root, [string] $CargoPath, [string] $Target, [switch] $FailGeneration)
$ErrorActionPreference = 'Stop'
$global:consumerCommands = @()
$global:consumerDiagnostics = @()
$names = @('CARGO_TARGET_DIR', 'CXX', 'CMAKE', 'VECTORSCAN_PREBUILT_DIR', 'VECTORSCAN_OFFLINE')
$before = @{}
foreach ($name in $names) { $before[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$location = (Get-Location).Path
function cargo {
    $global:consumerCommands += $args -join ' '
    if ($FailGeneration -and $args[0] -eq 'generate-lockfile') {
        $global:consumerDiagnostics += 'Mock lockfile generation failed (exit 42)'
        $global:LASTEXITCODE = 42
        return
    }
    $resolutionArguments = @($args)
    if ($args[0] -ne 'generate-lockfile') {
        if ($args[0] -notin @('test', 'run', 'build')) { throw "Unexpected Cargo command: $args" }
        # Check the real --locked resolution without needing rustc or an MSVC
        # linker in GNU/MSYS2 jobs. Dedicated consumer jobs build the archives.
        $resolutionArguments = @('generate-lockfile')
        if ($args -contains '--locked') { $resolutionArguments += '--locked' }
    }
    # Capture native stderr without PowerShell turning it into an exception.
    $ErrorActionPreference = 'Continue'
    $output = & $CargoPath @resolutionArguments 2>&1
    $exitCode = $LASTEXITCODE
    $global:consumerDiagnostics += @($output | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.Exception.Message }
        else { [string] $_ }
    })
    $global:LASTEXITCODE = $exitCode
}
$failure = $null
try { $null = & (Join-Path $Root 'scripts/test-msvc-consumer.ps1') -Target $Target }
catch { $failure = $_.Exception.Message }
$restored = $true
foreach ($name in $names) {
    if ([Environment]::GetEnvironmentVariable($name, 'Process') -ne $before[$name]) { $restored = $false }
}
[pscustomobject]@{
    error = $failure
    commands = @($global:consumerCommands)
    diagnostics = @($global:consumerDiagnostics)
    environment_restored = $restored
    location_restored = (Get-Location).Path -eq $location
} | ConvertTo-Json -Compress
"""


@unittest.skipUnless(POWERSHELL and CARGO, 'PowerShell and Cargo are required for MSVC consumer tests')
class MsvcConsumerTests(unittest.TestCase):
    def run_command(self, command, *, cwd, env, timeout):
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        self.assertEqual(result.returncode, 0,
                         f"{command!r}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result

    def consume(self, target='x86_64-pc-windows-msvc', lockfile='missing', fail_generation=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Lockfile tests must not depend on a working compiler, linker or SDK.
            environment = dict(os.environ, CARGO_TERM_COLOR='never', CARGO_NET_OFFLINE='true',
                               RUSTC=str(root / 'rustc-must-not-run'), RUSTDOC=str(root / 'rustdoc-must-not-run'),
                               CC=str(root / 'cc-must-not-run'), CXX=str(root / 'cxx-must-not-run'),
                               CMAKE=str(root / 'cmake-must-not-run'))
            scripts = root / 'scripts'
            scripts.mkdir()
            shutil.copyfile(Path(__file__).with_name('test-msvc-consumer.ps1'), scripts / 'test-msvc-consumer.ps1')
            # Stub SDK setup; real Cargo validates lockfiles without building.
            (scripts / 'msvc-env.ps1').write_text(
                "param($Target, $VisualStudio, $Toolset)\n"
                "$env:VCToolsVersion = '14.51.36231'\n"
                "$env:CARGO_BUILD_TARGET = $null\n"
            )
            manifest = root / 'Cargo.toml'
            manifest.write_text('[package]\nname = "kingfisher-vectorscan"\nversion = "0.0.0"\nedition = "2021"\n[workspace]\n')
            (root / 'src').mkdir()
            (root / 'src/lib.rs').write_text('#[test]\nfn smoke() { assert_eq!(2 + 2, 4); }\n')
            (root / 'examples').mkdir()
            for example in ('scan', 'throughput'):
                (root / f'examples/{example}.rs').write_text('fn main() {}\n')
            lock = root / 'Cargo.lock'
            if lockfile != 'missing':
                self.run_command([CARGO, 'generate-lockfile'], cwd=root, env=environment, timeout=30)
            before = lock.read_bytes() if lock.exists() else None
            if lockfile == 'stale':
                manifest.write_text(manifest.read_text().replace('0.0.0', '0.0.1'))
            harness = scripts / 'consumer-test.ps1'
            harness.write_text(CONSUMER_HARNESS)
            command = [
                POWERSHELL, '-NoProfile', '-NonInteractive', '-File', str(harness),
                '-Root', str(root), '-CargoPath', CARGO, '-Target', target,
            ]
            if fail_generation:
                command.append('-FailGeneration')
            result = self.run_command(command, cwd=scripts, env=environment, timeout=90)
            state = json.loads(result.stdout)
            state['diagnostics'] = '\n'.join(state['diagnostics'])
            self.assertTrue(state['environment_restored'], state['diagnostics'])
            self.assertTrue(state['location_restored'], state['diagnostics'])
            after = lock.read_bytes() if lock.exists() else None
            return state, before, after

    def test_fresh_checkout_generates_lockfile_before_locked_commands(self):
        for target in ('x86_64-pc-windows-msvc', 'aarch64-pc-windows-msvc'):
            with self.subTest(target=target):
                result, before, after = self.consume(target=target)
                self.assertIsNone(result['error'], result['diagnostics'])
                self.assertEqual(result['commands'], ['generate-lockfile', *CONSUMER_COMMANDS])
                self.assertIsNone(before)
                self.assertIsNotNone(after)

    def test_existing_lockfile_is_preserved(self):
        result, before, after = self.consume(lockfile='existing')
        self.assertIsNone(result['error'], result['diagnostics'])
        self.assertEqual(result['commands'], CONSUMER_COMMANDS)
        self.assertEqual(after, before)

    def test_lockfile_generation_failure_stops_consumer_commands(self):
        result, before, after = self.consume(fail_generation=True)
        self.assertEqual(result['error'], 'MSVC baseline archive consumer lockfile generation failed', result['diagnostics'])
        self.assertEqual(result['commands'], ['generate-lockfile'])
        self.assertIn('Mock lockfile generation failed', result['diagnostics'])
        self.assertIsNone(before)
        self.assertIsNone(after)

    def test_stale_lockfile_is_rejected_without_regenerating_it(self):
        result, before, after = self.consume(lockfile='stale')
        self.assertEqual(result['error'], 'MSVC baseline archive consumer tests failed', result['diagnostics'])
        self.assertIn('lock file', result['diagnostics'])
        self.assertEqual(result['commands'], CONSUMER_COMMANDS[:1])
        self.assertEqual(after, before)


if __name__ == '__main__':
    unittest.main()
