"""Build portable native release archives and embed their checksums in the crate."""
import argparse
import gzip
import hashlib
import json
import os
import re
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
    'x86_64-unknown-linux-musl', 'aarch64-unknown-linux-musl',
    'x86_64-apple-darwin', 'aarch64-apple-darwin',
    'x86_64-pc-windows-gnu', 'aarch64-pc-windows-gnullvm',
    'x86_64-pc-windows-msvc', 'aarch64-pc-windows-msvc',
)
MSVC_TOOLCHAIN_FILE = 'lib/build-toolchain.json'
MSVC_CLANG_VERSION = '22.1.3'


def msvc_archive_environment():
    """Release archives use a stable STL/CRT baseline, not the newest runner IDE."""
    visual_studio = os.environ.get('VisualStudioVersion', '')
    toolset = os.environ.get('VCToolsVersion', '').rstrip('\\/')
    if not visual_studio.startswith('17.') or not toolset.startswith('14.44.'):
        raise ValueError('MSVC archives require Visual Studio 2022 / MSVC 14.44; '
                         'run scripts/msvc-env.ps1 -Target <target> -VisualStudio 2022 -Toolset 14.44')
    compiler = os.environ.get('CXX') or 'clang-cl'
    description = subprocess.check_output([compiler, '--version'], text=True)
    found = re.search(r'clang version ([0-9.]+)', description)
    if not found or found.group(1) != MSVC_CLANG_VERSION:
        raise ValueError(f'MSVC archives require clang-cl {MSVC_CLANG_VERSION} for optimized ARM64 code generation; '
                         'run scripts/install-msvc-llvm.ps1 and pass its compiler to msvc-env.ps1 -ClangCl')
    return {'format': 1, 'visual_studio_version': visual_studio,
            'msvc_toolset': toolset, 'runtime': 'MD', 'clang_version': MSVC_CLANG_VERSION}


def msvc_archive_toolchain(prefix, target):
    metadata = json.loads((prefix / MSVC_TOOLCHAIN_FILE).read_text())
    if (metadata.get('format') != 1 or metadata.get('target') != target
            or not metadata.get('visual_studio_version', '').startswith('17.')
            or not metadata.get('msvc_toolset', '').startswith('14.44.')
            or metadata.get('runtime') != 'MD'
            or metadata.get('clang_version') != MSVC_CLANG_VERSION
            or metadata.get('library_sha256') != hashlib.sha256((prefix / 'lib/hs.lib').read_bytes()).hexdigest()):
        raise ValueError('MSVC archive toolchain metadata does not match the VS 2022 / 14.44 library build')
    return metadata


def verify_msvc_release_cache(build_dir):
    values = {}
    for line in (build_dir / 'CMakeCache.txt').read_text().splitlines():
        if not line or line.startswith(('#', '//')) or '=' not in line or ':' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.split(':', 1)[0]] = value
    if (values.get('CMAKE_BUILD_TYPE', '').lower() != 'release'
            or values.get('CMAKE_MSVC_RUNTIME_LIBRARY') != 'MultiThreadedDLL'):
        raise ValueError('MSVC archive configuration lost its optimized Release /MD settings')


def version():
    with (SYS / 'Cargo.toml').open('rb') as source:
        return tomllib.load(source)['package']['version']


def asset_name(target):
    return f'vectorscan-{version()}-{target}.tar.gz'


def library_path(target):
    return 'lib/hs.lib' if target.endswith('-msvc') else 'lib/libhs.a'


def build(target, prefix):
    toolchain = msvc_archive_environment() if target.endswith('-msvc') else None
    if target.endswith('-musl'):
        # These release assets use the GCC C++ ABI. Do not accidentally publish
        # a host/glibc library under a musl filename when building manually.
        for key, default in [('CC', 'cc'), ('CXX', 'c++')]:
            compiler = os.environ.get(key) or default
            machine = subprocess.check_output([compiler, '-dumpmachine'], text=True).strip()
            if not machine.startswith(target.split('-')[0] + '-') or not machine.endswith('-musl'):
                raise ValueError(f'{key}={compiler} targets {machine}, expected {target}')
    build_dir = ROOT / 'native-build' / target
    if toolchain is not None:
        # CMake deletes cache settings when a compiler path changes. Isolate the
        # compiler identity so switching LLVM cannot silently reset Release to Debug.
        compiler = '\0'.join(os.environ.get(key, 'clang-cl') for key in ('CC', 'CXX'))
        identity = hashlib.sha256(compiler.encode()).hexdigest()[:12]
        build_dir /= f"msvc-{toolchain['msvc_toolset']}-{identity}"
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
        generator = 'Ninja' if target.endswith('-msvc') else 'MinGW Makefiles'
        args += ['-G', generator, '-DCMAKE_SYSTEM_NAME=Windows',
                 f'-DCMAKE_SYSTEM_PROCESSOR={processor}']
        if target.endswith('-msvc'):
            args += ['-DCMAKE_C_COMPILER=clang-cl', '-DCMAKE_CXX_COMPILER=clang-cl',
                     f'-DCMAKE_C_COMPILER_TARGET={target}',
                     f'-DCMAKE_CXX_COMPILER_TARGET={target}',
                     '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL']
    for key in ('CC', 'CXX'):
        if os.environ.get(key):
            language = 'C' if key == 'CC' else 'CXX'
            args.append(f'-DCMAKE_{language}_COMPILER={os.environ[key]}')
    if 'apple' in target:
        args.append('-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0')
    subprocess.run(args, check=True)
    if toolchain is not None:
        verify_msvc_release_cache(build_dir)
    subprocess.run(['cmake', '--build', str(build_dir), '--config', 'Release',
                    '--parallel', '4'], check=True)
    subprocess.run(['cmake', '--install', str(build_dir), '--config', 'Release'], check=True)
    if toolchain is not None:
        toolchain.update(target=target, library_sha256=hashlib.sha256((prefix / 'lib/hs.lib').read_bytes()).hexdigest())
        (prefix / MSVC_TOOLCHAIN_FILE).write_text(json.dumps(toolchain, sort_keys=True, indent=2) + '\n')


def pack(target, prefix, output):
    library = library_path(target)
    required = [prefix / library, prefix / 'include/hs/hs.h']
    for path in required:
        if not path.is_file():
            raise ValueError(f'Missing installed file: {path}')
    output.mkdir(parents=True, exist_ok=True)
    destination = output / asset_name(target)
    files = [(prefix / library, library)]
    if target.endswith('-msvc'):
        msvc_archive_toolchain(prefix, target)
        files.append((prefix / MSVC_TOOLCHAIN_FILE, MSVC_TOOLCHAIN_FILE))
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
