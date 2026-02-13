#!/bin/bash
# dedupe installation script
# Usage: ./install.sh [install_path]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_PATH="${1:-/usr/local/bin}"
DEDUPE_SCRIPT="$SCRIPT_DIR/dedupe"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== dedupe Installation ==="
echo ""

# Check if dedupe script exists
if [ ! -f "$DEDUPE_SCRIPT" ]; then
    echo -e "${RED}Error: dedupe script not found in $SCRIPT_DIR${NC}"
    exit 1
fi

# Make executable
chmod +x "$DEDUPE_SCRIPT"

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"

# Test dedupe script
echo ""
echo "Testing dedupe script..."
if ! python3 -m py_compile "$DEDUPE_SCRIPT"; then
    echo -e "${RED}Error: dedupe script has syntax errors${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Script compiles successfully${NC}"

# Check if we need sudo for system install
if [[ "$INSTALL_PATH" == "/usr/local/bin" ]] || [[ "$INSTALL_PATH" == "/usr/bin" ]]; then
    if [ ! -w "$INSTALL_PATH" ]; then
        echo ""
        echo -e "${YELLOW}System installation requires sudo privileges${NC}"
        SUDO="sudo"
    else
        SUDO=""
    fi
else
    SUDO=""
    # Create directory if it doesn't exist
    mkdir -p "$INSTALL_PATH"
fi

# Install
echo ""
echo "Installing dedupe to $INSTALL_PATH..."
INSTALL_CMD="$SUDO cp \"$DEDUPE_SCRIPT\" \"$INSTALL_PATH/dedupe\""
if eval "$INSTALL_CMD"; then
    echo -e "${GREEN}✓ dedupe installed successfully${NC}"
else
    echo -e "${RED}Error: Installation failed${NC}"
    exit 1
fi

# Make sure it's executable
$SUDO chmod +x "$INSTALL_PATH/dedupe"

# Verify installation
echo ""
echo "Verifying installation..."
if command -v dedupe &> /dev/null; then
    echo -e "${GREEN}✓ dedupe is now available in your PATH${NC}"
    echo ""
    echo "Run 'dedupe --help' to get started"
else
    echo -e "${YELLOW}⚠ dedupe installed but may not be in your PATH${NC}"
    echo "Add $INSTALL_PATH to your PATH or use the full path:"
    echo "  $INSTALL_PATH/dedupe --help"
fi

echo ""
echo "=== Installation Complete ==="
