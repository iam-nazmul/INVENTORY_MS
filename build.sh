#!/bin/bash
# Build script for Inventory Management System
set -e

echo "Building Inventory Management System..."

# Ensure virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating..."
    uv venv .venv
fi

source .venv/bin/activate

# Ensure PyInstaller is installed in the virtual environment
if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "PyInstaller not installed in the virtual environment. Installing..."
    uv add pyinstaller
fi

# Clean previous builds
rm -rf dist build *.spec

# Determine platform
ICON_PATH="asset/logo/LogoIMS.png"
ICON_ARG=""
if [[ -f "$ICON_PATH" ]]; then
    ICON_ARG="--icon $ICON_PATH"
fi

# Build with PyInstaller
pyinstaller --onefile \
    --windowed \
    --name ims \
    $ICON_ARG \
    --hidden-import PyQt6.QtCore \
    --hidden-import PyQt6.QtGui \
    --hidden-import PyQt6.QtWidgets \
    --hidden-import matplotlib \
    --hidden-import matplotlib.backends.backend_qt5agg \
    --collect-all matplotlib \
    main.py

echo "Build complete! Executable created in dist/ directory"