from io import BytesIO

import pytest

from infra.storage.local import LocalStorage


def test_local_storage_rejects_path_traversal(tmp_path):
    storage = LocalStorage(str(tmp_path))

    with pytest.raises(ValueError):
        storage.save_file("org_1", "../secret.txt", BytesIO(b"secret"))


def test_local_storage_rejects_retrieval_path_traversal(tmp_path):
    storage = LocalStorage(str(tmp_path))

    with pytest.raises(ValueError):
        storage.get_file_path("../../secret.txt")
