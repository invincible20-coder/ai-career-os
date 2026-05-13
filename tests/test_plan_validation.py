from __future__ import annotations

import unittest

from backend.models.plan import ExecutionPlan, PlanStep, StepType
from backend.services.exceptions import PlanValidationError
from backend.services.plan_validator import validate_execution_plan


class PlanValidationTests(unittest.TestCase):
    def test_accepts_expected_plan_shape(self) -> None:
        plan = ExecutionPlan(
            goal="Get a backend engineer role",
            summary="Search, tailor, and track",
            steps=[
                PlanStep(step_number=1, step_type=StepType.PLAN, description="Confirm strategy"),
                PlanStep(
                    step_number=2,
                    step_type=StepType.SEARCH,
                    description="Search for backend roles",
                    parameters={"query": "Backend Engineer", "location": "India"},
                ),
                PlanStep(step_number=3, step_type=StepType.APPLY, description="Prepare applications"),
                PlanStep(step_number=4, step_type=StepType.TRACK, description="Track applications"),
            ],
        )

        validate_execution_plan(plan)

    def test_rejects_missing_required_step(self) -> None:
        plan = ExecutionPlan(
            goal="Get a backend engineer role",
            summary="Missing tracking step",
            steps=[
                PlanStep(step_number=1, step_type=StepType.PLAN, description="Confirm strategy"),
                PlanStep(
                    step_number=2,
                    step_type=StepType.SEARCH,
                    description="Search for backend roles",
                ),
                PlanStep(step_number=3, step_type=StepType.APPLY, description="Prepare applications"),
            ],
        )

        with self.assertRaises(PlanValidationError) as context:
            validate_execution_plan(plan)

        codes = {error.code for error in context.exception.errors}
        self.assertIn("missing_plan_step", codes)
        self.assertIn("invalid_plan_length", codes)

    def test_rejects_duplicate_and_out_of_order_steps(self) -> None:
        plan = ExecutionPlan(
            goal="Get a backend engineer role",
            summary="Out-of-order plan",
            steps=[
                PlanStep(step_number=1, step_type=StepType.PLAN, description="Confirm strategy"),
                PlanStep(step_number=2, step_type=StepType.APPLY, description="Prepare applications"),
                PlanStep(step_number=3, step_type=StepType.APPLY, description="Duplicate apply"),
                PlanStep(step_number=4, step_type=StepType.TRACK, description="Track applications"),
            ],
        )

        with self.assertRaises(PlanValidationError) as context:
            validate_execution_plan(plan)

        codes = {error.code for error in context.exception.errors}
        self.assertIn("duplicate_plan_step", codes)
        self.assertIn("missing_plan_step", codes)
        self.assertIn("invalid_plan_order", codes)
