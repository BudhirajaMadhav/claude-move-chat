# claude-chat-tools

Utilities for managing Claude Code chat sessions — move chats between projects and search across chat history.

## Tools

### claude-move-chat

Move chat sessions between Claude Code projects. Useful when you start a chat in the wrong project or want to reorganize.

### claude-search-chat

Full-text search across all Claude Code chat history. Search by content, filter by project or role, and get session IDs for `claude --resume`.

## Requirements

- Python 3.8+
- zsh (default on macOS)
- [fzf](https://github.com/junegunn/fzf) (optional, for fuzzy selection in move-chat)

```bash
# Install fzf (recommended)
brew install fzf
```

## Installation

```bash
git clone https://github.com/BudhirajaMadhav/claude-move-chat.git
cd claude-move-chat
./install.sh
```

Make sure `~/.local/bin` is in your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Usage

### claude-search-chat

```bash
# Search all chats
claude-search-chat "error handling"

# Filter by project
claude-search-chat "stitch" -p queryon

# Search only user messages
claude-search-chat "implement" --role user

# Regex search
claude-search-chat -r "PR #\d+" -n 10

# Case-sensitive search
claude-search-chat -s "MyClassName"
```

Results include session IDs for resuming:

```
~/Developer/my-project
  Fix authentication flow
  Session: 7e9ce563-ff99-4897-970b-8d37f216e90e

  [user] implement OAuth error handling...
```

Resume with: `claude --resume 7e9ce563-ff99-4897-970b-8d37f216e90e`

#### Search Options

| Flag | Description |
|------|-------------|
| `-p`, `--project` | Filter by project path (substring match) |
| `--role` | Filter by role (`user` or `assistant`) |
| `-r`, `--regex` | Treat query as regex |
| `-s` | Case-sensitive search |
| `-n`, `--max-results` | Max results (default: 50) |
| `-c`, `--context` | Context chars around match (default: 120) |
| `-v`, `--verbose` | Show extra details |

### claude-move-chat

#### Interactive Mode (recommended)

```bash
claude-move-chat
```

This launches an interactive TUI where you can:
1. Select source project
2. Select chat session to move
3. Select destination project (or enter custom path)
4. Confirm and execute

#### Direct Commands

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

#### Move Options

| Flag | Description |
|------|-------------|
| `--list <project>` | List all sessions in a project |
| `--from <project>` | Source project path |
| `--to <project>` | Destination project path |
| `--dry-run` | Preview changes without modifying files |
| `--verbose`, `-v` | Show detailed output |

## How It Works

Claude Code stores project data in `~/.claude/projects/[encoded-path]/`:

- `[sessionId].jsonl` — Chat transcript (JSONL with user/assistant messages)
- `[sessionId]/` — Session subdirectory (if exists)
- `sessions-index.json` — Index of all sessions

**Search** reads all JSONL files in parallel, extracting text from user messages, assistant responses, and tool usage.

**Move** copies session files to the destination project, updates both `sessions-index.json` files, and removes the source files. Global data (file history, todos) is indexed by session ID and doesn't need to be moved.

## License

MIT
