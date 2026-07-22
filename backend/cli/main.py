import argparse
import json
import mimetypes
import os
import subprocess
from pathlib import Path

import httpx


def _is_within_directory(candidate: Path, directory: Path) -> bool:
    try:
        candidate.relative_to(directory)
    except ValueError:
        return False
    return True


def collect_ingest_files(path: Path) -> list[Path]:
    path = path.resolve()
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise SystemExit(f"Path does not exist: {path}")

    git_dir = path / ".git"
    if git_dir.exists():
        result = subprocess.run(
            ["git", "-C", str(path), "ls-files", "--cached", "--others", "--exclude-standard"],
            check=True,
            capture_output=True,
            text=True,
        )
        files = []
        for relative in result.stdout.splitlines():
            candidate = path / relative
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if _is_within_directory(resolved, path):
                files.append(resolved)
        return sorted(files)

    ignored_directory_names = {".git", ".venv", "__pycache__", "node_modules"}
    files = []
    for candidate in path.rglob("*"):
        if not candidate.is_file():
            continue
        relative_parts = candidate.relative_to(path).parts
        if any(part.startswith(".") or part in ignored_directory_names for part in relative_parts):
            continue
        resolved = candidate.resolve()
        if _is_within_directory(resolved, path):
            files.append(resolved)
    return sorted(files)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asila", description="Asila knowledge platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Initialize a local Asila deployment")
    init.add_argument("--url", default=os.getenv("ASILA_URL", "http://localhost:8000"))
    init.add_argument("--setup-token", default=os.getenv("ASILA_SETUP_TOKEN"))
    init.add_argument("--owner-email", required=True)
    init.add_argument("--owner-name", default="Asila Owner")
    init.add_argument("--organization-name", default="My Asila Organization")
    init.add_argument("--organization-slug", default="my-asila-organization")

    ingest = subparsers.add_parser("ingest", help="Ingest a file or directory")
    ingest.add_argument("path", type=Path)
    ingest.add_argument("--url", default=os.getenv("ASILA_URL", "http://localhost:8000"))
    ingest.add_argument("--api-key", default=os.getenv("ASILA_API_KEY"))

    search = subparsers.add_parser("search", help="Search indexed knowledge")
    search.add_argument("query")
    search.add_argument("--url", default=os.getenv("ASILA_URL", "http://localhost:8000"))
    search.add_argument("--api-key", default=os.getenv("ASILA_API_KEY"))
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--mode", choices=["keyword", "hybrid"], default="keyword")

    status = subparsers.add_parser("status", help="Check Asila and ingestion status")
    status.add_argument("--url", default=os.getenv("ASILA_URL", "http://localhost:8000"))
    status.add_argument("--api-key", default=os.getenv("ASILA_API_KEY"))
    status.add_argument("--job-id")

    return parser


def run_init(args: argparse.Namespace) -> int:
    if not args.setup_token:
        raise SystemExit("ASILA_SETUP_TOKEN or --setup-token is required")
    response = httpx.post(
        f"{args.url.rstrip('/')}/api/v1/setup",
        headers={"X-Asila-Setup-Token": args.setup_token},
        json={
            "owner_email": args.owner_email,
            "owner_name": args.owner_name,
            "organization_name": args.organization_name,
            "organization_slug": args.organization_slug,
        },
        timeout=30,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))
    return 0


def run_search(args: argparse.Namespace) -> int:
    if not args.api_key:
        raise SystemExit("ASILA_API_KEY or --api-key is required")
    response = httpx.get(
        f"{args.url.rstrip('/')}/api/v1/knowledge/retrieval/search",
        headers={"X-Asila-API-Key": args.api_key},
        params={"query": args.query, "limit": args.limit, "mode": args.mode},
        timeout=30,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))
    return 0


def run_ingest(args: argparse.Namespace) -> int:
    if not args.api_key:
        raise SystemExit("ASILA_API_KEY or --api-key is required")
    files = collect_ingest_files(args.path)
    if not files:
        raise SystemExit("No ingestible files found")

    root = args.path.resolve() if args.path.is_dir() else args.path.resolve().parent
    uploaded = []
    with httpx.Client(timeout=60) as client:
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            relative_name = str(file_path.relative_to(root))
            response = client.post(
                f"{args.url.rstrip('/')}/api/v1/knowledge/documents",
                headers={"X-Asila-API-Key": args.api_key},
                json={
                    "title": relative_name,
                    "source_uri": f"file://{file_path}",
                    "content": content,
                    "mime_type": mimetypes.guess_type(file_path.name)[0],
                    "metadata": {"path": relative_name},
                },
            )
            response.raise_for_status()
            uploaded.append(response.json())
    print(json.dumps({"uploaded": len(uploaded), "documents": uploaded}, indent=2))
    return 0


def run_status(args: argparse.Namespace) -> int:
    headers = {"X-Asila-API-Key": args.api_key} if args.api_key else {}
    path = f"/api/v1/knowledge/jobs/{args.job_id}" if args.job_id else "/api/v1/health"
    response = httpx.get(f"{args.url.rstrip('/')}{path}", headers=headers, timeout=15)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        return run_init(args)
    if args.command == "search":
        return run_search(args)
    if args.command == "ingest":
        return run_ingest(args)
    if args.command == "status":
        return run_status(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
