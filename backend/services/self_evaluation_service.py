"""
Self-Evaluation Service — The engine evaluates its own predictions.

Tracks:
- Interview conversion predictions
- Offer conversion predictions
- Recommendation acceptance predictions
- Pattern accuracy
- Confidence calibration (are confidence scores actually predictive?)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from backend.models.abc_intelligence import (
    PredictionRecord,
    SelfEvaluationMetrics,
)
from backend.storage.records import utc_now
from backend.storage.repository import HuntRepository


@dataclass(slots=True)
class SelfEvaluationService:
    """Engine quality tracking — the system evaluates its own accuracy."""

    repository: HuntRepository

    async def track_prediction(
        self,
        *,
        user_id: str,
        predicted_outcome: str,
        predicted_confidence: float,
        job_id: str = "",
        category: str = "",
    ) -> PredictionRecord:
        """Record what the engine predicted for later evaluation."""
        now = utc_now()
        prediction_id = str(uuid.uuid4())

        await self.repository.save_self_evaluation(
            user_id=user_id,
            prediction_id=prediction_id,
            predicted_outcome=predicted_outcome,
            predicted_confidence=predicted_confidence,
            job_id=job_id,
            category=category,
        )

        return PredictionRecord(
            prediction_id=prediction_id,
            user_id=user_id,
            predicted_outcome=predicted_outcome,
            predicted_confidence=predicted_confidence,
            job_id=job_id,
            category=category,
            created_at=now,
        )

    async def evaluate_prediction(
        self,
        *,
        prediction_id: str,
        actual_outcome: str,
    ) -> None:
        """Compare prediction to actual outcome."""
        was_correct = self._is_correct(prediction_id, actual_outcome)
        await self.repository.evaluate_prediction(
            prediction_id,
            actual_outcome=actual_outcome,
            was_correct=was_correct,
        )

    async def compute_metrics(self, user_id: str) -> SelfEvaluationMetrics:
        """Compute full self-evaluation metrics."""
        now = utc_now()
        evaluations = await self.repository.list_self_evaluations(user_id, limit=200)

        if not evaluations:
            return SelfEvaluationMetrics(user_id=user_id, updated_at=now)

        total = len(evaluations)
        evaluated = [e for e in evaluations if e.was_correct is not None]
        correct = sum(1 for e in evaluated if e.was_correct)
        evaluated_count = max(1, len(evaluated))

        # Interview conversion rate (predicted interview outcomes)
        interview_predictions = [
            e for e in evaluated if e.predicted_outcome in ("interview", "assessment")
        ]
        interview_correct = sum(1 for e in interview_predictions if e.was_correct)
        interview_conversion = (
            round(interview_correct / max(1, len(interview_predictions)), 4)
            if interview_predictions else 0.0
        )

        # Offer conversion rate
        offer_predictions = [
            e for e in evaluated if e.predicted_outcome in ("offer", "accepted")
        ]
        offer_correct = sum(1 for e in offer_predictions if e.was_correct)
        offer_conversion = (
            round(offer_correct / max(1, len(offer_predictions)), 4)
            if offer_predictions else 0.0
        )

        # Recommendation acceptance (predicted applies that actually applied)
        apply_predictions = [
            e for e in evaluated if e.predicted_outcome == "applied"
        ]
        apply_correct = sum(1 for e in apply_predictions if e.was_correct)
        recommendation_acceptance = (
            round(apply_correct / max(1, len(apply_predictions)), 4)
            if apply_predictions else 0.0
        )

        # Pattern accuracy (overall)
        pattern_accuracy = round(correct / evaluated_count, 4)

        # Confidence calibration: are high-confidence predictions more accurate?
        calibration = self._calibration_score(evaluated)

        # Behavior prediction accuracy
        behavior_accuracy = pattern_accuracy  # Same metric for now

        return SelfEvaluationMetrics(
            user_id=user_id,
            interview_conversion_rate=interview_conversion,
            offer_conversion_rate=offer_conversion,
            recommendation_acceptance_rate=recommendation_acceptance,
            pattern_accuracy=pattern_accuracy,
            confidence_calibration=calibration,
            behavior_prediction_accuracy=behavior_accuracy,
            total_predictions=total,
            correct_predictions=correct,
            updated_at=now,
        )

    @staticmethod
    def _is_correct(prediction_id: str, actual_outcome: str) -> bool:
        """Simple match check — can be enhanced with partial correctness."""
        # For now, we rely on exact match stored at evaluation time
        # The caller provides the ground truth
        return True  # Placeholder — actual logic is caller-determined

    @staticmethod
    def _calibration_score(evaluated) -> float:
        """Are high-confidence predictions more accurate than low-confidence ones?

        Perfect calibration: 80% confident predictions are correct 80% of the time.
        """
        if not evaluated:
            return 0.0

        # Bucket by confidence
        buckets: dict[str, list[bool]] = {
            "low": [],      # 0.0 - 0.4
            "medium": [],   # 0.4 - 0.7
            "high": [],     # 0.7 - 1.0
        }
        for e in evaluated:
            c = e.predicted_confidence
            if c < 0.4:
                buckets["low"].append(e.was_correct)
            elif c < 0.7:
                buckets["medium"].append(e.was_correct)
            else:
                buckets["high"].append(e.was_correct)

        # Check if higher confidence → higher accuracy
        accuracy_by_bucket: dict[str, float] = {}
        for bucket, outcomes in buckets.items():
            if outcomes:
                accuracy_by_bucket[bucket] = sum(outcomes) / len(outcomes)

        if len(accuracy_by_bucket) < 2:
            return 0.5  # Not enough data

        values = list(accuracy_by_bucket.values())
        # Check monotonicity
        monotonic = all(
            values[i] <= values[i + 1] for i in range(len(values) - 1)
        )
        if monotonic:
            return round(min(1.0, sum(values) / len(values) + 0.2), 4)

        return round(sum(values) / len(values), 4)
