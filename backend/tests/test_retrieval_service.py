from services.retrieval.service import (
    normalize_search_limit,
    reciprocal_rank_fusion,
    validate_query,
)


def test_retrieval_query_is_normalized():
    assert validate_query("  deploy   the   worker ") == "deploy the worker"


def test_retrieval_limit_is_bounded():
    assert normalize_search_limit(None) == 10
    assert normalize_search_limit(0) == 1
    assert normalize_search_limit(1000) == 50


def test_reciprocal_rank_fusion_prefers_results_seen_by_both_retrievers():
    lexical = [{"chunk_id": "shared"}, {"chunk_id": "lexical-only"}]
    semantic = [{"chunk_id": "shared"}, {"chunk_id": "semantic-only"}]

    fused = reciprocal_rank_fusion([lexical, semantic])

    assert fused[0]["chunk_id"] == "shared"
