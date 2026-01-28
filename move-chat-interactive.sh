#!/bin/zsh
#
# Interactive Chat Migration Tool for Claude Code
# Uses fzf for selection if available, otherwise falls back to simple menus
#

set -e

# Ensure Homebrew paths are in PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

CLAUDE_DIR="$HOME/.claude"
PROJECTS_DIR="$CLAUDE_DIR/projects"
MOVE_SCRIPT="$CLAUDE_DIR/move-chat.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if fzf is available
use_fzf=false
if command -v fzf &> /dev/null; then
    use_fzf=true
fi

# Get list of projects with their original paths
get_projects() {
    for dir in "$PROJECTS_DIR"/-*/; do
        [ -d "$dir" ] || continue
        index_file="$dir/sessions-index.json"
        if [ -f "$index_file" ]; then
            original_path=$(python3 -c "import json; print(json.load(open('$index_file')).get('originalPath', 'Unknown'))" 2>/dev/null || echo "Unknown")
            session_count=$(python3 -c "import json; print(len(json.load(open('$index_file')).get('entries', [])))" 2>/dev/null || echo "0")
            echo "$original_path|$session_count|$dir"
        fi
    done
}

# Get sessions for a project
get_sessions() {
    local project_dir="$1"
    local index_file="$project_dir/sessions-index.json"

    if [ -f "$index_file" ]; then
        python3 -c "
import json
data = json.load(open('$index_file'))
for entry in data.get('entries', []):
    sid = entry.get('sessionId', 'unknown')
    # Use firstPrompt as the title/summary
    title = entry.get('firstPrompt', 'No title')[:50].replace('|', ' ')
    modified = entry.get('modified', 'unknown')[:10]
    print(f'{sid}|{title}|{modified}')
" 2>/dev/null
    fi
}

# Simple menu selection (fallback when fzf not available)
select_from_menu() {
    local prompt="$1"
    shift
    local options=("$@")

    echo "${CYAN}$prompt${NC}"
    echo ""

    local i=1
    for opt in "${options[@]}"; do
        echo "  ${YELLOW}$i)${NC} $opt"
        ((i++))
    done
    echo ""

    local selection
    while true; do
        read "selection?Enter number (1-${#options[@]}): "
        if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le "${#options[@]}" ]; then
            echo "${options[$selection]}"
            return
        fi
        echo "${RED}Invalid selection. Try again.${NC}"
    done
}

# Main interactive flow
main() {
    echo "${GREEN}=== Claude Code Chat Migration Tool ===${NC}"
    echo ""

    # Step 1: Get all projects
    echo "${BLUE}Loading projects...${NC}"

    project_data=("${(@f)$(get_projects | sort)}")

    if [ ${#project_data[@]} -eq 0 ]; then
        echo "${RED}No projects found in $PROJECTS_DIR${NC}"
        exit 1
    fi

    # Format projects for display
    typeset -a project_display
    typeset -A project_dirs
    typeset -A project_paths

    for item in "${project_data[@]}"; do
        local proj_path count proj_dir
        proj_path="${item%%|*}"
        local rest="${item#*|}"
        count="${rest%%|*}"
        proj_dir="${rest#*|}"
        display="$proj_path ($count sessions)"
        project_display+=("$display")
        project_dirs[$display]="$proj_dir"
        project_paths[$display]="$proj_path"
    done

    # Step 2: Select source project
    echo ""
    if $use_fzf; then
        echo "${CYAN}Select SOURCE project (use arrows/type to filter):${NC}"
        selected_source=$(printf '%s\n' "${project_display[@]}" | fzf --height=15 --reverse --prompt="Source > ")
    else
        selected_source=$(select_from_menu "Select SOURCE project:" "${project_display[@]}")
    fi

    if [ -z "$selected_source" ]; then
        echo "${RED}No project selected. Exiting.${NC}"
        exit 1
    fi

    source_dir="${project_dirs[$selected_source]}"
    source_path="${project_paths[$selected_source]}"

    echo "${GREEN}Selected source:${NC} $source_path"
    echo ""

    # Step 3: Get sessions from source project
    session_data=("${(@f)$(get_sessions "$source_dir")}")

    if [ ${#session_data[@]} -eq 0 ] || [ -z "${session_data[1]}" ]; then
        echo "${RED}No sessions found in this project.${NC}"
        exit 1
    fi

    # Format sessions for display
    typeset -a session_display
    typeset -A session_ids

    for item in "${session_data[@]}"; do
        [ -z "$item" ] && continue
        local session_id_val title_val modified_val rest_val display_val
        session_id_val="${item%%|*}"
        rest_val="${item#*|}"
        title_val="${rest_val%%|*}"
        modified_val="${rest_val#*|}"
        display_val="[$modified_val] $title_val"
        session_display+=("$display_val")
        session_ids[$display_val]="$session_id_val"
    done

    # Step 4: Select session to move
    if $use_fzf; then
        echo "${CYAN}Select session to MOVE (use arrows/type to filter):${NC}"
        selected_session=$(printf '%s\n' "${session_display[@]}" | fzf --height=15 --reverse --prompt="Session > ")
    else
        selected_session=$(select_from_menu "Select session to MOVE:" "${session_display[@]}")
    fi

    if [ -z "$selected_session" ]; then
        echo "${RED}No session selected. Exiting.${NC}"
        exit 1
    fi

    session_id="${session_ids[$selected_session]}"

    echo "${GREEN}Selected session:${NC} $selected_session"
    echo "${GREEN}Session ID:${NC} $session_id"
    echo ""

    # Step 5: Select destination project
    # Filter out source project from destinations
    typeset -a dest_display
    for item in "${project_display[@]}"; do
        if [ "$item" != "$selected_source" ]; then
            dest_display+=("$item")
        fi
    done

    # Add option to enter custom path
    dest_display+=("[Enter custom path]")

    if $use_fzf; then
        echo "${CYAN}Select DESTINATION project (use arrows/type to filter):${NC}"
        selected_dest=$(printf '%s\n' "${dest_display[@]}" | fzf --height=15 --reverse --prompt="Destination > ")
    else
        selected_dest=$(select_from_menu "Select DESTINATION project:" "${dest_display[@]}")
    fi

    if [ -z "$selected_dest" ]; then
        echo "${RED}No destination selected. Exiting.${NC}"
        exit 1
    fi

    if [ "$selected_dest" = "[Enter custom path]" ]; then
        echo ""
        read "dest_path?Enter destination project path: "
        if [ -z "$dest_path" ]; then
            echo "${RED}No path entered. Exiting.${NC}"
            exit 1
        fi
    else
        dest_path="${project_paths[$selected_dest]}"
    fi

    echo "${GREEN}Selected destination:${NC} $dest_path"
    echo ""

    # Step 6: Confirm and execute
    echo "${YELLOW}=== Migration Summary ===${NC}"
    echo "  Session: ${CYAN}$selected_session${NC}"
    echo "  From:    ${CYAN}$source_path${NC}"
    echo "  To:      ${CYAN}$dest_path${NC}"
    echo ""

    read "confirm?Proceed with migration? [y/N] "

    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "${YELLOW}Migration cancelled.${NC}"
        exit 0
    fi

    echo ""
    echo "${BLUE}Executing migration...${NC}"
    echo ""

    python3 "$MOVE_SCRIPT" "$session_id" --from "$source_path" --to "$dest_path" --verbose

    echo ""
    echo "${GREEN}Done! You can now access this chat from: $dest_path${NC}"
}

main "$@"
