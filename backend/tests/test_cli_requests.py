from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def test_cli_search_uses_canonical_knowledge_endpoint():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"results": []}

    with patch("cli.commands.search.httpx.get", return_value=response) as get:
        runner.invoke(app, ["search", "deployment", "--api-key", "ask_test"])

    get.assert_called_once()
    assert get.call_args.args[0].endswith("/api/v1/knowledge/retrieval/search")


def test_cli_status_uses_health_endpoint_by_default():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"status": "ok", "checks": {}}

    with patch("cli.commands.doctor.httpx.get", return_value=response) as get:
        runner.invoke(app, ["doctor"])

    get.assert_called_once()
    assert get.call_args.args[0].endswith("/api/v1/health/ready")
