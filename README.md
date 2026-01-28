# claude-move-chat

Move chat sessions between Claude Code projects.

## Why?

Claude Code stores chat sessions per-project directory. If you start a chat in the wrong project or want to reorganize your chats, this tool lets you move them.

## Requirements

- Python 3.8+
- zsh (default on macOS)
- [fzf](https://github.com/junegunn/fzf) (optional, for fuzzy selection)

```bash
# Install fzf (recommended)
brew install fzf
```

## Installation

```bash
git clone https://github.com/yourusername/claude-move-chat.git
cd claude-move-chat
./install.sh
```

Make sure `~/.local/bin` is in your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Usage

### Interactive Mode (recommended)

```bash
claude-move-chat
```

This launches an interactive TUI where you can:
1. Select source project
2. Select chat session to move
3. Select destination project (or enter custom path)
4. Confirm and execute

### Direct Commands

```bash
# List sessions in a project
claude-move-chat-core.py --list /path/to/project

# Move a session (dry-run first)
claude-move-chat-core.py <session-id> \
    --from /path/to/source \
    --to /path/to/destination \
    --dry-run

# Execute the move
claude-move-chat-core.py <session-id> \
    --from /path/to/source \
    --to /path/to/destination
```

### Options

| Flag | Description |
|------|-------------|
| `--list <project>` | List all sessions in a project |
| `--from <project>` | Source project path |
| `--to <project>` | Destination project path |
| `--dry-run` | Preview changes without modifying files |
| `--verbose`, `-v` | Show detailed output |

## How It Works

Claude Code stores project data in `~/.claude/projects/[encoded-path]/`:

- `[sessionId].jsonl` - Chat transcript
- `[sessionId]/` - Session subdirectory (if exists)
- `sessions-index.json` - Index of all sessions

This tool:
1. Copies the session files to the destination project
2. Updates both `sessions-index.json` files
3. Deletes the source files

Global data (file history, todos) is indexed by session ID and doesn't need to be moved.

## License

MIT
