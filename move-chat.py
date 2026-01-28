#!/usr/bin/env python3
"""
Chat Migration Tool for Claude Code

Moves chat sessions between Claude Code projects.
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from datetime import datetime


CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"


def encode_path(path: str) -> str:
    """Encode a project path to Claude's directory naming convention."""
    # Replace / with - and special chars like @ and . with -
    encoded = path.replace("/", "-")
    encoded = re.sub(r"[@.]", "-", encoded)
    return encoded


def get_project_dir(project_path: str) -> Path:
    """Get the Claude project directory for a given project path."""
    encoded = encode_path(project_path)
    return PROJECTS_DIR / encoded


def load_sessions_index(project_dir: Path, original_path: str = None) -> dict:
    """Load the sessions-index.json file for a project."""
    index_path = project_dir / "sessions-index.json"
    if not index_path.exists():
        return {"version": 1, "entries": [], "originalPath": original_path or ""}
    with open(index_path, "r") as f:
        return json.load(f)


def save_sessions_index(project_dir: Path, index: dict) -> None:
    """Save the sessions-index.json file for a project."""
    index_path = project_dir / "sessions-index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)


def find_session_in_index(index: dict, session_id: str) -> tuple[int, dict] | None:
    """Find a session in the index by ID. Returns (index, session) or None."""
    for i, session in enumerate(index.get("entries", [])):
        if session.get("sessionId") == session_id:
            return i, session
    return None


def create_session_entry(session_id: str, project_dir: Path, project_path: str) -> dict:
    """Create a minimal session entry for an unindexed session."""
    jsonl_path = project_dir / f"{session_id}.jsonl"
    return {
        "sessionId": session_id,
        "fullPath": str(jsonl_path),
        "projectPath": project_path,
        "summary": "Migrated session",
        "created": datetime.now().isoformat(),
        "modified": datetime.now().isoformat(),
    }


def list_sessions(project_path: str, verbose: bool = False) -> None:
    """List all sessions in a project."""
    project_dir = get_project_dir(project_path)

    if not project_dir.exists():
        print(f"Error: Project directory does not exist: {project_dir}")
        sys.exit(1)

    index = load_sessions_index(project_dir)
    sessions = index.get("entries", [])

    if not sessions:
        print(f"No sessions found in project: {project_path}")
        return

    print(f"Sessions in {project_path}:")
    print(f"Project dir: {project_dir}\n")

    for session in sessions:
        session_id = session.get("sessionId", "unknown")
        summary = session.get("summary") or session.get("firstPrompt", "No summary")[:60]
        modified = session.get("modified", "unknown")

        # Check if JSONL file exists
        jsonl_path = project_dir / f"{session_id}.jsonl"
        jsonl_exists = jsonl_path.exists()

        # Check if session subdirectory exists
        subdir_path = project_dir / session_id
        subdir_exists = subdir_path.exists()

        print(f"  {session_id}")
        print(f"    Summary: {summary}")
        print(f"    Modified: {modified}")
        if verbose:
            print(f"    JSONL exists: {jsonl_exists}")
            print(f"    Subdir exists: {subdir_exists}")
        print()


def move_session(
    session_id: str,
    source_path: str,
    dest_path: str,
    dry_run: bool = False,
    verbose: bool = False
) -> None:
    """Move a session from source project to destination project."""

    source_dir = get_project_dir(source_path)
    dest_dir = get_project_dir(dest_path)

    # Validate source project exists
    if not source_dir.exists():
        print(f"Error: Source project directory does not exist: {source_dir}")
        sys.exit(1)

    # Create destination project if it doesn't exist
    if not dest_dir.exists():
        if verbose or dry_run:
            print(f"Destination project does not exist, will create: {dest_dir}")
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)

    # Load source index and find session
    source_index = load_sessions_index(source_dir)
    session_result = find_session_in_index(source_index, session_id)

    # Check if session file exists even if not indexed
    source_jsonl = source_dir / f"{session_id}.jsonl"

    if session_result is None:
        if source_jsonl.exists():
            # Session file exists but not in index - create a temporary entry
            if verbose:
                print(f"Session not in index but file exists, creating entry")
            session_idx = None  # Not in index
            session_data = create_session_entry(session_id, source_dir, source_path)
        else:
            print(f"Error: Session {session_id} not found in source project")
            sys.exit(1)
    else:
        session_idx, session_data = session_result

    # Define source files
    source_subdir = source_dir / session_id

    # Define destination files
    dest_jsonl = dest_dir / f"{session_id}.jsonl"
    dest_subdir = dest_dir / session_id

    # Check if session already exists in destination
    dest_index = load_sessions_index(dest_dir, dest_path)
    if find_session_in_index(dest_index, session_id) is not None:
        print(f"Error: Session {session_id} already exists in destination project")
        sys.exit(1)

    if verbose or dry_run:
        print(f"Source project: {source_path}")
        print(f"Source dir: {source_dir}")
        print(f"Destination project: {dest_path}")
        print(f"Destination dir: {dest_dir}")
        print(f"Session ID: {session_id}")
        print(f"Summary: {session_data.get('summary') or session_data.get('firstPrompt', 'No summary')[:60]}")
        print()

    # Prepare new session entry for destination
    new_session_data = session_data.copy()
    new_session_data["fullPath"] = str(dest_jsonl)
    new_session_data["projectPath"] = dest_path
    new_session_data["modified"] = datetime.now().isoformat()

    if dry_run:
        print("DRY RUN - No changes will be made\n")

        if not dest_dir.exists():
            print(f"Would create destination directory: {dest_dir}")

        if source_jsonl.exists():
            print(f"Would copy: {source_jsonl} -> {dest_jsonl}")
        else:
            print(f"Warning: Source JSONL does not exist: {source_jsonl}")

        if source_subdir.exists():
            print(f"Would copy: {source_subdir}/ -> {dest_subdir}/")

        print(f"Would add session to destination sessions-index.json")
        if session_idx is not None:
            print(f"Would remove session from source sessions-index.json")
        else:
            print(f"Session not in source index, no index update needed")

        if source_jsonl.exists():
            print(f"Would delete: {source_jsonl}")
        if source_subdir.exists():
            print(f"Would delete: {source_subdir}/")

        print("\nDry run complete.")
        return

    # Perform the migration
    try:
        # Step 1: Copy JSONL file
        if source_jsonl.exists():
            if verbose:
                print(f"Copying {source_jsonl} -> {dest_jsonl}")
            shutil.copy2(source_jsonl, dest_jsonl)
        else:
            print(f"Warning: Source JSONL does not exist: {source_jsonl}")

        # Step 2: Copy session subdirectory if exists
        if source_subdir.exists():
            if verbose:
                print(f"Copying {source_subdir}/ -> {dest_subdir}/")
            shutil.copytree(source_subdir, dest_subdir)

        # Step 3: Add entry to destination sessions-index.json
        if verbose:
            print("Adding session to destination sessions-index.json")
        dest_index["entries"].append(new_session_data)
        save_sessions_index(dest_dir, dest_index)

        # Step 4: Remove entry from source sessions-index.json (if it was there)
        if session_idx is not None:
            if verbose:
                print("Removing session from source sessions-index.json")
            source_index["entries"].pop(session_idx)
            save_sessions_index(source_dir, source_index)
        elif verbose:
            print("Session was not in source index, skipping index update")

        # Step 5: Delete source files
        if source_jsonl.exists():
            if verbose:
                print(f"Deleting {source_jsonl}")
            source_jsonl.unlink()

        if source_subdir.exists():
            if verbose:
                print(f"Deleting {source_subdir}/")
            shutil.rmtree(source_subdir)

        print(f"Successfully moved session {session_id}")
        print(f"  From: {source_path}")
        print(f"  To: {dest_path}")

    except Exception as e:
        print(f"Error during migration: {e}")
        print("Attempting rollback...")

        # Rollback: remove destination files if they exist
        try:
            if dest_jsonl.exists():
                dest_jsonl.unlink()
            if dest_subdir.exists():
                shutil.rmtree(dest_subdir)

            # Restore destination index
            dest_index_restored = load_sessions_index(dest_dir)
            dest_index_restored["entries"] = [
                s for s in dest_index_restored.get("entries", [])
                if s.get("sessionId") != session_id
            ]
            save_sessions_index(dest_dir, dest_index_restored)

            print("Rollback complete. Source files preserved.")
        except Exception as rollback_error:
            print(f"Rollback failed: {rollback_error}")
            print("Manual intervention may be required.")

        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Move chat sessions between Claude Code projects"
    )

    parser.add_argument(
        "session_id",
        nargs="?",
        help="Session ID to move"
    )
    parser.add_argument(
        "--list",
        metavar="PROJECT",
        help="List sessions in a project"
    )
    parser.add_argument(
        "--from",
        dest="source",
        metavar="PROJECT",
        help="Source project path"
    )
    parser.add_argument(
        "--to",
        dest="dest",
        metavar="PROJECT",
        help="Destination project path"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.list:
        list_sessions(args.list, verbose=args.verbose)
    elif args.session_id and args.source and args.dest:
        move_session(
            args.session_id,
            args.source,
            args.dest,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
    else:
        parser.print_help()
        print("\nExamples:")
        print("  # List sessions in a project")
        print("  ./move-chat.py --list /Users/user/project")
        print()
        print("  # Move a session")
        print("  ./move-chat.py <session-id> --from /source/project --to /dest/project")
        print()
        print("  # Preview without changes")
        print("  ./move-chat.py <session-id> --from /source --to /dest --dry-run")
        sys.exit(1)


if __name__ == "__main__":
    main()
