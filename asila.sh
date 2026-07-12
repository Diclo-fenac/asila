#!/bin/bash
# Asila CLI Ingestion Wrapper

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INGEST_SCRIPT="$DIR/backend/scripts/ingest.py"

if [ -z "$ASILA_API_KEY" ]; then
    echo -e "\033[0;31mError: ASILA_API_KEY environment variable is required.\033[0m"
    exit 1
fi

if [ "$1" == "ingest" ]; then
    # Ensure backend venv is ready
    if [ ! -d "$DIR/backend/.venv" ]; then
        echo "Initializing backend environment..."
        cd "$DIR/backend" && uv sync
    fi

    cd "$DIR"
    # Use git ls-files if inside a git repo
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "Using git ls-files to respect .gitignore..."
        files=$(git ls-files --cached --others --exclude-standard)
    else
        echo "Not a git repository. Finding all files in current directory..."
        files=$(find . -type f -not -path '*/\.*')
    fi
    
    # Run the ingestion script
    cd "$DIR/backend"
    
    # We pass the absolute paths so the script can find them
    abs_files=""
    for file in $files; do
        if [ -f "$DIR/$file" ]; then
            abs_files="$abs_files $DIR/$file"
        fi
    done
    
    uv run python scripts/ingest.py $abs_files
else
    echo "Usage: ./asila.sh ingest"
    exit 1
fi
