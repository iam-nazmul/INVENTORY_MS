#!/usr/bin/env python3
"""
Cross-platform build and packaging script for Inventory Management System.
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / 'dist'
BUILD_DIR = ROOT / 'build'
SPEC_SUFFIX = '.spec'
ICON_BASE = ROOT / 'asset' / 'logo' / 'LogoIMS'
ICON_PNG = ICON_BASE.with_suffix('.png')
ICON_ICO = ICON_BASE.with_suffix('.ico')
ICON_ICNS = ICON_BASE.with_suffix('.icns')


def run_subprocess(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print('Command failed:', ' '.join(cmd))
        print(result.stderr)
        return False
    return True


def find_executable(name):
    from shutil import which
    return which(name)


def get_pyinstaller_cmd():
    if find_executable('pyinstaller'):
        return ['pyinstaller']
    if find_executable('uv'):
        return ['uv', 'run', 'pyinstaller']
    raise RuntimeError('PyInstaller not found. Install with `uv add pyinstaller` or `pip install pyinstaller`.' )


def generate_platform_icons():
    try:
        from PIL import Image
    except ImportError:
        return

    if ICON_PNG.exists():
        if not ICON_ICO.exists():
            with Image.open(ICON_PNG) as image:
                image.save(ICON_ICO, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        if not ICON_ICNS.exists():
            with Image.open(ICON_PNG) as image:
                image.save(ICON_ICNS, format='ICNS')


def read_version():
    pyproject = ROOT / 'pyproject.toml'
    if not pyproject.exists():
        return '0.0.0'
    with pyproject.open('r', encoding='utf-8') as fh:
        for line in fh:
            if line.strip().startswith('version'):
                _, value = line.split('=', 1)
                return value.strip().strip('"').strip("'")
    return '0.0.0'


def clean_build():
    for path in [DIST_DIR, BUILD_DIR]:
        if path.exists():
            shutil.rmtree(path)
    for file in ROOT.iterdir():
        if file.suffix == SPEC_SUFFIX:
            file.unlink()


def build_executable(name, windowed=True):
    exe_path = DIST_DIR / name
    if exe_path.exists():
        print(f'Executable {exe_path} already exists. Skipping build.')
        return True

    generate_platform_icons()
    cmd = get_pyinstaller_cmd() + [
        '--onefile',
        '--name', name,
    ]
    if windowed:
        cmd.append('--windowed')

    if platform.system() == 'Windows' and ICON_ICO.exists():
        cmd += ['--icon', str(ICON_ICO)]
    elif platform.system() == 'Darwin' and ICON_ICNS.exists():
        cmd += ['--icon', str(ICON_ICNS)]
    elif ICON_PNG.exists():
        cmd += ['--icon', str(ICON_PNG)]

    cmd += [
        '--hidden-import', 'PyQt6.QtCore',
        '--hidden-import', 'PyQt6.QtGui',
        '--hidden-import', 'PyQt6.QtWidgets',
        '--hidden-import', 'matplotlib',
        '--hidden-import', 'matplotlib.backends.backend_qt5agg',
        '--collect-all', 'matplotlib',
        'main.py'
    ]
    return run_subprocess(cmd)


def build_app(name):
    if platform.system() != 'Darwin':
        print('macOS app packaging must be run on macOS.')
        return False
    print('Building macOS .app bundle...')
    return build_executable(name, windowed=True)


def build_deb(name, version):
    if platform.system() != 'Linux':
        print('Debian packaging must be run on Linux.')
        return False

    exe_path = DIST_DIR / name
    if not exe_path.exists():
        print(f'Executable not found: {exe_path}. Building it first...')
        if not build_executable(name, windowed=True):
            return False

    pkg_root = ROOT / 'deb_pkg'
    debian_dir = pkg_root / 'DEBIAN'
    bin_dir = pkg_root / 'usr' / 'bin'
    applications_dir = pkg_root / 'usr' / 'share' / 'applications'

    if pkg_root.exists():
        shutil.rmtree(pkg_root)
    bin_dir.mkdir(parents=True, exist_ok=True)
    applications_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(exe_path, bin_dir / name)
    os.chmod(bin_dir / name, 0o755)

    package_name = name.lower().replace('_', '-')

    # Create .desktop file
    desktop_file = applications_dir / f'{package_name}.desktop'
    desktop_text = f"""[Desktop Entry]
Name=Inventory Management System
Exec={name}
Type=Application
Categories=Office;Utility;
Terminal=false
"""
    desktop_file.write_text(desktop_text, encoding='utf-8')

    control = debian_dir / 'control'
    control.parent.mkdir(parents=True, exist_ok=True)

    control_text = f"""Package: {package_name}
Version: {version}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: IMS Developer <noreply@example.com>
Description: Inventory Management System - PyQt6 desktop application
"""
    control.write_text(control_text, encoding='utf-8')

    deb_file = DIST_DIR / f'{name}_{version}_amd64.deb'
    if deb_file.exists():
        deb_file.unlink()

    if not run_subprocess(['dpkg-deb', '--build', str(pkg_root), str(deb_file)]):
        return False

    print('Deb package created:', deb_file)
    return True


def main():
    parser = argparse.ArgumentParser(description='Build Inventory Management System artifacts.')
    parser.add_argument('--target', choices=['exe', 'app', 'deb', 'all'], default='all', help='Artifact type to build')
    parser.add_argument('--name', default='inventory_ms', help='Output binary/package base name')
    args = parser.parse_args()

    clean_build()
    version = read_version()

    if platform.system() == 'Windows' and args.target in ('exe', 'all'):
        print(f'Building executable: {args.name}')
        if not build_executable(args.name, windowed=True):
            return 1

    if platform.system() == 'Darwin' and args.target in ('app', 'all'):
        print(f'Building macOS app: {args.name}.app')
        if not build_app(args.name):
            return 1

    if platform.system() == 'Linux':
        if args.target in ('exe', 'all', 'deb'):
            print(f'Building executable: {args.name}')
            if not build_executable(args.name, windowed=True):
                return 1
        if args.target in ('deb', 'all'):
            print(f'Packaging DEB for: {args.name}')
            if not build_deb(args.name, version):
                return 1

    print('Build finished. Check the dist/ directory.')
    return 0


if __name__ == '__main__':
    sys.exit(main())