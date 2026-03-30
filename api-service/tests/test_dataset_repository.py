"""
Tests for Dataset Repository
Database operations for dataset management with mocked AsyncSession
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.models.dataset import Dataset, DatasetVersion, DatasetColumn, DatasetStatus, DatasetSource
from app.repositories.dataset import DatasetRepository


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def repo():
    return DatasetRepository(Dataset)


# ==================== create ====================


class TestDatasetRepoCreate:

    @pytest.mark.asyncio
    async def test_create_basic(self, repo, mock_db):
        data = {"name": "Temperature Data", "source": DatasetSource.GENERATED}
        result = await repo.create(mock_db, obj_in_data=data)
        assert result is not None
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_normalizes_string_source(self, repo, mock_db):
        data = {"name": "Test", "source": "generated"}
        await repo.create(mock_db, obj_in_data=data)
        assert data["source"] == DatasetSource.GENERATED

    @pytest.mark.asyncio
    async def test_create_with_columns(self, repo, mock_db):
        data = {
            "name": "With Cols",
            "source": DatasetSource.UPLOAD,
            "columns": [{"name": "temp", "data_type": "float"}],
        }
        await repo.create(mock_db, obj_in_data=data)
        # add called for dataset + column
        assert mock_db.add.call_count >= 2

    @pytest.mark.asyncio
    async def test_create_no_commit(self, repo, mock_db):
        data = {"name": "Test", "source": DatasetSource.GENERATED}
        await repo.create(mock_db, obj_in_data=data, commit=False)
        mock_db.flush.assert_called_once()


# ==================== update ====================


class TestDatasetRepoUpdate:

    @pytest.mark.asyncio
    async def test_update_fields(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        ds.id = uuid4()
        ds.name = "Old"
        result = await repo.update(mock_db, db_obj=ds, obj_in_data={"name": "New"})
        assert result is ds
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_normalizes_string_source(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        ds.id = uuid4()
        data = {"source": "upload"}
        await repo.update(mock_db, db_obj=ds, obj_in_data=data)
        assert data["source"] == DatasetSource.UPLOAD

    @pytest.mark.asyncio
    async def test_update_no_commit(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        ds.id = uuid4()
        await repo.update(mock_db, db_obj=ds, obj_in_data={"name": "X"}, commit=False)
        mock_db.flush.assert_called_once()


# ==================== get_by_id / get_by_name ====================


class TestDatasetRepoLookup:

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = ds
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_id(mock_db, uuid4())
        assert result is ds

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_id(mock_db, uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_include_deleted(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        await repo.get_by_id(mock_db, uuid4(), include_deleted=True)

    @pytest.mark.asyncio
    async def test_get_by_id_no_columns(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        await repo.get_by_id(mock_db, uuid4(), include_columns=False)

    @pytest.mark.asyncio
    async def test_get_by_name_found(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = ds
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_name(mock_db, "Temperature Data")
        assert result is ds

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_by_name(mock_db, "missing")
        assert result is None


# ==================== filter_datasets ====================


class TestFilterDatasets:

    @pytest.mark.asyncio
    async def test_filter_empty(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        datasets, total = await repo.filter_datasets(mock_db, filters={})
        assert total == 0
        assert datasets == []

    @pytest.mark.asyncio
    async def test_filter_with_search(self, repo, mock_db):
        mock_count = MagicMock()
        mock_count.scalar.return_value = 1
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = [MagicMock()]
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        datasets, total = await repo.filter_datasets(
            mock_db, filters={"search": "temp"}, sort_order="asc"
        )
        assert total == 1

    @pytest.mark.asyncio
    async def test_filter_with_all_filters(self, repo, mock_db):
        from datetime import datetime
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_data = MagicMock()
        mock_data.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_count, mock_data])
        await repo.filter_datasets(
            mock_db,
            filters={
                "source": "generated",
                "status": "ready",
                "file_format": "csv",
                "tags": ["iot"],
                "min_rows": 10,
                "max_rows": 1000,
                "created_after": datetime(2024, 1, 1),
                "created_before": datetime(2025, 1, 1),
            },
        )


# ==================== delete ====================


class TestDatasetRepoDelete:

    @pytest.mark.asyncio
    async def test_soft_delete(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        ds.is_deleted = False
        repo.get_by_id = AsyncMock(return_value=ds)
        result = await repo.delete(mock_db, uuid4(), soft_delete=True)
        assert ds.is_deleted is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_hard_delete(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        repo.get_by_id = AsyncMock(return_value=ds)
        result = await repo.delete(mock_db, uuid4(), soft_delete=False)
        mock_db.delete.assert_called_once_with(ds)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo, mock_db):
        repo.get_by_id = AsyncMock(return_value=None)
        result = await repo.delete(mock_db, uuid4())
        assert result is None


# ==================== update_status / update_metrics ====================


class TestDatasetRepoStatusMetrics:

    @pytest.mark.asyncio
    async def test_update_status(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        repo.get_by_id = AsyncMock(return_value=ds)
        result = await repo.update_status(
            mock_db, uuid4(), DatasetStatus.READY,
            validation_status="valid", validation_errors=[]
        )
        assert result is ds
        assert ds.status == DatasetStatus.READY

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, repo, mock_db):
        repo.get_by_id = AsyncMock(return_value=None)
        result = await repo.update_status(mock_db, uuid4(), DatasetStatus.READY)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status_no_commit(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        repo.get_by_id = AsyncMock(return_value=ds)
        await repo.update_status(mock_db, uuid4(), DatasetStatus.READY, commit=False)
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_metrics(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        repo.get_by_id = AsyncMock(return_value=ds)
        result = await repo.update_metrics(
            mock_db, uuid4(), row_count=100, column_count=5,
            file_size=2048, completeness_score=0.95
        )
        assert result is ds
        assert ds.row_count == 100
        assert ds.column_count == 5

    @pytest.mark.asyncio
    async def test_update_metrics_not_found(self, repo, mock_db):
        repo.get_by_id = AsyncMock(return_value=None)
        result = await repo.update_metrics(mock_db, uuid4(), row_count=0, column_count=0)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_metrics_no_commit(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        repo.get_by_id = AsyncMock(return_value=ds)
        await repo.update_metrics(mock_db, uuid4(), row_count=10, column_count=2, commit=False)
        mock_db.flush.assert_called_once()


# ==================== Column Operations ====================


class TestDatasetRepoColumns:

    @pytest.mark.asyncio
    async def test_add_columns(self, repo, mock_db):
        cols = [{"name": "temp", "data_type": "float"}, {"name": "ts", "data_type": "datetime"}]
        result = await repo.add_columns(mock_db, uuid4(), cols)
        assert len(result) == 2
        assert mock_db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_add_columns_no_commit(self, repo, mock_db):
        cols = [{"name": "val", "data_type": "int"}]
        await repo.add_columns(mock_db, uuid4(), cols, commit=False)
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_column_statistics(self, repo, mock_db):
        col = MagicMock(spec=DatasetColumn)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = col
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.update_column_statistics(
            mock_db, uuid4(), {"min_value": 0, "max_value": 100}
        )
        assert result is col

    @pytest.mark.asyncio
    async def test_update_column_statistics_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.update_column_statistics(mock_db, uuid4(), {})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_columns(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.delete_columns(mock_db, uuid4())
        assert result == 5

    @pytest.mark.asyncio
    async def test_delete_columns_no_commit(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_db.execute = AsyncMock(return_value=mock_result)
        await repo.delete_columns(mock_db, uuid4(), commit=False)
        mock_db.commit.assert_not_called()


# ==================== Version Operations ====================


class TestDatasetRepoVersions:

    @pytest.mark.asyncio
    async def test_create_version(self, repo, mock_db):
        ds = MagicMock(spec=Dataset)
        ds.file_path = "/data/test.csv"
        ds.file_size = 1024
        ds.row_count = 100
        ds.column_count = 5
        ds.schema_definition = {"cols": []}
        repo.get_by_id = AsyncMock(return_value=ds)
        mock_version_result = MagicMock()
        mock_version_result.scalar.return_value = 2
        mock_db.execute = AsyncMock(return_value=mock_version_result)
        result = await repo.create_version(mock_db, uuid4(), change_description="Updated")
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_version_not_found(self, repo, mock_db):
        repo.get_by_id = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            await repo.create_version(mock_db, uuid4())

    @pytest.mark.asyncio
    async def test_get_versions(self, repo, mock_db):
        v1, v2 = MagicMock(), MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [v2, v1]
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_versions(mock_db, uuid4())
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_versions_include_deleted(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        await repo.get_versions(mock_db, uuid4(), include_deleted=True)

    @pytest.mark.asyncio
    async def test_get_latest_version(self, repo, mock_db):
        v = MagicMock(spec=DatasetVersion)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = v
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_latest_version(mock_db, uuid4())
        assert result is v

    @pytest.mark.asyncio
    async def test_get_latest_version_none(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_latest_version(mock_db, uuid4())
        assert result is None


# ==================== Bulk Operations ====================


class TestDatasetRepoBulk:

    @pytest.mark.asyncio
    async def test_bulk_delete_empty(self, repo, mock_db):
        result = await repo.bulk_delete(mock_db, dataset_ids=[])
        assert result == 0

    @pytest.mark.asyncio
    async def test_bulk_soft_delete(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.bulk_delete(mock_db, dataset_ids=[uuid4(), uuid4(), uuid4()])
        assert result == 3

    @pytest.mark.asyncio
    async def test_bulk_hard_delete(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.bulk_delete(mock_db, dataset_ids=[uuid4(), uuid4()], soft_delete=False)
        assert result == 2
