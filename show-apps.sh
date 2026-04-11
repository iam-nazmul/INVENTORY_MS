#!/bin/bash
# Create a desktop entry for Inventory MS so it appears in Ubuntu's app launcher.

set -euo pipefail

APP_NAME="Inventory MS"
DESKTOP_ID="inventory-ms"
EXEC_PATH=""
ICON_SRC="asset/logo/LogoIMS.png"
ICON_DEST="$HOME/.local/share/icons/${DESKTOP_ID}.png"
DESKTOP_FILE="$HOME/.local/share/applications/${DESKTOP_ID}.desktop"

# Detect executable location.
if [ -x "/usr/bin/inventory_ms" ]; then
    EXEC_PATH="/usr/bin/inventory_ms"
elif [ -x "./dist/inventory_ms" ]; then
    EXEC_PATH="$(pwd)/dist/inventory_ms"
elif [ -x "./inventory_ms" ]; then
    EXEC_PATH="$(pwd)/inventory_ms"
else
    echo "Error: inventory_ms executable not found."
    echo "Place the built executable at /usr/bin/inventory_ms or ./dist/inventory_ms."
    exit 1
fi

# Ensure icon exists and copy it to the local icon folder.
if [ ! -f "$ICON_SRC" ]; then
    echo "Warning: icon file not found at $ICON_SRC. Desktop entry will be created without a custom icon."
    ICON_DEST=""i

mkdir -p "$(dirname "$DESKTOP_FILE")"
if [ -n "$ICON_DEST" ]; then
    mkdir -p "$(dirname "$ICON_DEST")"
    cp "$ICON_SRC" "$ICON_DEST"
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=${APP_NAME}
Comment=Inventory Management System
Exec=${EXEC_PATH}
Icon=${ICON_DEST:-inventory-ms}
Terminal=false
Categories=Utility;Business;
StartupWMClass=inventory_ms
EOF

chmod +x "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$(dirname "$DESKTOP_FILE")" >/dev/null 2>&1 || true
fi

echo "Desktop entry created: $DESKTOP_FILE"
echo "You can now open Activities and search for '${APP_NAME}'."
