from unittest.mock import MagicMock, patch

from cli.main import build_parser, run_search, run_status


def test_cli_search_uses_canonical_knowledge_endpoint():
    args = build_parser().parse_args(["search", "deployment", "--api-key", "ask_test"])
    response = MagicMock()
    response.json.return_value = {"results": []}

    with patch("cli.main.httpx.get", return_value=response) as get:
        run_search(args)

    get.assert_called_once()
    assert get.call_args.args[0].endswith("/api/v1/knowledge/retrieval/search")


def test_cli_status_uses_health_endpoint_by_default():
    args = build_parser().parse_args(["status"])
    response = MagicMock()
    response.json.return_value = {"status": "ok"}

    with patch("cli.main.httpx.get", return_value=response) as get:
        run_status(args)

    assert get.call_args.args[0].endswith("/api/v1/health")
