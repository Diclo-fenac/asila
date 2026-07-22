from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from core.database.base import AppBase, PlatformBase
from domain.app.chunks.models import Chunk
from domain.app.documents.models import Document
from domain.app.embeddings.models import Embedding
from domain.app.ingestion_jobs.models import IngestionJob
from domain.app.repositories.models import Repository
from domain.platform.api_keys.models import ApiKey
from domain.platform.memberships.models import Membership
from domain.platform.organizations.models import Organization
from domain.platform.service_accounts.models import ServiceAccount
from domain.platform.users.models import User


def test_platform_models_have_platform_schema():
    assert set(PlatformBase.metadata.tables) >= {
        "platform.users",
        "platform.organizations",
        "platform.memberships",
        "platform.service_accounts",
        "platform.api_keys",
    }


def test_application_models_have_organization_scope():
    for model in (Repository, Document, Chunk, Embedding, IngestionJob):
        table = inspect(model).local_table
        assert table.schema == "app"
        assert "organization_id" in table.c
        assert table.c.organization_id.nullable is False


def test_organization_creator_and_api_key_constraints_are_modelled():
    organization_table = inspect(Organization).local_table
    membership_table = inspect(Membership).local_table
    api_key_table = inspect(ApiKey).local_table
    service_account_table = inspect(ServiceAccount).local_table

    assert "created_by_user_id" in organization_table.c
    assert "role" in membership_table.c
    assert "expires_at" in api_key_table.c
    assert "revoked_at" in api_key_table.c
    assert "organization_id" in service_account_table.c


def test_application_metadata_compiles_as_postgresql_ddl():
    for table in AppBase.metadata.sorted_tables:
        CreateTable(table).compile(dialect=postgresql.dialect())


def test_platform_metadata_compiles_as_postgresql_ddl():
    for table in PlatformBase.metadata.sorted_tables:
        CreateTable(table).compile(dialect=postgresql.dialect())
