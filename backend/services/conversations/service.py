from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.app.conversations.models import Conversation, Message, MessageRole
from domain.ports.ai import EmbeddingProvider, GenerationProvider
from services.retrieval.service import SearchResult, hybrid_search, keyword_search


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} is required")
    return normalized


async def create_conversation(
    session: AsyncSession,
    *,
    organization_id: str,
    title: str = "New conversation",
    created_by_user_id: str | None = None,
) -> Conversation:
    conversation = Conversation(
        id=f"conv_{uuid4().hex}",
        organization_id=organization_id,
        title=_required_text(title, "Conversation title"),
        created_by_user_id=created_by_user_id,
    )
    session.add(conversation)
    await session.flush()
    return conversation


async def get_conversation(
    session: AsyncSession, *, organization_id: str, conversation_id: str
) -> Conversation | None:
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def list_conversations(
    session: AsyncSession, *, organization_id: str, limit: int = 50
) -> list[Conversation]:
    result = await session.execute(
        select(Conversation)
        .where(Conversation.organization_id == organization_id)
        .order_by(Conversation.updated_at.desc())
        .limit(min(max(limit, 1), 200))
    )
    return list(result.scalars().all())


async def list_messages(
    session: AsyncSession, *, organization_id: str, conversation_id: str, limit: int = 200
) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(
            Message.organization_id == organization_id,
            Message.conversation_id == conversation_id,
        )
        .order_by(Message.created_at.asc())
        .limit(min(max(limit, 1), 500))
    )
    return list(result.scalars().all())


async def append_message(
    session: AsyncSession,
    *,
    organization_id: str,
    conversation_id: str,
    role: MessageRole,
    content: str,
    citations: Sequence[dict] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> Message:
    conversation = await get_conversation(
        session,
        organization_id=organization_id,
        conversation_id=conversation_id,
    )
    if conversation is None:
        raise ValueError("Conversation not found")

    message = Message(
        id=f"msg_{uuid4().hex}",
        organization_id=organization_id,
        conversation_id=conversation_id,
        role=role,
        content=_required_text(content, "Message content"),
        citations=list(citations or []),
        provider=provider,
        model=model,
        token_count=max(1, len(content.split())),
    )
    session.add(message)
    await session.flush()
    return message


def citations_for_results(results: Sequence[SearchResult]) -> list[dict]:
    return [
        {
            "chunk_id": result.chunk_id,
            "document_id": result.document_id,
            "title": result.title,
            "source_uri": result.source_uri,
            "page_number": result.page_number,
            "score": result.score,
        }
        for result in results
    ]


async def answer_question(
    session: AsyncSession,
    *,
    organization_id: str,
    conversation_id: str,
    question: str,
    generation_provider: GenerationProvider,
    embedding_provider: EmbeddingProvider | None = None,
    mode: str = "keyword",
) -> tuple[Message, Message, list[dict]]:
    question = _required_text(question, "Question")
    user_message = await append_message(
        session,
        organization_id=organization_id,
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=question,
    )

    if mode == "hybrid":
        if embedding_provider is None:
            raise ValueError("Hybrid mode requires an embedding provider")
        results = await hybrid_search(
            session,
            question,
            provider=embedding_provider,
            limit=10,
        )
    else:
        results = await keyword_search(session, question, limit=10)

    citations = citations_for_results(results)
    context = "\n\n".join(
        f"[{index}] {result.title} ({result.source_uri})\n{result.content}"
        for index, result in enumerate(results, start=1)
    )
    if not context:
        context = "No relevant source passages were found."
    answer = await generation_provider.generate(question, context)
    assistant_message = await append_message(
        session,
        organization_id=organization_id,
        conversation_id=conversation_id,
        role=MessageRole.ASSISTANT,
        content=answer,
        citations=citations,
        provider=generation_provider.__class__.__name__,
        model=getattr(generation_provider, "model", None),
    )
    return user_message, assistant_message, citations
