#!/bin/bash
#
# Install script for claude-move-chat
#

set -e

INSTALL_DIR="$HOME/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing claude-move-chat..."

# Create install directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Copy scripts
cp "$SCRIPT_DIR/move-chat.py" "$INSTALL_DIR/claude-move-chat-core.py"
cp "$SCRIPT_DIR/move-chat-interactive.sh" "$INSTALL_DIR/claude-move-chat"

# Make executable
chmod +x "$INSTALL_DIR/claude-move-chat-core.py"
chmod +x "$INSTALL_DIR/claude-move-chat"

# Update the interactive script to reference the installed core script
sed -i '' "s|MOVE_SCRIPT=.*|MOVE_SCRIPT=\"$INSTALL_DIR/claude-move-chat-core.py\"|" "$INSTALL_DIR/claude-move-chat"

echo ""
echo "Installed to: $INSTALL_DIR/claude-move-chat"

# Check if install dir is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "NOTE: $INSTALL_DIR is not in your PATH."
    echo "Add the following to your ~/.zshrc or ~/.bashrc:"
    echo ""
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then restart your terminal or run: source ~/.zshrc"
else
    echo ""
    echo "Done! You can now run: claude-move-chat"
fi
