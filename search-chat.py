#!/usr/bin/env python3
"""
Chat Search Tool for Claude Code

Search across all Claude Code chat history content - user messages,
assistant responses, and tool usage.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"


def get_project_original_path(project_dir: Path) -> str:
    """Get the original project path from sessions-index.json or first JSONL."""
    index_file = project_dir / "sessions-index.json"
    if index_file.exists():
        try:
            data = json.loads(index_file.read_text())
            path = data.get("originalPath", "")
            if path:
                return path
        except Exception:
            pass

    # Fallback: read cwd from first JSONL
    for jsonl_file in sorted(project_dir.glob("*.jsonl"), key=os.path.getmtime, reverse=True):
        try:
            with open(jsonl_file) as f:
                for line in f:
                    entry = json.loads(line)
                    cwd = entry.get("cwd", "")
                    if cwd:
                        return cwd
        except Exception:
            continue

    return project_dir.name


def get_session_title(project_dir: Path, session_id: str) -> str:
    """Get session title from index or first user message."""
    index_file = project_dir / "sessions-index.json"
    if index_file.exists():
        try:
            data = json.loads(index_file.read_text())
            for entry in data.get("entries", []):
                if entry.get("sessionId") == session_id:
                    return entry.get("summary") or entry.get("firstPrompt", "")[:80] or "No title"
        except Exception:
            pass
    return ""


def extract_text_from_content(content) -> str:
    """Extract plain text from message content (string or content blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    # Include tool name and input for searchability
                    tool_name = block.get("name", "")
                    tool_input = json.dumps(block.get("input", {}))
                    parts.append(f"[tool:{tool_name}] {tool_input}")
                elif block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, str):
                        parts.append(result_content)
                    elif isinstance(result_content, list):
                        for rc in result_content:
                            if isinstance(rc, dict) and rc.get("type") == "text":
                                parts.append(rc.get("text", ""))
        return "\n".join(parts)
    return ""


def search_session_file(args: tuple) -> list:
    """Search a single session JSONL file. Designed for multiprocessing."""
    jsonl_path, pattern, case_insensitive, roles_filter, context_chars = args
    results = []
    session_id = Path(jsonl_path).stem
    project_dir = Path(jsonl_path).parent

    flags = re.IGNORECASE if case_insensitive else 0
    try:
        compiled = re.compile(pattern, flags)
    except re.error:
        # Treat as literal string
        compiled = re.compile(re.escape(pattern), flags)

    try:
        with open(jsonl_path) as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg = entry.get("message", {})
                role = msg.get("role", entry.get("type", ""))

                if roles_filter and role not in roles_filter:
                    continue

                content = msg.get("content", "")
                text = extract_text_from_content(content)

                if not text:
                    continue

                match = compiled.search(text)
                if match:
                    # Extract context around match
                    start = max(0, match.start() - context_chars)
                    end = min(len(text), match.end() + context_chars)
                    snippet = text[start:end].strip()
                    # Clean up whitespace
                    snippet = re.sub(r'\s+', ' ', snippet)

                    timestamp = entry.get("timestamp", "")
                    if not timestamp:
                        # Try to get from message
                        timestamp = msg.get("timestamp", "")

                    results.append({
                        "session_id": session_id,
                        "project_dir": str(project_dir),
                        "role": role,
                        "line_num": line_num,
                        "snippet": snippet,
                        "match_start": match.start(),
                        "timestamp": timestamp,
                    })
    except Exception as e:
        pass

    return results


def search_chats(
    query: str,
    project_filter: str = None,
    case_insensitive: bool = True,
    roles: list = None,
    max_results: int = 50,
    context_chars: int = 120,
    regex: bool = False,
    workers: int = None,
) -> list:
    """Search across all Claude Code chat sessions."""

    if not regex:
        pattern = re.escape(query)
    else:
        pattern = query

    roles_filter = set(roles) if roles else None

    # Collect all JSONL files to search
    jsonl_files = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        # Apply project filter
        if project_filter:
            original_path = get_project_original_path(project_dir)
            if project_filter.lower() not in original_path.lower() and \
               project_filter.lower() not in project_dir.name.lower():
                continue

        for jsonl_file in project_dir.glob("*.jsonl"):
            if jsonl_file.stem == "sessions-index":
                continue
            jsonl_files.append(str(jsonl_file))

    if not jsonl_files:
        return []

    # Search in parallel
    all_results = []
    search_args = [
        (f, pattern, case_insensitive, roles_filter, context_chars)
        for f in jsonl_files
    ]

    if workers is None:
        workers = min(8, os.cpu_count() or 4)

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(search_session_file, args): args for args in search_args}
        for future in as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception:
                pass

    # Sort by timestamp (newest first), then limit
    all_results.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return all_results[:max_results]


def format_results(results: list, verbose: bool = False) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."

    # Group by session
    sessions = {}
    for r in results:
        key = (r["project_dir"], r["session_id"])
        if key not in sessions:
            sessions[key] = []
        sessions[key].append(r)

    lines = []
    lines.append(f"Found {len(results)} match(es) across {len(sessions)} session(s):\n")

    for (project_dir_str, session_id), matches in sessions.items():
        project_dir = Path(project_dir_str)
        original_path = get_project_original_path(project_dir)
        title = get_session_title(project_dir, session_id)

        # Shorten project path for display
        short_project = original_path.replace(str(Path.home()), "~")

        lines.append(f"\033[1;34m{short_project}\033[0m")
        if title:
            lines.append(f"  \033[1;33m{title}\033[0m")
        lines.append(f"  \033[0;35mSession: {session_id}\033[0m")
        lines.append("")

        for m in matches:
            role_color = "\033[0;32m" if m["role"] == "user" else "\033[0;36m"
            role_label = m["role"]
            snippet = m["snippet"]

            lines.append(f"  {role_color}[{role_label}]\033[0m {snippet}")

        lines.append("")

    return "\n".join(lines)


def format_for_fzf(results: list) -> str:
    """Format results as pipe-delimited lines for fzf consumption."""
    lines = []
    for r in results:
        project_dir = Path(r["project_dir"])
        original_path = get_project_original_path(project_dir)
        short_project = original_path.replace(str(Path.home()), "~")
        title = get_session_title(project_dir, r["session_id"])
        role = r["role"]
        snippet = r["snippet"][:200]

        # Format: project | title | role | snippet | session_id
        line = f"{short_project}\t{title[:50]}\t{role}\t{snippet}\t{r['session_id']}"
        lines.append(line)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search across Claude Code chat history"
    )

    parser.add_argument(
        "query",
        help="Search query (text or regex with --regex)"
    )
    parser.add_argument(
        "--project", "-p",
        help="Filter to a specific project (substring match on path)"
    )
    parser.add_argument(
        "--case-sensitive", "-s",
        action="store_true",
        help="Case-sensitive search (default: case-insensitive)"
    )
    parser.add_argument(
        "--regex", "-r",
        action="store_true",
        help="Treat query as a regular expression"
    )
    parser.add_argument(
        "--role",
        choices=["user", "assistant"],
        action="append",
        help="Filter by message role (can be specified multiple times)"
    )
    parser.add_argument(
        "--max-results", "-n",
        type=int,
        default=50,
        help="Maximum number of results (default: 50)"
    )
    parser.add_argument(
        "--context", "-c",
        type=int,
        default=120,
        help="Characters of context around match (default: 120)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show session IDs and extra details"
    )
    parser.add_argument(
        "--fzf",
        action="store_true",
        help="Output in fzf-compatible format (tab-delimited)"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Number of parallel workers (default: auto)"
    )

    args = parser.parse_args()

    results = search_chats(
        query=args.query,
        project_filter=args.project,
        case_insensitive=not args.case_sensitive,
        roles=args.role,
        max_results=args.max_results,
        context_chars=args.context,
        regex=args.regex,
        workers=args.workers,
    )

    if args.fzf:
        print(format_for_fzf(results))
    else:
        print(format_results(results, verbose=args.verbose))


if __name__ == "__main__":
    main()
