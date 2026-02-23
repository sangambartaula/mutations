import unittest
from unittest.mock import patch

from api.index import get_leaderboard


class LeaderboardTests(unittest.TestCase):
    @patch("api.index.get_bazaar_prices", return_value={})
    def test_veilshroom_is_included_with_recipe(self, _mock_prices):
        result = get_leaderboard(
            plots=3,
            fortune=2500,
            gh_upgrade=9,
            unique_crops=12,
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
        )

        veil = next((m for m in result["leaderboard"] if m["mutationName"] == "Veilshroom"), None)
        self.assertIsNotNone(veil, "Veilshroom should be present in leaderboard output.")

        ingredient_amounts = {i["name"]: i["amount"] for i in veil["breakdown"]["ingredients"]}
        self.assertEqual(ingredient_amounts.get("Red Mushroom"), 3)
        self.assertEqual(ingredient_amounts.get("Brown Mushroom"), 3)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_growth_stages_are_clamped_to_minimum_one(self, _mock_prices):
        result = get_leaderboard(
            plots=3,
            fortune=2500,
            gh_upgrade=9,
            unique_crops=12,
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
        )

        veil = next((m for m in result["leaderboard"] if m["mutationName"] == "Veilshroom"), None)
        self.assertIsNotNone(veil)
        self.assertEqual(veil["breakdown"]["growth_stages"], 1)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_profit_per_cycle_matches_profit_divided_by_estimated_time(self, _mock_prices):
        result = get_leaderboard(
            plots=3,
            fortune=2500,
            gh_upgrade=9,
            unique_crops=12,
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
        )

        for mutation in result["leaderboard"]:
            estimated_time = mutation["breakdown"]["estimated_time_hours"]
            if estimated_time <= 0:
                continue
            expected = mutation["profit"] / estimated_time
            self.assertAlmostEqual(mutation["profit_per_cycle"], expected, places=6)


if __name__ == "__main__":
    unittest.main()
