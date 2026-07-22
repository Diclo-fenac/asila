from sqlalchemy import inspect

from domain.app.conversations.models import Conversation, Message


def test_conversation_and_message_are_organization_scoped():
    for model in (Conversation, Message):
        table = inspect(model).local_table
        assert table.schema == "app"
        assert table.c.organization_id.nullable is False
    assert "citations" in inspect(Message).local_table.c

