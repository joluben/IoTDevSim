"""
Tests for Dataset Service
Unit tests for dataset management business logic
"""

import pytest
import pandas as pd
import numpy as np
import os
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.services.dataset import DatasetService, UPLOAD_DIR
from app.models.dataset import Dataset, DatasetColumn, DatasetStatus, DatasetSource
from app.schemas.dataset import (
    DatasetCreate,
    DatasetUpdate,
    DatasetUploadCreate,
    DatasetGenerateRequest,
    DatasetFilters,
    GeneratorInfo,
)


# ==================== Fixtures ====================

@pytest.fixture
def dataset_service():
    """Create a DatasetService instance with mocked repository"""
    service = DatasetService()
    service.repository = AsyncMock()
    return service


@pytest.fixture
def mock_db():
    """Create a mock async database session"""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def sample_dataset():
    """Create a sample Dataset model instance"""
    ds = MagicMock(spec=Dataset)
    ds.id = uuid4()
    ds.name = "Test Dataset"
    ds.description = "A test dataset"
    ds.source = DatasetSource.UPLOAD
    ds.status = DatasetStatus.READY
    ds.file_path = str(UPLOAD_DIR / f"{ds.id}.csv")
    ds.file_format = "csv"
    ds.file_size = 1024
    ds.row_count = 100
    ds.column_count = 5
    ds.tags = ["test", "sensor"]
    ds.custom_metadata = {}
    ds.completeness_score = 98.5
    ds.validation_status = "valid"
    ds.validation_errors = []
    ds.generator_type = None
    ds.generator_config = {}
    ds.schema_definition = {}
    ds.is_deleted = False
    ds.created_at = datetime.now()
    ds.updated_at = datetime.now()
    ds.columns = []
    return ds


@pytest.fixture
def sample_csv_content():
    """Create sample CSV file content"""
    return b"timestamp,sensor_id,temperature,humidity\n2024-01-01T00:00:00,S001,22.5,45.0\n2024-01-01T01:00:00,S001,23.1,44.2\n2024-01-01T02:00:00,S002,21.8,46.5\n"


@pytest.fixture
def sample_upload_metadata():
    """Create sample upload metadata"""
    return DatasetUploadCreate(
        name="Uploaded Dataset",
        description="Test upload",
        tags=["upload", "test"],
        has_header=True,
        delimiter=",",
        encoding="utf-8",
    )


# ==================== CRUD Tests ====================


class TestCreateDataset:
    """Tests for dataset creation"""

    @pytest.mark.asyncio
    async def test_create_dataset_success(self, dataset_service, mock_db, sample_dataset):
        dataset_service.repository.get_by_name.return_value = None
        dataset_service.repository.create.return_value = sample_dataset

        dataset_in = DatasetCreate(
            name="New Dataset",
            source="manual",
            description="A new dataset",
            tags=["test"],
        )

        result = await dataset_service.create_dataset(mock_db, dataset_in)

        assert result == sample_dataset
        dataset_service.repository.get_by_name.assert_called_once_with(mock_db, "New Dataset")
        dataset_service.repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_dataset_duplicate_name(self, dataset_service, mock_db, sample_dataset):
        dataset_service.repository.get_by_name.return_value = sample_dataset

        dataset_in = DatasetCreate(
            name="Test Dataset",
            source="manual",
        )

        with pytest.raises(ValueError, match="already exists"):
            await dataset_service.create_dataset(mock_db, dataset_in)


class TestGetDataset:
    """Tests for getting a dataset"""

    @pytest.mark.asyncio
    async def test_get_dataset_success(self, dataset_service, mock_db, sample_dataset):
        dataset_service.repository.get_by_id.return_value = sample_dataset

        result = await dataset_service.get_dataset(mock_db, sample_dataset.id)

        assert result == sample_dataset
        dataset_service.repository.get_by_id.assert_called_once_with(
            mock_db, sample_dataset.id, include_columns=True
        )

    @pytest.mark.asyncio
    async def test_get_dataset_not_found(self, dataset_service, mock_db):
        dataset_service.repository.get_by_id.return_value = None
        fake_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            await dataset_service.get_dataset(mock_db, fake_id)


class TestUpdateDataset:
    """Tests for updating a dataset"""

    @pytest.mark.asyncio
    async def test_update_dataset_success(self, dataset_service, mock_db, sample_dataset):
        dataset_service.repository.get_by_id.return_value = sample_dataset
        dataset_service.repository.update.return_value = sample_dataset

        update_in = DatasetUpdate(description="Updated description")

        result = await dataset_service.update_dataset(mock_db, sample_dataset.id, update_in)

        assert result == sample_dataset
        dataset_service.repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_dataset_not_found(self, dataset_service, mock_db):
        dataset_service.repository.get_by_id.return_value = None

        update_in = DatasetUpdate(description="Updated")

        with pytest.raises(ValueError, match="not found"):
            await dataset_service.update_dataset(mock_db, uuid4(), update_in)

    @pytest.mark.asyncio
    async def test_update_dataset_duplicate_name(self, dataset_service, mock_db, sample_dataset):
        other_dataset = MagicMock(spec=Dataset)
        other_dataset.id = uuid4()
        other_dataset.name = "Other Dataset"

        dataset_service.repository.get_by_id.return_value = sample_dataset
        dataset_service.repository.get_by_name.return_value = other_dataset

        update_in = DatasetUpdate(name="Other Dataset")

        with pytest.raises(ValueError, match="already exists"):
            await dataset_service.update_dataset(mock_db, sample_dataset.id, update_in)


class TestDeleteDataset:
    """Tests for deleting a dataset"""

    @pytest.mark.asyncio
    async def test_delete_dataset_soft(self, dataset_service, mock_db, sample_dataset):
        dataset_service.repository.delete.return_value = sample_dataset

        result = await dataset_service.delete_dataset(mock_db, sample_dataset.id)

        assert result is True
        dataset_service.repository.delete.assert_called_once_with(
            mock_db, sample_dataset.id, soft_delete=True
        )

    @pytest.mark.asyncio
    async def test_delete_dataset_hard(self, dataset_service, mock_db, sample_dataset):
        dataset_service.repository.delete.return_value = sample_dataset

        result = await dataset_service.delete_dataset(mock_db, sample_dataset.id, hard_delete=True)

        assert result is True
        dataset_service.repository.delete.assert_called_once_with(
            mock_db, sample_dataset.id, soft_delete=False
        )

    @pytest.mark.asyncio
    async def test_delete_dataset_not_found(self, dataset_service, mock_db):
        dataset_service.repository.delete.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await dataset_service.delete_dataset(mock_db, uuid4())


# ==================== File Processing Tests ====================


class TestParseFile:
    """Tests for file parsing"""

    def test_parse_csv(self, dataset_service, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b,c\n1,2,3\n4,5,6\n")

        df = dataset_service._parse_file(csv_file, "csv")

        assert len(df) == 2
        assert list(df.columns) == ["a", "b", "c"]

    def test_parse_tsv(self, dataset_service, tmp_path):
        tsv_file = tmp_path / "test.tsv"
        tsv_file.write_text("a\tb\tc\n1\t2\t3\n")

        df = dataset_service._parse_file(tsv_file, "tsv")

        assert len(df) == 1
        assert list(df.columns) == ["a", "b", "c"]

    def test_parse_json(self, dataset_service, tmp_path):
        json_file = tmp_path / "test.json"
        json_file.write_text('[{"a": 1, "b": 2}, {"a": 3, "b": 4}]')

        df = dataset_service._parse_file(json_file, "json")

        assert len(df) == 2
        assert "a" in df.columns

    def test_parse_csv_no_header(self, dataset_service, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("1,2,3\n4,5,6\n")

        df = dataset_service._parse_file(csv_file, "csv", has_header=False)

        assert len(df) == 2
        assert len(df.columns) == 3

    def test_parse_csv_semicolon_delimiter(self, dataset_service, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a;b;c\n1;2;3\n")

        df = dataset_service._parse_file(csv_file, "csv", delimiter=";")

        assert list(df.columns) == ["a", "b", "c"]

    def test_parse_unsupported_format(self, dataset_service, tmp_path):
        file = tmp_path / "test.xyz"
        file.write_text("data")

        with pytest.raises(ValueError, match="Unsupported file format"):
            dataset_service._parse_file(file, "xyz")


class TestAnalyzeDataframe:
    """Tests for DataFrame analysis"""

    def test_analyze_numeric_columns(self, dataset_service):
        df = pd.DataFrame({
            "int_col": [1, 2, 3, 4, 5],
            "float_col": [1.1, 2.2, 3.3, 4.4, 5.5],
        })

        result = dataset_service._analyze_dataframe(df)

        assert len(result) == 2
        assert result[0]["name"] == "int_col"
        assert result[0]["data_type"] == "integer"
        assert result[0]["position"] == 0
        assert result[0]["null_count"] == 0
        assert result[0]["unique_count"] == 5
        assert result[0]["min_value"] is not None
        assert result[0]["max_value"] is not None
        assert result[0]["mean_value"] is not None

        assert result[1]["name"] == "float_col"
        assert result[1]["data_type"] == "float"

    def test_analyze_string_columns(self, dataset_service):
        df = pd.DataFrame({
            "name": ["Alice", "Bob", "Charlie"],
        })

        result = dataset_service._analyze_dataframe(df)

        assert result[0]["data_type"] == "string"
        assert result[0]["unique_count"] == 3
        assert result[0]["min_value"] is not None

    def test_analyze_with_nulls(self, dataset_service):
        df = pd.DataFrame({
            "col": [1, None, 3, None, 5],
        })

        result = dataset_service._analyze_dataframe(df)

        assert result[0]["null_count"] == 2
        assert result[0]["nullable"] is True

    def test_analyze_empty_dataframe(self, dataset_service):
        df = pd.DataFrame({"a": [], "b": []})

        result = dataset_service._analyze_dataframe(df)

        assert len(result) == 2
        assert result[0]["null_count"] == 0

    def test_analyze_sample_values(self, dataset_service):
        df = pd.DataFrame({
            "col": list(range(10)),
        })

        result = dataset_service._analyze_dataframe(df)

        assert len(result[0]["sample_values"]) == 5


class TestCalculateCompleteness:
    """Tests for completeness calculation"""

    def test_full_completeness(self, dataset_service):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        score = dataset_service._calculate_completeness(df)

        assert score == 100.0

    def test_partial_completeness(self, dataset_service):
        df = pd.DataFrame({"a": [1, None, 3], "b": [4, 5, None]})

        score = dataset_service._calculate_completeness(df)

        assert 60.0 < score < 70.0

    def test_empty_dataframe_completeness(self, dataset_service):
        df = pd.DataFrame()

        score = dataset_service._calculate_completeness(df)

        assert score == 100.0


# ==================== Generator Tests ====================


class TestGenerators:
    """Tests for synthetic data generators"""

    def test_temperature_generator(self, dataset_service):
        config = {
            "sensor_count": 2,
            "duration_days": 1,
            "sampling_interval": 3600,
            "base_temperature": 22.0,
            "variation_range": 5.0,
        }

        df = dataset_service._generate_temperature_data(config)

        assert len(df) > 0
        assert "timestamp" in df.columns
        assert "sensor_id" in df.columns
        assert "temperature" in df.columns
        assert "unit" in df.columns
        assert df["unit"].iloc[0] == "Celsius"
        # 2 sensors × 24 hours = 48 rows
        assert len(df) == 2 * 24

    def test_temperature_generator_defaults(self, dataset_service):
        config = {}

        df = dataset_service._generate_temperature_data(config)

        assert len(df) > 0
        assert "sensor_id" in df.columns

    def test_equipment_generator(self, dataset_service):
        config = {
            "equipment_types": ["pump", "motor"],
            "equipment_count": 3,
        }

        df = dataset_service._generate_equipment_data(config)

        assert len(df) > 0
        assert "equipment_id" in df.columns
        assert "type" in df.columns
        assert "status" in df.columns
        assert "load_percent" in df.columns
        assert "vibration" in df.columns
        # 2 types × 3 count × 24 hours = 144 rows
        assert len(df) == 2 * 3 * 24

    def test_environmental_generator(self, dataset_service):
        config = {
            "location_count": 2,
            "parameters": ["co2", "humidity"],
        }

        df = dataset_service._generate_environmental_data(config)

        assert len(df) > 0
        assert "location_id" in df.columns
        assert "parameter" in df.columns
        assert "value" in df.columns
        assert "unit" in df.columns
        # 2 locations × 2 parameters = 4 rows
        assert len(df) == 4

    def test_fleet_generator(self, dataset_service):
        config = {"vehicle_count": 5}

        df = dataset_service._generate_fleet_data(config)

        assert len(df) == 5
        assert "vehicle_id" in df.columns
        assert "latitude" in df.columns
        assert "longitude" in df.columns
        assert "speed" in df.columns
        assert "fuel_level" in df.columns

    def test_generate_data_dispatch(self, dataset_service):
        df = dataset_service._generate_data("temperature", {"sensor_count": 1, "duration_days": 1, "sampling_interval": 86400})
        assert "temperature" in df.columns

        df = dataset_service._generate_data("equipment", {"equipment_types": ["pump"], "equipment_count": 1})
        assert "equipment_id" in df.columns

        df = dataset_service._generate_data("environmental", {"location_count": 1, "parameters": ["co2"]})
        assert "location_id" in df.columns

        df = dataset_service._generate_data("fleet", {"vehicle_count": 1})
        assert "vehicle_id" in df.columns

    def test_generate_data_unknown_type(self, dataset_service):
        df = dataset_service._generate_data("unknown_type", {})
        assert len(df) == 1
        assert "timestamp" in df.columns


class TestGetGeneratorTypes:
    """Tests for generator type listing"""

    def test_returns_all_generators(self, dataset_service):
        generators = dataset_service.get_generator_types()

        assert len(generators) == 4
        ids = [g.id for g in generators]
        assert "temperature" in ids
        assert "equipment" in ids
        assert "environmental" in ids
        assert "fleet" in ids

    def test_generator_info_structure(self, dataset_service):
        generators = dataset_service.get_generator_types()

        for gen in generators:
            assert isinstance(gen, GeneratorInfo)
            assert gen.id
            assert gen.name
            assert gen.description
            assert gen.config_schema
            assert gen.example_config
            assert gen.output_columns


# ==================== Upload Integration Tests ====================


class TestUploadFile:
    """Tests for file upload flow"""

    @pytest.mark.asyncio
    async def test_upload_unsupported_format(self, dataset_service, mock_db, sample_upload_metadata):
        with pytest.raises(ValueError, match="Unsupported file format"):
            await dataset_service.upload_file(
                mock_db,
                file_content=b"data",
                filename="test.xyz",
                metadata=sample_upload_metadata,
            )

    @pytest.mark.asyncio
    async def test_upload_duplicate_name(self, dataset_service, mock_db, sample_dataset, sample_upload_metadata):
        dataset_service.repository.get_by_name.return_value = sample_dataset

        with pytest.raises(ValueError, match="already exists"):
            await dataset_service.upload_file(
                mock_db,
                file_content=b"a,b\n1,2\n",
                filename="test.csv",
                metadata=sample_upload_metadata,
            )


# ==================== Validation Tests ====================


class TestValidateDataset:
    """Tests for dataset validation"""

    @pytest.mark.asyncio
    async def test_validate_not_found(self, dataset_service, mock_db):
        dataset_service.repository.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await dataset_service.validate_dataset(mock_db, uuid4())

    @pytest.mark.asyncio
    async def test_validate_empty_dataset(self, dataset_service, mock_db, sample_dataset):
        sample_dataset.row_count = 0
        sample_dataset.columns = []
        sample_dataset.file_path = None
        sample_dataset.completeness_score = 0.0
        dataset_service.repository.get_by_id.return_value = sample_dataset
        dataset_service.repository.update_status.return_value = sample_dataset

        result = await dataset_service.validate_dataset(mock_db, sample_dataset.id)

        assert result.warning_count > 0
        warning_types = [w["type"] for w in result.warnings]
        assert "empty_dataset" in warning_types
        assert "no_columns" in warning_types

    @pytest.mark.asyncio
    async def test_validate_valid_dataset(self, dataset_service, mock_db, sample_dataset):
        col = MagicMock(spec=DatasetColumn)
        col.name = "temp"
        col.data_type = "float"
        sample_dataset.columns = [col]
        sample_dataset.file_path = None
        sample_dataset.completeness_score = 95.0
        dataset_service.repository.get_by_id.return_value = sample_dataset
        dataset_service.repository.update_status.return_value = sample_dataset

        result = await dataset_service.validate_dataset(mock_db, sample_dataset.id)

        assert result.is_valid is True
        assert result.error_count == 0


# ==================== Statistics Tests ====================


class TestStatistics:
    """Tests for statistics retrieval"""

    @pytest.mark.asyncio
    async def test_get_statistics(self, dataset_service, mock_db):
        expected = {
            "total": 10,
            "by_source": {"upload": 5, "generated": 5},
            "by_status": {"ready": 8, "error": 2},
            "total_rows": 50000,
            "total_size_bytes": 1024000,
        }
        dataset_service.repository.get_stats.return_value = expected

        result = await dataset_service.get_statistics(mock_db)

        assert result == expected
        dataset_service.repository.get_stats.assert_called_once_with(mock_db)


# ==================== Write File Tests ====================


class TestWriteFile:
    """Tests for file writing utility"""

    def test_write_file(self, tmp_path):
        file_path = tmp_path / "output.csv"
        content = b"hello,world\n1,2\n"

        DatasetService._write_file(file_path, content)

        assert file_path.exists()
        assert file_path.read_bytes() == content
