"""Exercise archive provenance and publication completeness without network access."""
import hashlib
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import native


class NativeReleaseTests(unittest.TestCase):
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
            with self.subTest(target=target), patch.dict(native.os.environ, {}, clear=True), \
                    patch.object(native.subprocess, 'run') as run:
                native.build(target, Path('unused'))
                configure = run.call_args_list[0].args[0]
                self.assertIn('Ninja', configure)
                self.assertIn('-DCMAKE_C_COMPILER=clang-cl', configure)
                self.assertIn(f'-DCMAKE_CXX_COMPILER_TARGET={target}', configure)
                self.assertIn('-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL', configure)
                self.assertNotIn('MinGW Makefiles', configure)

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
            native.pack(target, prefix, output)
            with tarfile.open(output / native.asset_name(target)) as archive:
                self.assertIn('lib/hs.lib', archive.getnames())
                self.assertNotIn('lib/libhs.a', archive.getnames())

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
