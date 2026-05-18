#!/bin/bash
set -e

APP_NAME="digest"
INSTALL_DIR="/opt/${APP_NAME}"
DESKTOP_DIR="/usr/share/applications"

echo "=== Installing ${APP_NAME} ==="

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found."
    exit 1
fi

echo "Installing dependencies..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3-gi python3-gi-cairo gir1.2-gtk-3.0 \
    python3-requests \
    gir1.2-poppler-0.18 \
    tesseract-ocr python3-pil python3-venv

echo "Copying application files..."
sudo mkdir -p "${INSTALL_DIR}"
sudo cp -r "$(dirname "$0")"/* "${INSTALL_DIR}/"
sudo chmod +x "${INSTALL_DIR}/digest.py"

echo "Creating virtual environment..."
sudo python3 -m venv --system-site-packages "${INSTALL_DIR}/venv"
sudo "${INSTALL_DIR}/venv/bin/pip" install --quiet pypdf pytesseract

echo "Installing icon..."
sudo mkdir -p /usr/share/icons/hicolor/scalable/apps
sudo cp "${INSTALL_DIR}/digest.svg" /usr/share/icons/hicolor/scalable/apps/digest.svg
sudo gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true

echo "Installing desktop entry..."
sudo cp "${INSTALL_DIR}/digest.desktop" "${DESKTOP_DIR}/"
sudo update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true

echo "Creating launcher..."
sudo tee /usr/local/bin/digest > /dev/null << 'EOF'
#!/bin/bash
exec /opt/digest/venv/bin/python3 /opt/digest/digest.py "$@"
EOF
sudo chmod +x /usr/local/bin/digest

echo "Creating config directory..."
mkdir -p "$HOME/.config/${APP_NAME}"

echo ""
echo "=== Installation complete! ==="
echo "Run: digest"
echo "Or search for 'Digest' in your application menu."
echo ""
echo "On first launch, open Settings (⚙) and enter your OpenRouter API key."
