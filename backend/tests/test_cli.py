from cli.main import build_parser, collect_ingest_files


def test_cli_exposes_day_one_commands():
    parser = build_parser()

    assert parser.parse_args(["init", "--owner-email", "a@example.com"]).command == "init"
    assert parser.parse_args(["search", "how do I deploy?"]).command == "search"
    assert parser.parse_args(["ingest", "."]).command == "ingest"
    assert parser.parse_args(["status"]).command == "status"


def test_cli_file_collection_skips_hidden_and_runtime_directories(tmp_path):
    (tmp_path / "README.md").write_text("hello")
    (tmp_path / ".env").write_text("secret")
    runtime = tmp_path / ".venv"
    runtime.mkdir()
    (runtime / "ignored.txt").write_text("ignored")

    files = collect_ingest_files(tmp_path)

    assert files == [tmp_path / "README.md"]


def test_cli_file_collection_rejects_symlinks_outside_the_requested_directory(tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret")
    (tmp_path / "linked-secret.txt").symlink_to(outside)

    assert collect_ingest_files(tmp_path) == []
