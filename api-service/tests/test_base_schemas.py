"""
Tests for Base Pydantic Schemas
Validation helpers, pagination, error/success responses, bulk operations, CSV schemas
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime
from pydantic import ValidationError

from app.schemas.base import (
    PaginationParams,
    SortOrder,
    SortParams,
    FilterParams,
    PaginatedResponse,
    ErrorDetail,
    ErrorResponse,
    SuccessResponse,
    HealthStatus,
    HealthCheck,
    BulkOperation,
    BulkOperationResult,
    FileUpload,
    CSVUploadParams,
    CSVValidationError,
    CSVUploadResult,
    validate_uuid,
    validate_non_empty_string,
    validate_positive_int,
    validate_email,
)


# ==================== PaginationParams ====================


class TestPaginationParams:

    def test_defaults(self):
        p = PaginationParams()
        assert p.skip == 0
        assert p.limit == 100

    def test_custom_values(self):
        p = PaginationParams(skip=10, limit=50)
        assert p.skip == 10
        assert p.limit == 50

    def test_negative_skip_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(skip=-1)

    def test_zero_limit_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)

    def test_limit_over_1000_rejected(self):
        with pytest.raises(ValidationError):
            PaginationParams(limit=1001)


# ==================== SortParams ====================


class TestSortParams:

    def test_defaults(self):
        s = SortParams()
        assert s.sort_by is None
        assert s.sort_order == "desc"

    def test_asc_order(self):
        s = SortParams(sort_order="asc")
        assert s.sort_order == "asc"


# ==================== FilterParams ====================


class TestFilterParams:

    def test_defaults(self):
        f = FilterParams()
        assert f.search is None
        assert f.is_active is None

    def test_with_search(self):
        f = FilterParams(search="sensor", is_active=True)
        assert f.search == "sensor"
        assert f.is_active is True


# ==================== PaginatedResponse ====================


class TestPaginatedResponse:

    def test_create_with_items(self):
        r = PaginatedResponse.create(items=["a", "b"], total=10, skip=0, limit=5)
        assert r.total == 10
        assert r.has_next is True
        assert r.has_prev is False
        assert len(r.items) == 2

    def test_create_last_page(self):
        r = PaginatedResponse.create(items=["x"], total=3, skip=2, limit=5)
        assert r.has_next is False
        assert r.has_prev is True

    def test_create_single_page(self):
        r = PaginatedResponse.create(items=["a", "b"], total=2, skip=0, limit=10)
        assert r.has_next is False
        assert r.has_prev is False

    def test_create_empty(self):
        r = PaginatedResponse.create(items=[], total=0, skip=0, limit=10)
        assert r.has_next is False
        assert r.has_prev is False
        assert r.total == 0


# ==================== ErrorDetail / ErrorResponse ====================


class TestErrorSchemas:

    def test_error_detail(self):
        e = ErrorDetail(type="validation", message="bad field", field="name", code="E001")
        assert e.type == "validation"
        assert e.field == "name"

    def test_error_response(self):
        r = ErrorResponse(error="Not found")
        assert r.error == "Not found"
        assert r.details is None
        assert isinstance(r.timestamp, datetime)

    def test_error_response_with_details(self):
        detail = ErrorDetail(type="auth", message="expired")
        r = ErrorResponse(error="Auth error", details=[detail], request_id="req-123")
        assert len(r.details) == 1
        assert r.request_id == "req-123"


# ==================== SuccessResponse ====================


class TestSuccessResponse:

    def test_basic(self):
        r = SuccessResponse(message="OK")
        assert r.message == "OK"
        assert r.data is None

    def test_with_data(self):
        r = SuccessResponse(message="Created", data={"id": "123"})
        assert r.data["id"] == "123"


# ==================== HealthCheck ====================


class TestHealthCheck:

    def test_healthy(self):
        h = HealthCheck(status=HealthStatus.HEALTHY, service="api", version="1.0")
        assert h.status == "healthy"

    def test_degraded(self):
        h = HealthCheck(
            status=HealthStatus.DEGRADED,
            service="api",
            version="1.0",
            checks={"db": True, "cache": False},
        )
        assert h.checks["cache"] is False


# ==================== BulkOperation ====================


class TestBulkOperation:

    def test_valid(self):
        ids = [uuid4()]
        b = BulkOperation(operation="delete", ids=ids)
        assert b.operation == "delete"

    def test_empty_ids_rejected(self):
        with pytest.raises(ValidationError):
            BulkOperation(operation="delete", ids=[])


class TestBulkOperationResult:

    def test_result(self):
        r = BulkOperationResult(operation="delete", total=5, successful=4, failed=1)
        assert r.total == 5
        assert r.failed == 1


# ==================== FileUpload / CSV ====================


class TestFileUpload:

    def test_valid(self):
        f = FileUpload(filename="data.csv", content_type="text/csv", size=1024)
        assert f.size == 1024

    def test_negative_size_rejected(self):
        with pytest.raises(ValidationError):
            FileUpload(filename="f.csv", content_type="text/csv", size=-1)


class TestCSVUploadParams:

    def test_defaults(self):
        c = CSVUploadParams()
        assert c.has_header is True
        assert c.delimiter == ","
        assert c.encoding == "utf-8"
        assert c.skip_rows == 0
        assert c.max_rows is None

    def test_custom(self):
        c = CSVUploadParams(delimiter=";", encoding="latin-1", skip_rows=1, max_rows=100)
        assert c.delimiter == ";"


class TestCSVValidationError:

    def test_valid(self):
        e = CSVValidationError(row=1, column="temp", error="out of range", value="999")
        assert e.row == 1


class TestCSVUploadResult:

    def test_valid(self):
        r = CSVUploadResult(total_rows=100, valid_rows=95, invalid_rows=5)
        assert r.total_rows == 100


# ==================== Validation Helpers ====================


class TestValidateUuid:

    def test_valid_string(self):
        uid = uuid4()
        result = validate_uuid(str(uid))
        assert result == uid

    def test_valid_uuid_object(self):
        uid = uuid4()
        result = validate_uuid(uid)
        assert result == uid

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError, match="Invalid UUID"):
            validate_uuid("not-a-uuid")

    def test_non_string_non_uuid_raises(self):
        with pytest.raises(ValueError, match="UUID must be"):
            validate_uuid(12345)


class TestValidateNonEmptyString:

    def test_valid(self):
        assert validate_non_empty_string("hello") == "hello"

    def test_strips_whitespace(self):
        assert validate_non_empty_string("  hello  ") == "hello"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            validate_non_empty_string("   ")

    def test_non_string_raises(self):
        with pytest.raises(ValueError, match="string"):
            validate_non_empty_string(123)


class TestValidatePositiveInt:

    def test_valid(self):
        assert validate_positive_int(5) == 5

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="positive"):
            validate_positive_int(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="positive"):
            validate_positive_int(-1)

    def test_non_int_raises(self):
        with pytest.raises(ValueError, match="positive"):
            validate_positive_int("5")


class TestValidateEmail:

    def test_valid(self):
        assert validate_email("User@Example.COM") == "user@example.com"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid email"):
            validate_email("not-an-email")

    def test_non_string_raises(self):
        with pytest.raises(ValueError, match="string"):
            validate_email(123)
