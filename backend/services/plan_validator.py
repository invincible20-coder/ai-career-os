"""
Strict planner validation rules.
"""

from __future__ import annotations

from collections import Counter

from backend.models.errors import ErrorDetail
from backend.models.plan import EXPECTED_STEP_ORDER, ExecutionPlan
from backend.services.exceptions import PlanValidationError


def validate_execution_plan(plan: ExecutionPlan) -> None:
    """Validate the planner output and reject invalid workflows."""

    actual_step_types = [step.step_type for step in plan.steps]
    step_counts = Counter(actual_step_types)
    errors: list[ErrorDetail] = []

    if len(plan.steps) != len(EXPECTED_STEP_ORDER):
        errors.append(
            ErrorDetail(
                code="invalid_plan_length",
                message="Planner must return exactly four workflow steps",
                step="plan",
                details={
                    "expected_steps": [step.value for step in EXPECTED_STEP_ORDER],
                    "actual_count": len(plan.steps),
                },
            )
        )

    for expected_step in EXPECTED_STEP_ORDER:
        occurrences = step_counts.get(expected_step, 0)
        if occurrences == 0:
            errors.append(
                ErrorDetail(
                    code="missing_plan_step",
                    message=f"Planner omitted required step '{expected_step.value}'",
                    step="plan",
                    details={"expected_step": expected_step.value},
                )
            )
        elif occurrences > 1:
            errors.append(
                ErrorDetail(
                    code="duplicate_plan_step",
                    message=f"Planner duplicated step '{expected_step.value}'",
                    step="plan",
                    details={
                        "expected_step": expected_step.value,
                        "occurrences": occurrences,
                    },
                )
            )

    expected_order = list(EXPECTED_STEP_ORDER)
    if actual_step_types != expected_order:
        errors.append(
            ErrorDetail(
                code="invalid_plan_order",
                message="Planner steps must follow plan -> search -> apply -> track",
                step="plan",
                details={
                    "expected_order": [step.value for step in expected_order],
                    "actual_order": [step.value for step in actual_step_types],
                },
            )
        )

    expected_numbers = list(range(1, len(plan.steps) + 1))
    actual_numbers = [step.step_number for step in plan.steps]
    if actual_numbers != expected_numbers:
        errors.append(
            ErrorDetail(
                code="invalid_step_numbers",
                message="Planner step numbers must be sequential starting at 1",
                step="plan",
                details={
                    "expected_numbers": expected_numbers,
                    "actual_numbers": actual_numbers,
                },
            )
        )

    if errors:
        raise PlanValidationError("Planner returned an invalid execution plan", errors=errors)
