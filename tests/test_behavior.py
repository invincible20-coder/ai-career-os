from __future__ import annotations

import unittest

from backend.models.behavior import BehaviorMetrics, BehaviorType
from backend.services.behavior_service import BehaviorService


class BehaviorClassificationTests(unittest.TestCase):
    def test_requires_minimum_data_before_classification(self) -> None:
        classification, explanation = BehaviorService.classify(
            BehaviorMetrics(
                user_key="user-1",
                total_applications=3,
                apps_per_day=3,
                success_rate=0.5,
                minimum_data_threshold_met=False,
            )
        )

        self.assertEqual(classification, BehaviorType.INSUFFICIENT_DATA)
        self.assertIn("Not enough", explanation)

    def test_classifies_networker_before_volume_based_types(self) -> None:
        classification, _ = BehaviorService.classify(
            BehaviorMetrics(
                user_key="user-1",
                total_applications=10,
                apps_per_day=12,
                success_rate=0.1,
                referral_ratio=0.4,
                role_diversity=2,
                minimum_data_threshold_met=True,
            )
        )

        self.assertEqual(classification, BehaviorType.NETWORKER)

    def test_classifies_mass_applier_from_high_volume_low_success(self) -> None:
        classification, _ = BehaviorService.classify(
            BehaviorMetrics(
                user_key="user-1",
                total_applications=16,
                apps_per_day=16,
                success_rate=0.01,
                referral_ratio=0,
                role_diversity=2,
                minimum_data_threshold_met=True,
            )
        )

        self.assertEqual(classification, BehaviorType.MASS_APPLIER)

    def test_classifies_desperate_from_high_volume_and_role_spread(self) -> None:
        classification, _ = BehaviorService.classify(
            BehaviorMetrics(
                user_key="user-1",
                total_applications=16,
                apps_per_day=16,
                success_rate=0.01,
                referral_ratio=0,
                role_diversity=10,
                minimum_data_threshold_met=True,
            )
        )

        self.assertEqual(classification, BehaviorType.DESPERATE)
