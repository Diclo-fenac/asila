import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from services.generation.service import _log_unanswered
from domain.tenant.users.models import User

@pytest.mark.asyncio
async def test_log_unanswered_with_valid_user():
    # Mock database session
    db = AsyncMock(spec=AsyncSession)
    
    # Mock result showing user exists
    mock_result = MagicMock()
    mock_user = User(id="test@example.com")
    mock_result.scalar_one_or_none.return_value = mock_user
    db.execute.return_value = mock_result
    
    # Call _log_unanswered
    await _log_unanswered(db, "hello", "test@example.com")
    
    # Verify we queried the User table
    assert db.execute.called
    
    # Verify UnansweredQuery was added with correct user_id
    assert db.add.called
    added_uq = db.add.call_args[0][0]
    assert added_uq.user_id == "test@example.com"
    assert added_uq.question == "hello"
    assert db.commit.called

@pytest.mark.asyncio
async def test_log_unanswered_with_invalid_user():
    # Mock database session
    db = AsyncMock(spec=AsyncSession)
    
    # Mock result showing user does not exist (None)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    
    # Call _log_unanswered with non-existent user
    await _log_unanswered(db, "hello", "nonexistent@example.com")
    
    # Verify we queried the User table
    assert db.execute.called
    
    # Verify UnansweredQuery was added with user_id = None
    assert db.add.called
    added_uq = db.add.call_args[0][0]
    assert added_uq.user_id is None
    assert added_uq.question == "hello"
    assert db.commit.called

@pytest.mark.asyncio
async def test_log_unanswered_no_user():
    # Mock database session
    db = AsyncMock(spec=AsyncSession)
    
    # Call _log_unanswered with no user_id
    await _log_unanswered(db, "hello", None)
    
    # Verify we did not execute query on users table
    assert not db.execute.called
    
    # Verify UnansweredQuery was added with user_id = None
    assert db.add.called
    added_uq = db.add.call_args[0][0]
    assert added_uq.user_id is None
    assert added_uq.question == "hello"
    assert db.commit.called
