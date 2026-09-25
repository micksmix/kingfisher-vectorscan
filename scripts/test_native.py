"""Exercise archive provenance and publication completeness without network access."""
import hashlib
from pathlib import Path
import tarfile
import tempfile
import unittest
import native


class NativeReleaseTests(unittest.TestCase):
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
