#!/bin/zsh
#
# Interactive Chat Search Tool for Claude Code
# Searches across all chat history content with fzf preview
#

set -e

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

CLAUDE_DIR="$HOME/.claude"
SEARCH_SCRIPT="$CLAUDE_DIR/search-chat.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ $# -eq 0 ]; then
    echo "${CYAN}Usage:${NC}"
    echo "  claude-search-chat <query>          Search all chats"
    echo "  claude-search-chat -p <project> <q> Filter by project"
    echo "  claude-search-chat -r <regex>       Regex search"
    echo "  claude-search-chat --role user <q>  Search only user messages"
    echo ""
    echo "${YELLOW}Options:${NC}"
    echo "  -p, --project   Filter by project path (substring match)"
    echo "  -r, --regex     Treat query as regex"
    echo "  -s              Case-sensitive search"
    echo "  --role          Filter by role (user/assistant)"
    echo "  -n              Max results (default: 50)"
    echo "  -c              Context chars around match (default: 120)"
    echo "  -v              Verbose (show session IDs)"
    echo ""

    if command -v fzf &> /dev/null; then
        echo "${BLUE}Tip: Pipe to fzf for interactive filtering:${NC}"
        echo "  claude-search-chat --fzf <query> | fzf --delimiter='\t' --with-nth=1..4"
    fi
    exit 0
fi

python3 "$SEARCH_SCRIPT" "$@"
