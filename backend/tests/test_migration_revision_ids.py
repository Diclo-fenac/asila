import re
from pathlib import Path


VERSIONS_DIRECTORIES = (
    Path(__file__).parents[1] / "migrations/platform/versions",
    Path(__file__).parents[1] / "migrations/app/versions",
)


def test_alembic_revision_ids_fit_the_default_version_column():
    for versions_directory in VERSIONS_DIRECTORIES:
        for migration in versions_directory.glob("*.py"):
            source = migration.read_text()
            match = re.search(r'^revision: str = "([^"]+)"$', source, re.MULTILINE)
            assert match, f"Missing revision identifier: {migration}"
            assert len(match.group(1)) <= 32, migration
