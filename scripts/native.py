"""Build portable native release archives and embed their checksums in the crate."""
import argparse
import gzip
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile
try:
    import tomllib
except ModuleNotFoundError:  # Ubuntu 22.04 ships Python 3.10.
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
SYS = ROOT / 'kingfisher-vectorscan-sys'
TARGETS = (
    'x86_64-unknown-linux-gnu', 'aarch64-unknown-linux-gnu',
    'x86_64-apple-darwin', 'aarch64-apple-darwin',
    'x86_64-pc-windows-gnu', 'aarch64-pc-windows-gnullvm',
)


def version():
    with (SYS / 'Cargo.toml').open('rb') as source:
        return tomllib.load(source)['package']['version']


def asset_name(target):
    return f'vectorscan-{version()}-{target}.tar.gz'


def build(target, prefix):
    build_dir = ROOT / 'native-build' / target
    args = ['cmake', '-S', str(SYS / 'vectorscan'), '-B', str(build_dir),
            '-DCMAKE_BUILD_TYPE=Release', f'-DCMAKE_INSTALL_PREFIX={prefix}',
            '-DCMAKE_INSTALL_LIBDIR=lib', '-DCMAKE_INSTALL_INCLUDEDIR=include',
            '-DCMAKE_POSITION_INDEPENDENT_CODE=ON', '-DBUILD_STATIC_LIBS=ON']
    for option in ['BUILD_SHARED_LIBS', 'BUILD_UNIT', 'BUILD_TOOLS', 'BUILD_EXAMPLES',
                   'BUILD_BENCHMARKS', 'BUILD_DOC', 'FAT_RUNTIME', 'USE_CPU_NATIVE',
                   'BUILD_AVX2', 'BUILD_AVX512', 'BUILD_AVX512VBMI', 'BUILD_SVE',
                   'BUILD_SVE2', 'BUILD_SVE2_BITPERM', 'WARNINGS_AS_ERRORS']:
        args.append(f'-D{option}=OFF')
    if 'windows' in target:
        processor = 'ARM64' if target.startswith('aarch64') else 'AMD64'
        args += ['-G', 'MinGW Makefiles', '-DCMAKE_SYSTEM_NAME=Windows',
                 f'-DCMAKE_SYSTEM_PROCESSOR={processor}']
    for key in ('CC', 'CXX'):
        if os.environ.get(key):
            language = 'C' if key == 'CC' else 'CXX'
            args.append(f'-DCMAKE_{language}_COMPILER={os.environ[key]}')
    if 'apple' in target:
        args.append('-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0')
    subprocess.run(args, check=True)
    subprocess.run(['cmake', '--build', str(build_dir), '--parallel', '4'], check=True)
    subprocess.run(['cmake', '--install', str(build_dir)], check=True)


def pack(target, prefix, output):
    required = [prefix / 'lib/libhs.a', prefix / 'include/hs/hs.h']
    for path in required:
        if not path.is_file():
            raise ValueError(f'Missing installed file: {path}')
    output.mkdir(parents=True, exist_ok=True)
    destination = output / asset_name(target)
    files = [(prefix / 'lib/libhs.a', 'lib/libhs.a')]
    files += [(p, p.relative_to(prefix).as_posix()) for p in sorted((prefix / 'include/hs').glob('*.h'))]
    files += [(SYS / name, f'licenses/{name}') for name in ('NOTICE', 'LICENSE-VECTORSCAN', 'LICENSE-MIT', 'LICENSE-APACHE')]
    # Fixed metadata makes packaging deterministic for the same compiled inputs.
    with destination.open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for path, name in files:
                    info = archive.gettarinfo(str(path), arcname=name)
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ''
                    info.mode = 0o644
                    with path.open('rb') as data:
                        archive.addfile(info, data)
    print(destination)


def manifest(directory, require_all=False):
    paths = sorted(directory.glob('vectorscan-*.tar.gz'))
    expected = {asset_name(target): target for target in TARGETS}
    if not paths or any(p.name not in expected for p in paths):
        raise ValueError('Missing archives or unexpected version/target in archive directory')
    if require_all and {p.name for p in paths} != set(expected):
        raise ValueError('Release must contain every supported target')
    return '# version target sha256\n' + ''.join(
        f'{version()} {expected[p.name]} {hashlib.sha256(p.read_bytes()).hexdigest()}\n'
        for p in paths
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'pack', 'manifest', 'release'])
    parser.add_argument('--target', choices=TARGETS)
    parser.add_argument('--prefix', type=Path, default=ROOT / 'native-install')
    parser.add_argument('--archives', type=Path, default=ROOT / 'native-archives')
    parser.add_argument('--require-all', action='store_true')
    args = parser.parse_args()
    if args.command in ('build', 'pack'):
        if not args.target:
            parser.error('--target is required')
        if args.command == 'build':
            build(args.target, args.prefix.resolve())
        pack(args.target, args.prefix.resolve(), args.archives)
    elif args.command == 'manifest':
        (SYS / 'prebuilt-manifest.txt').write_text(manifest(args.archives, args.require_all))
    else:
        # On retries, use the already-published assets, never replace binaries under
        # an existing tag. The embedded manifest must match that release exactly.
        tag = f'v{version()}'
        releases = subprocess.check_output(['gh', 'api', '--paginate', 'repos/micksmix/kingfisher-vectorscan/releases', '--jq', '.[].tag_name'], text=True).splitlines()
        if tag in releases:
            canonical = ROOT / 'native-canonical'
            canonical.mkdir(exist_ok=True)
            subprocess.run(['gh', 'release', 'download', tag, '--repo', 'micksmix/kingfisher-vectorscan', '--dir', str(canonical), '--clobber'], check=True)
            text = manifest(canonical, require_all=True)
            if text != (canonical / 'prebuilt-manifest.txt').read_text():
                raise ValueError('Published release assets do not match their manifest')
            (SYS / 'prebuilt-manifest.txt').write_text(text)
        else:
            text = manifest(args.archives, require_all=True)
            (SYS / 'prebuilt-manifest.txt').write_text(text)
            checksums = args.archives / 'prebuilt-manifest.txt'
            checksums.write_text(text)
            subprocess.run(['gh', 'release', 'create', tag, '--repo', 'micksmix/kingfisher-vectorscan', '--verify-tag', '--title', tag,
                            '--notes', 'Portable native Vectorscan archives. SHA-256 checksums are embedded in the published sys crate. See README.md for target and runtime requirements.',
                            *map(str, sorted(args.archives.glob('*.tar.gz'))), str(checksums)], check=True)


if __name__ == '__main__':
    main()
