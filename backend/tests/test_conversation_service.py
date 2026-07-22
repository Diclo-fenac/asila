from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.app.conversations.models import MessageRole
from services.conversations.service import append_message, create_conversation


@pytest.mark.asyncio
async def test_create_conversation_is_organization_scoped():
    session = MagicMock()
    session.flush = AsyncMock()

    conversation = await create_conversation(
        session,
        organization_id="org_1",
        title="Deployment questions",
        created_by_user_id="usr_1",
    )

    assert conversation.organization_id == "org_1"
    assert conversation.title == "Deployment questions"
    session.add.assert_called_once_with(conversation)


@pytest.mark.asyncio
async def test_append_message_rejects_unknown_conversation():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    with pytest.raises(ValueError, match="Conversation not found"):
        await append_message(
            session,
            organization_id="org_1",
            conversation_id="conv_missing",
            role=MessageRole.USER,
            content="Where is the runbook?",
        )


@pytest.mark.asyncio
async def test_append_message_persists_citations_and_role():
    conversation = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = conversation
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()

    message = await append_message(
        session,
        organization_id="org_1",
        conversation_id="conv_1",
        role=MessageRole.ASSISTANT,
        content="Restart the worker.",
        citations=[{"source_uri": "file:///runbook.md"}],
        provider="OllamaGenerationProvider",
        model="llama3.2",
    )

    assert message.organization_id == "org_1"
    assert message.role is MessageRole.ASSISTANT
    assert message.citations == [{"source_uri": "file:///runbook.md"}]
    assert message.model == "llama3.2"


@pytest.mark.asyncio
async def test_answer_question_stores_cited_assistant_response():
    from services.conversations.service import answer_question
    from services.retrieval.service import SearchResult

    conversation = MagicMock()
    conversation_result = MagicMock()
    conversation_result.scalar_one_or_none.return_value = conversation
    session = MagicMock()
    session.execute = AsyncMock(return_value=conversation_result)
    session.flush = AsyncMock()

    provider = MagicMock(model="local-model")
    provider.generate = AsyncMock(return_value="Use the restart runbook.")
    result = SearchResult(
        chunk_id="chk_1",
        document_id="doc_1",
        title="Runbook",
        source_uri="file:///runbook.md",
        content="Restart the worker.",
        page_number=None,
        score=0.9,
    )

    with patch(
        "services.conversations.service.keyword_search",
        new=AsyncMock(return_value=[result]),
    ):
        user_message, assistant_message, citations = await answer_question(
            session,
            organization_id="org_1",
            conversation_id="conv_1",
            question="How do I restart it?",
            generation_provider=provider,
        )

    assert user_message.role is MessageRole.USER
    assert assistant_message.role is MessageRole.ASSISTANT
    assert assistant_message.citations[0]["document_id"] == "doc_1"
    assert citations[0]["source_uri"] == "file:///runbook.md"
    provider.generate.assert_awaited_once()
