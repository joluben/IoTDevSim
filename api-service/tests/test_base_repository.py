"""
Tests for Base CRUD Repository
Generic repository operations with mocked AsyncSession and model
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from pydantic import BaseModel

from app.models.connection import Connection
from app.repositories.base import CRUDBase


class FakeCreateSchema(BaseModel):
    name: str
    description: str = ""


class FakeUpdateSchema(BaseModel):
    name: str = None
    description: str = None


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def repo():
    return CRUDBase(Connection)


# ==================== get ====================


class TestBaseGet:

    @pytest.mark.asyncio
    async def test_get_found(self, repo, mock_db):
        obj = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = obj
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get(mock_db, uuid4())
        assert result is obj

    @pytest.mark.asyncio
    async def test_get_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get(mock_db, uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_include_deleted(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get(mock_db, uuid4(), include_deleted=True)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_raises_on_error(self, repo, mock_db):
        mock_db.execute = AsyncMock(side_effect=Exception("db error"))
        with pytest.raises(Exception, match="db error"):
            await repo.get(mock_db, uuid4())


# ==================== get_multi ====================


class TestBaseGetMulti:

    @pytest.mark.asyncio
    async def test_get_multi_default(self, repo, mock_db):
        obj1, obj2 = MagicMock(), MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [obj1, obj2]
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_multi(mock_db)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_multi_with_pagination(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_multi(mock_db, skip=10, limit=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_multi_with_filters(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_multi(
            mock_db, filters={"is_active": True}
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_get_multi_with_list_filter(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_multi(
            mock_db, filters={"protocol": ["mqtt", "http"]}
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_get_multi_with_like_filter(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_multi(
            mock_db, filters={"name": {"like": "sensor"}}
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_get_multi_order_by_asc(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_multi(mock_db, order_by="name")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_multi_order_by_desc(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_multi(mock_db, order_by="-name")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_multi_include_deleted(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.get_multi(mock_db, include_deleted=True)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_multi_raises_on_error(self, repo, mock_db):
        mock_db.execute = AsyncMock(side_effect=Exception("db error"))
        with pytest.raises(Exception, match="db error"):
            await repo.get_multi(mock_db)


# ==================== count ====================


class TestBaseCount:

    @pytest.mark.asyncio
    async def test_count_default(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.count(mock_db)
        assert result == 42

    @pytest.mark.asyncio
    async def test_count_with_filters(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.count(mock_db, filters={"is_active": True})
        assert result == 5

    @pytest.mark.asyncio
    async def test_count_with_list_filter(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.count(mock_db, filters={"protocol": ["mqtt"]})
        assert result == 3

    @pytest.mark.asyncio
    async def test_count_with_like_filter(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.count(mock_db, filters={"name": {"like": "test"}})
        assert result == 1

    @pytest.mark.asyncio
    async def test_count_include_deleted(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 50
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.count(mock_db, include_deleted=True)
        assert result == 50

    @pytest.mark.asyncio
    async def test_count_raises_on_error(self, repo, mock_db):
        mock_db.execute = AsyncMock(side_effect=Exception("db error"))
        with pytest.raises(Exception, match="db error"):
            await repo.count(mock_db)


# ==================== create ====================


class TestBaseCreate:

    @pytest.mark.asyncio
    async def test_create_with_commit(self, repo, mock_db):
        schema = FakeCreateSchema(name="Test", description="desc")
        result = await repo.create(mock_db, obj_in=schema)
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_no_commit(self, repo, mock_db):
        schema = FakeCreateSchema(name="Test")
        await repo.create(mock_db, obj_in=schema, commit=False)
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_rollback_on_error(self, repo, mock_db):
        mock_db.commit = AsyncMock(side_effect=Exception("commit fail"))
        schema = FakeCreateSchema(name="Test")
        with pytest.raises(Exception, match="commit fail"):
            await repo.create(mock_db, obj_in=schema)
        mock_db.rollback.assert_called_once()


# ==================== update ====================


class TestBaseUpdate:

    @pytest.mark.asyncio
    async def test_update_with_dict(self, repo, mock_db):
        db_obj = MagicMock()
        db_obj.id = uuid4()
        result = await repo.update(mock_db, db_obj=db_obj, obj_in={"name": "Updated"})
        assert result is db_obj
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_with_schema(self, repo, mock_db):
        db_obj = MagicMock()
        db_obj.id = uuid4()
        schema = FakeUpdateSchema(name="Updated")
        result = await repo.update(mock_db, db_obj=db_obj, obj_in=schema)
        assert result is db_obj

    @pytest.mark.asyncio
    async def test_update_no_commit(self, repo, mock_db):
        db_obj = MagicMock()
        db_obj.id = uuid4()
        await repo.update(mock_db, db_obj=db_obj, obj_in={"name": "X"}, commit=False)
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_rollback_on_error(self, repo, mock_db):
        mock_db.commit = AsyncMock(side_effect=Exception("commit fail"))
        db_obj = MagicMock()
        db_obj.id = uuid4()
        with pytest.raises(Exception, match="commit fail"):
            await repo.update(mock_db, db_obj=db_obj, obj_in={"name": "X"})
        mock_db.rollback.assert_called_once()


# ==================== delete ====================


class TestBaseDelete:

    @pytest.mark.asyncio
    async def test_soft_delete(self, repo, mock_db):
        obj = MagicMock()
        obj.is_deleted = False
        obj.deleted_at = None
        repo.get = AsyncMock(return_value=obj)
        result = await repo.delete(mock_db, id=uuid4(), soft_delete=True)
        assert result is obj
        assert obj.is_deleted is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_hard_delete(self, repo, mock_db):
        obj = MagicMock()
        repo.get = AsyncMock(return_value=obj)
        result = await repo.delete(mock_db, id=uuid4(), soft_delete=False)
        assert result is obj
        mock_db.delete.assert_called_once_with(obj)

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo, mock_db):
        repo.get = AsyncMock(return_value=None)
        result = await repo.delete(mock_db, id=uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_no_commit(self, repo, mock_db):
        obj = MagicMock()
        obj.is_deleted = False
        repo.get = AsyncMock(return_value=obj)
        await repo.delete(mock_db, id=uuid4(), commit=False)
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_rollback_on_error(self, repo, mock_db):
        repo.get = AsyncMock(side_effect=Exception("db error"))
        with pytest.raises(Exception, match="db error"):
            await repo.delete(mock_db, id=uuid4())
        mock_db.rollback.assert_called_once()


# ==================== bulk_create ====================


class TestBaseBulkCreate:

    @pytest.mark.asyncio
    async def test_bulk_create(self, repo, mock_db):
        schemas = [FakeCreateSchema(name="A"), FakeCreateSchema(name="B")]
        result = await repo.bulk_create(mock_db, objs_in=schemas)
        assert len(result) == 2
        mock_db.add_all.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_no_commit(self, repo, mock_db):
        schemas = [FakeCreateSchema(name="A")]
        await repo.bulk_create(mock_db, objs_in=schemas, commit=False)
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_create_rollback_on_error(self, repo, mock_db):
        mock_db.commit = AsyncMock(side_effect=Exception("fail"))
        schemas = [FakeCreateSchema(name="A")]
        with pytest.raises(Exception, match="fail"):
            await repo.bulk_create(mock_db, objs_in=schemas)
        mock_db.rollback.assert_called_once()


# ==================== search ====================


class TestBaseSearch:

    @pytest.mark.asyncio
    async def test_search(self, repo, mock_db):
        obj = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [obj]
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.search(
            mock_db, query="sensor", search_fields=["name", "description"]
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.search(
            mock_db, query="nothing", search_fields=["name"]
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_search_include_deleted(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.search(
            mock_db, query="x", search_fields=["name"], include_deleted=True
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = await repo.search(
            mock_db, query="x", search_fields=["name"], skip=5, limit=10
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_search_raises_on_error(self, repo, mock_db):
        mock_db.execute = AsyncMock(side_effect=Exception("db error"))
        with pytest.raises(Exception, match="db error"):
            await repo.search(mock_db, query="x", search_fields=["name"])
