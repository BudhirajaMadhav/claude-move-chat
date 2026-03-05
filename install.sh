#!/bin/bash
#
# Install script for claude-move-chat and claude-search-chat
#

set -e

INSTALL_DIR="$HOME/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing claude chat tools..."

# Create install directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Install claude-move-chat
cp "$SCRIPT_DIR/move-chat.py" "$INSTALL_DIR/claude-move-chat-core.py"
cp "$SCRIPT_DIR/move-chat-interactive.sh" "$INSTALL_DIR/claude-move-chat"
chmod +x "$INSTALL_DIR/claude-move-chat-core.py"
chmod +x "$INSTALL_DIR/claude-move-chat"
sed -i '' "s|MOVE_SCRIPT=.*|MOVE_SCRIPT=\"$INSTALL_DIR/claude-move-chat-core.py\"|" "$INSTALL_DIR/claude-move-chat"
echo "  Installed: claude-move-chat"

# Install claude-search-chat
cp "$SCRIPT_DIR/search-chat.py" "$INSTALL_DIR/claude-search-chat-core.py"
cp "$SCRIPT_DIR/search-chat-interactive.sh" "$INSTALL_DIR/claude-search-chat"
chmod +x "$INSTALL_DIR/claude-search-chat-core.py"
chmod +x "$INSTALL_DIR/claude-search-chat"
sed -i '' "s|SEARCH_SCRIPT=.*|SEARCH_SCRIPT=\"$INSTALL_DIR/claude-search-chat-core.py\"|" "$INSTALL_DIR/claude-search-chat"
echo "  Installed: claude-search-chat"

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
    echo "Done! Available commands:"
    echo "  claude-move-chat    - Move chat sessions between projects"
    echo "  claude-search-chat  - Search across chat history"
fi
