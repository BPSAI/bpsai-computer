"""Tests for permission-request and permission-response message schemas (T2I.5)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from computer.contracts import (
    PermissionRequestContent,
    PermissionResponseContent,
    all_schemas,
)


class TestPermissionRequestContent:
    """Validate permission-request message schema."""

    def test_valid_request(self):
        msg = PermissionRequestContent(
            path="src/computer/daemon.py",
            operation="write",
            reason="Need to update daemon config for hotfix",
            task_id="T2I.5",
        )
        assert msg.path == "src/computer/daemon.py"
        assert msg.operation == "write"
        assert msg.reason == "Need to update daemon config for hotfix"
        assert msg.task_id == "T2I.5"

    def test_all_operations_valid(self):
        for op in ("read", "write", "execute"):
            msg = PermissionRequestContent(
                path="/some/path", operation=op,
                reason="testing", task_id="T1.1",
            )
            assert msg.operation == op

    def test_invalid_operation_rejected(self):
        with pytest.raises(ValidationError):
            PermissionRequestContent(
                path="/some/path", operation="delete",
                reason="testing", task_id="T1.1",
            )

    def test_path_required(self):
        with pytest.raises(ValidationError):
            PermissionRequestContent(
                operation="read", reason="testing", task_id="T1.1",
            )

    def test_operation_required(self):
        with pytest.raises(ValidationError):
            PermissionRequestContent(
                path="/some/path", reason="testing", task_id="T1.1",
            )

    def test_reason_required(self):
        with pytest.raises(ValidationError):
            PermissionRequestContent(
                path="/some/path", operation="read", task_id="T1.1",
            )

    def test_task_id_required(self):
        with pytest.raises(ValidationError):
            PermissionRequestContent(
                path="/some/path", operation="read", reason="testing",
            )


class TestPermissionResponseContent:
    """Validate permission-response message schema."""

    def test_valid_approved(self):
        msg = PermissionResponseContent(
            approved=True,
            scope="file",
            ttl=3600,
        )
        assert msg.approved is True
        assert msg.scope == "file"
        assert msg.ttl == 3600

    def test_valid_denied(self):
        msg = PermissionResponseContent(
            approved=False,
            scope="directory",
            ttl=0,
        )
        assert msg.approved is False

    def test_all_scopes_valid(self):
        for scope in ("file", "directory", "glob"):
            msg = PermissionResponseContent(
                approved=True, scope=scope, ttl=300,
            )
            assert msg.scope == scope

    def test_invalid_scope_rejected(self):
        with pytest.raises(ValidationError):
            PermissionResponseContent(
                approved=True, scope="universe", ttl=300,
            )

    def test_approved_required(self):
        with pytest.raises(ValidationError):
            PermissionResponseContent(scope="file", ttl=300)

    def test_scope_required(self):
        with pytest.raises(ValidationError):
            PermissionResponseContent(approved=True, ttl=300)

    def test_ttl_required(self):
        with pytest.raises(ValidationError):
            PermissionResponseContent(approved=True, scope="file")

    def test_ttl_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            PermissionResponseContent(approved=True, scope="file", ttl=-1)

    def test_request_id_optional(self):
        msg = PermissionResponseContent(
            approved=True, scope="file", ttl=300,
            request_id="msg-req-1",
        )
        assert msg.request_id == "msg-req-1"

    def test_request_id_defaults_none(self):
        msg = PermissionResponseContent(
            approved=True, scope="file", ttl=300,
        )
        assert msg.request_id is None


class TestPermissionSchemaExport:
    """Permission models appear in all_schemas() for cross-repo validation."""

    def test_permission_request_in_all_schemas(self):
        schemas = all_schemas()
        assert "PermissionRequestContent" in schemas

    def test_permission_response_in_all_schemas(self):
        schemas = all_schemas()
        assert "PermissionResponseContent" in schemas

    def test_permission_request_schema_has_required_fields(self):
        schema = PermissionRequestContent.model_json_schema()
        props = schema["properties"]
        assert "path" in props
        assert "operation" in props
        assert "reason" in props
        assert "task_id" in props

    def test_permission_response_schema_has_required_fields(self):
        schema = PermissionResponseContent.model_json_schema()
        props = schema["properties"]
        assert "approved" in props
        assert "scope" in props
        assert "ttl" in props

    def test_schemas_are_valid_json(self):
        schemas = all_schemas()
        for name in ("PermissionRequestContent", "PermissionResponseContent"):
            json.loads(json.dumps(schemas[name]))
