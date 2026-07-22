#!/bin/bash
# Asila CLI Ingestion Wrapper

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ "$1" != "init" ] && [ "$1" != "status" ] && [ -z "$ASILA_API_KEY" ]; then
    echo -e "\033[0;31mError: ASILA_API_KEY environment variable is required.\033[0m"
    exit 1
fi

if [ "$1" == "init" ]; then
    shift
    cd "$DIR/backend"
    uv run python -m cli.main init "$@"
elif [ "$1" == "search" ]; then
    shift
    cd "$DIR/backend"
    uv run python -m cli.main search "$@"
elif [ "$1" == "ingest" ]; then
    shift
    cd "$DIR/backend"
    if [ "$#" -eq 0 ]; then
        set -- .
    fi
    uv run python -m cli.main ingest "$@"
elif [ "$1" == "status" ]; then
    shift
    cd "$DIR/backend"
    uv run python -m cli.main status "$@"
else
    echo "Usage: ./asila.sh {init|search|ingest|status}"
    exit 1
fi
