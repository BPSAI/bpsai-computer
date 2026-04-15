"""Tests for Phase C message schemas and JSON Schema export."""

from __future__ import annotations

import json

from computer.contracts import (
    DispatchContent,
    DriverStatusContent,
    PlanProposalContent,
    ReviewResultContent,
    SessionResumeContent,
    all_schemas,
)


class TestPlanProposal:
    def test_valid(self):
        msg = PlanProposalContent(
            plan_id="plan-sprint-3", title="Sprint 3 Plan",
            tasks=["T3.1", "T3.2"], estimated_budget=5000,
        )
        assert msg.plan_id == "plan-sprint-3"
        assert len(msg.tasks) == 2

    def test_tasks_can_be_empty(self):
        msg = PlanProposalContent(
            plan_id="plan-empty", title="Empty plan",
            tasks=[], estimated_budget=0,
        )
        assert msg.tasks == []


class TestDriverStatus:
    def test_valid(self):
        msg = DriverStatusContent(
            session_id="s-1", task_id="T3.1",
            status="in_progress", progress_pct=50,
            current_step="Writing tests",
        )
        assert msg.progress_pct == 50

    def test_status_values(self):
        for status in ("pending", "in_progress", "complete", "failed", "blocked"):
            msg = DriverStatusContent(session_id="s-1", task_id="T3.1", status=status)
            assert msg.status == status


class TestReviewResult:
    def test_valid(self):
        msg = ReviewResultContent(
            session_id="s-1", task_id="T3.1", verdict="approved",
            comments=["Looks good"], issues=[],
        )
        assert msg.verdict == "approved"

    def test_verdict_values(self):
        for verdict in ("approved", "changes_requested", "rejected"):
            msg = ReviewResultContent(session_id="s-1", task_id="T3.1", verdict=verdict)
            assert msg.verdict == verdict


class TestSessionResume:
    def test_valid(self):
        msg = SessionResumeContent(
            session_id="s-1", reason="Task blocked, resuming after fix",
            resumed_from="s-0",
        )
        assert msg.session_id == "s-1"
        assert msg.resumed_from == "s-0"

    def test_resumed_from_optional(self):
        msg = SessionResumeContent(session_id="s-1", reason="Manual resume")
        assert msg.resumed_from is None


class TestSchemaExport:
    def test_all_schemas_export(self):
        schemas = all_schemas()
        assert isinstance(schemas, dict)
        expected_keys = {
            "ChannelEnvelope", "DispatchContent", "ResumeContent",
            "DispatchResultContent", "SessionStartedContent",
            "SessionCompleteContent", "SessionFailedContent",
            "SessionOutputContent", "SignalBatchItem", "SignalBatchRequest",
            "HeartbeatRequest", "PlanProposalContent", "DriverStatusContent",
            "ReviewResultContent", "SessionResumeContent",
        }
        assert expected_keys == set(schemas.keys())

    def test_schemas_are_valid_json_schema(self):
        schemas = all_schemas()
        for name, schema in schemas.items():
            assert "properties" in schema or "type" in schema, f"{name} missing properties/type"
            json.loads(json.dumps(schema))

    def test_schema_validates_valid_data(self):
        schema = DispatchContent.model_json_schema()
        assert "properties" in schema
        assert "target" in schema["properties"]
        assert "prompt" in schema["properties"]

    def test_single_source_of_truth(self):
        schema = DispatchContent.model_json_schema()
        agent_prop = schema["properties"]["agent"]
        assert agent_prop.get("default") == "driver"
