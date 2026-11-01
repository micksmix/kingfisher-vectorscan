"""Exercise archive provenance and publication completeness without network access."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import native

POWERSHELL = shutil.which('pwsh') or shutil.which('powershell.exe')


class NativeReleaseTests(unittest.TestCase):
    @unittest.skipUnless(POWERSHELL, 'PowerShell is required for MSVC compiler discovery tests')
    def test_msvc_llvm_selection_uses_host_architecture(self):
        script = Path(__file__).with_name('find-msvc-llvm.ps1')
        cases = [
            ('X64', ('arm64', 'x64', 'generic', 'standalone'), 'x64'),
            ('Arm64', ('arm64', 'x64', 'generic', 'standalone'), 'arm64'),
            ('Arm64', ('x64', 'generic', 'standalone'), 'x64'),
            ('X64', ('arm64', 'generic', 'standalone'), 'generic'),
            ('X64', ('arm64', 'standalone'), 'standalone'),
            ('Arm64', ('standalone',), 'standalone'),
            ('X64', ('arm64',), None),
        ]
        for host, available, expected in cases:
            with self.subTest(host=host, available=available), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                installation = root / 'Visual Studio'
                program_files = root / 'Program Files'
                directories = {
                    'arm64': installation / 'VC/Tools/Llvm/ARM64/bin',
                    'x64': installation / 'VC/Tools/Llvm/x64/bin',
                    'generic': installation / 'VC/Tools/Llvm/bin',
                    'standalone': program_files / 'LLVM/bin',
                }
                for toolset in available:
                    directories[toolset].mkdir(parents=True, exist_ok=True)
                    (directories[toolset] / 'clang-cl.exe').write_bytes(b'compiler')
                result = subprocess.run([
                    POWERSHELL, '-NoProfile', '-NonInteractive', '-File', str(script),
                    '-Installation', str(installation), '-ProgramFiles', str(program_files),
                    '-HostArchitecture', host,
                ], check=True, capture_output=True, text=True)
                selected = result.stdout.strip()
                expected_path = directories[expected].as_posix() if expected else ''
                # PowerShell and MSYS2 use different separators; exercise both styles on every host.
                for output in (selected.replace('\\', '/'), selected.replace('/', '\\')):
                    with self.subTest(output=output):
                        self.assertEqual(output.replace('\\', '/'), expected_path)

    def test_release_requires_both_msvc_archives(self):
        msvc = {'x86_64-pc-windows-msvc', 'aarch64-pc-windows-msvc'}
        self.assertTrue(msvc <= set(native.TARGETS))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for target in native.TARGETS:
                (root / native.asset_name(target)).write_bytes(target.encode())
            for target in msvc:
                asset = root / native.asset_name(target)
                content = asset.read_bytes()
                asset.unlink()
                with self.assertRaises(ValueError):
                    native.manifest(root, require_all=True)
                asset.write_bytes(content)

    def test_msvc_build_uses_microsoft_abi_and_runtime(self):
        for target in ('x86_64-pc-windows-msvc', 'aarch64-pc-windows-msvc'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory, \
                    patch.dict(native.os.environ, {'VisualStudioVersion': '17.0', 'VCToolsVersion': '14.44.35207'}, clear=True), \
                    patch.object(native.subprocess, 'run') as run, \
                    patch.object(native.subprocess, 'check_output', return_value='clang version 22.1.3'), \
                    patch.object(native, 'verify_msvc_release_cache') as cache:
                prefix = Path(directory)
                (prefix / 'lib').mkdir()
                (prefix / 'lib/hs.lib').write_bytes(b'Microsoft ABI')
                native.build(target, prefix)
                configure = run.call_args_list[0].args[0]
                self.assertIn('Ninja', configure)
                self.assertIn('-DCMAKE_C_COMPILER=clang-cl', configure)
                self.assertIn(f'-DCMAKE_CXX_COMPILER_TARGET={target}', configure)
                self.assertIn('-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL', configure)
                self.assertNotIn('MinGW Makefiles', configure)
                self.assertNotIn('_USE_STD_VECTOR_ALGORITHMS', ' '.join(configure))
                self.assertEqual(native.msvc_archive_toolchain(prefix, target)['msvc_toolset'], '14.44.35207')
                cache.assert_called_once()

    def test_msvc_archive_rejects_the_regression_prone_clang_version(self):
        with patch.dict(native.os.environ, {'VisualStudioVersion': '17.0', 'VCToolsVersion': '14.44.35207'}, clear=True), \
                patch.object(native.subprocess, 'check_output', return_value='clang version 19.1.5'), \
                patch.object(native.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'optimized ARM64'):
                native.build('aarch64-pc-windows-msvc', Path('unused'))
            run.assert_not_called()

    def test_msvc_archive_rejects_cmake_cache_reset_to_debug(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / 'CMakeCache.txt'
            cache.write_text('CMAKE_BUILD_TYPE:STRING=Debug\nCMAKE_MSVC_RUNTIME_LIBRARY:STRING=MultiThreadedDLL\n')
            with self.assertRaisesRegex(ValueError, 'optimized Release'):
                native.verify_msvc_release_cache(root)
            cache.write_text('CMAKE_BUILD_TYPE:STRING=Release\nCMAKE_MSVC_RUNTIME_LIBRARY:STRING=MultiThreadedDLL\n')
            native.verify_msvc_release_cache(root)

    def test_msvc_archive_rejects_runner_toolset_drift_before_building(self):
        for environment in ({}, {'VisualStudioVersion': '18.0', 'VCToolsVersion': '14.51.36231'},
                            {'VisualStudioVersion': '17.0', 'VCToolsVersion': '14.43.34808'}):
            with self.subTest(environment=environment), patch.dict(native.os.environ, environment, clear=True), \
                    patch.object(native.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'VS|Visual Studio 2022'):
                    native.build('aarch64-pc-windows-msvc', Path('unused'))
                run.assert_not_called()

    def test_msvc_ci_pins_the_producer_and_tests_newer_consumers(self):
        workflow = (native.ROOT / '.github/workflows/native.yml').read_text()
        producer = workflow.split('  msvc-archives:', 1)[1].split('  msvc-consumers:', 1)[0]
        consumers = workflow.split('  msvc-consumers:', 1)[1].split('  musl-archives:', 1)[0]
        self.assertIn('install-msvc-baseline.ps1', producer)
        self.assertIn('install-msvc-llvm.ps1', producer)
        self.assertIn('-VisualStudio 2022 -Toolset 14.44', producer)
        self.assertIn('needs: msvc-archives', consumers)
        self.assertIn('windows-2025-vs2026', consumers)
        self.assertIn('test-msvc-consumer.ps1', consumers)
        self.assertNotIn('_USE_STD_VECTOR_ALGORITHMS', workflow)
        selector = (native.ROOT / 'scripts/msvc-env.ps1').read_text()
        self.assertIn('Microsoft.VCToolsVersion.default.txt', selector)
        self.assertIn("'VCToolsVersion', 'VCToolsInstallDir'", selector)
        self.assertIn("'INCLUDE', 'LIB', 'LIBPATH'", selector)

    def test_msvc_archive_requires_coff_library(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix = root / 'prefix'
            (prefix / 'lib').mkdir(parents=True)
            (prefix / 'include/hs').mkdir(parents=True)
            (prefix / 'include/hs/hs.h').write_text('header')
            (prefix / 'lib/libhs.a').write_bytes(b'wrong ABI')
            target = 'aarch64-pc-windows-msvc'
            output = root / 'archives'
            with self.assertRaises(ValueError):
                native.pack(target, prefix, output)
            (prefix / 'lib/hs.lib').write_bytes(b'Microsoft ABI')
            toolchain = {'format': 1, 'target': target, 'visual_studio_version': '17.0',
                         'msvc_toolset': '14.44.35207', 'runtime': 'MD', 'clang_version': native.MSVC_CLANG_VERSION,
                         'library_sha256': hashlib.sha256(b'Microsoft ABI').hexdigest()}
            (prefix / native.MSVC_TOOLCHAIN_FILE).write_text(json.dumps(toolchain))
            native.pack(target, prefix, output)
            with tarfile.open(output / native.asset_name(target)) as archive:
                self.assertIn('lib/hs.lib', archive.getnames())
                self.assertNotIn('lib/libhs.a', archive.getnames())
                self.assertIn(native.MSVC_TOOLCHAIN_FILE, archive.getnames())
            (prefix / 'lib/hs.lib').write_bytes(b'replaced library')
            with self.assertRaisesRegex(ValueError, 'metadata'):
                native.pack(target, prefix, output)

    def test_release_requires_both_musl_archives(self):
        musl = {'x86_64-unknown-linux-musl', 'aarch64-unknown-linux-musl'}
        self.assertTrue(musl <= set(native.TARGETS))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for target in native.TARGETS:
                (root / native.asset_name(target)).write_bytes(target.encode())
            manifest = native.manifest(root, require_all=True)
            for target in musl:
                self.assertIn(f' {target} ', manifest)
                asset = root / native.asset_name(target)
                content = asset.read_bytes()
                asset.unlink()
                with self.assertRaises(ValueError):
                    native.manifest(root, require_all=True)
                asset.write_bytes(content)

    def test_musl_build_rejects_wrong_toolchain(self):
        for machine in ['x86_64-linux-gnu', 'aarch64-alpine-linux-musl']:
            with self.subTest(machine=machine), patch.dict(native.os.environ, {}, clear=True), \
                    patch.object(native.subprocess, 'check_output', return_value=machine), \
                    patch.object(native.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    native.build('x86_64-unknown-linux-musl', Path('unused'))
                run.assert_not_called()

    def test_archive_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix = root / 'prefix'
            (prefix / 'lib').mkdir(parents=True)
            (prefix / 'include/hs').mkdir(parents=True)
            (prefix / 'lib/libhs.a').write_bytes(b'library')
            (prefix / 'include/hs/hs.h').write_text('header')
            target = native.TARGETS[0]
            output = root / 'archives'
            native.pack(target, prefix, output)
            asset = output / native.asset_name(target)
            first = asset.read_bytes()
            native.pack(target, prefix, output)
            self.assertEqual(first, asset.read_bytes())
            with tarfile.open(asset) as archive:
                self.assertIn('licenses/NOTICE', archive.getnames())
                self.assertIn('lib/libhs.a', archive.getnames())
            self.assertIn(hashlib.sha256(first).hexdigest(), native.manifest(output))
            with self.assertRaises(ValueError):
                native.manifest(output, require_all=True)
            (output / 'vectorscan-wrong-version.tar.gz').write_bytes(b'wrong')
            with self.assertRaises(ValueError):
                native.manifest(output)


if __name__ == '__main__':
    unittest.main()
