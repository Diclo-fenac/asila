from typer.testing import CliRunner

from cli.commands.ingest import collect_ingest_files
from cli.main import app

runner = CliRunner()


def test_cli_exposes_day_one_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "search" in result.stdout
    assert "ingest" in result.stdout
    assert "doctor" in result.stdout
    assert "org" in result.stdout
    assert "key" in result.stdout
    assert "documents" in result.stdout
    assert "jobs" in result.stdout
    assert "audit" in result.stdout


def test_cli_exposes_operator_subcommands():
    for sub, cmd in [
        ("org", "create"),
        ("key", "create"),
        ("key", "rotate"),
        ("key", "list"),
        ("key", "revoke"),
        ("documents", "list"),
        ("documents", "delete"),
        ("jobs", "get"),
        ("audit", "list"),
        ("audit", "verify"),
    ]:
        res = runner.invoke(app, [sub, "--help"])
        assert res.exit_code == 0
        assert cmd in res.stdout


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
