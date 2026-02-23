import unittest
import math
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

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_all_in_aloe_uses_reset_adjusted_special_multiplier_at_stage_14(self, _mock_prices):
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

        aloe = next((m for m in result["leaderboard"] if m["mutationName"] == "All-in Aloe"), None)
        self.assertIsNotNone(aloe)
        self.assertEqual(aloe["breakdown"]["growth_stages"], 14)

        sunflower = next((y for y in aloe["breakdown"]["yields"] if y["name"] == "Sunflower"), None)
        self.assertIsNotNone(sunflower)
        self.assertEqual(sunflower["math"]["special"], 9.37)

    @patch("api.index.get_bazaar_prices", return_value={"Lonelily": {"buyPrice": 100, "sellPrice": 90}})
    def test_hourly_mode_uses_expected_value_formula(self, _mock_prices):
        plots = 2
        default_chance = 0.25
        result = get_leaderboard(
            plots=plots,
            fortune=2500,
            gh_upgrade=9,
            unique_crops=12,
            mode="hourly",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
            mutation_chance=default_chance,
            harvest_mode="full",
            custom_time_hours=24.0,
        )

        lonelily = next((m for m in result["leaderboard"] if m["mutationName"] == "Lonelily"), None)
        self.assertIsNotNone(lonelily)

        x = lonelily["breakdown"]["base_limit"]
        chance = lonelily["hourly"]["mutation_chance"]
        self.assertAlmostEqual(chance, 0.02, places=6)
        cycle_time_hours = result["metadata"]["cycle_time_hours"]
        t_cycles = math.log(1.0 / x) / math.log(1.0 - chance)
        harvest_time_hours = max(cycle_time_hours, t_cycles * cycle_time_hours)
        completed_cycles = int(harvest_time_hours // cycle_time_hours)
        expected_mutations = plots * x * (1.0 - ((1.0 - chance) ** completed_cycles))
        expected_profit_per_hour = (expected_mutations * 100.0) / harvest_time_hours

        self.assertAlmostEqual(lonelily["profit_per_hour"], expected_profit_per_hour, places=6)


if __name__ == "__main__":
    unittest.main()
