import unittest
from unittest.mock import patch

from api.index import (
    DEFAULT_METRIC_SPAWN_CHANCE,
    LONELILY_METRIC_SPAWN_CHANCE,
    get_leaderboard,
)


class LeaderboardTests(unittest.TestCase):
    @patch("api.index.get_bazaar_prices", return_value={})
    def test_mode_specific_fortune_buff_math(self, _mock_prices):
        result = get_leaderboard(
            plots=3,
            fortune=100,
            gh_upgrade=9,
            unique_crops=12,
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
            harvest_harbinger=True,
            infini_vacuum=True,
            dark_cacao=True,
            hypercharge_level=20,
        )

        breakdown = result["metadata"]["fortune_breakdown"]
        self.assertEqual(breakdown["base_fortune"], 100)
        self.assertEqual(breakdown["bonus_total"], 510)
        self.assertEqual(breakdown["effective_fortune"], 610)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_split_greenhouse_and_evergreen_controls_affect_backend_math(self, _mock_prices):
        maxed = get_leaderboard(
            plots=3,
            fortune=2500,
            gh_yield_upgrade=9,
            gh_speed_upgrade=9,
            evergreen_chip_level=20,
            evergreen_chip_rarity="legendary",
            unique_crops=12,
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
        )
        reduced = get_leaderboard(
            plots=3,
            fortune=2500,
            gh_yield_upgrade=0,
            gh_speed_upgrade=0,
            evergreen_chip_level=0,
            evergreen_chip_rarity="legendary",
            unique_crops=12,
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
        )

        self.assertLess(maxed["metadata"]["cycle_time_hours"], reduced["metadata"]["cycle_time_hours"])
        self.assertEqual(maxed["metadata"]["yield_breakdown"]["evergreen_bonus"], 0.6)
        self.assertEqual(reduced["metadata"]["yield_breakdown"]["evergreen_bonus"], 0.0)
        self.assertEqual(maxed["metadata"]["speed_breakdown"]["greenhouse_speed_upgrade"], 9)
        self.assertEqual(reduced["metadata"]["speed_breakdown"]["greenhouse_speed_upgrade"], 0)

        devourer_maxed = next((m for m in maxed["leaderboard"] if m["mutationName"] == "Devourer"), None)
        devourer_reduced = next((m for m in reduced["leaderboard"] if m["mutationName"] == "Devourer"), None)
        self.assertIsNotNone(devourer_maxed)
        self.assertIsNotNone(devourer_reduced)

        pumpkin_maxed = next((y for y in devourer_maxed["breakdown"]["yields"] if y["name"] == "Pumpkin"), None)
        pumpkin_reduced = next((y for y in devourer_reduced["breakdown"]["yields"] if y["name"] == "Pumpkin"), None)
        self.assertIsNotNone(pumpkin_maxed)
        self.assertIsNotNone(pumpkin_reduced)
        self.assertEqual(pumpkin_maxed["math"]["evergreen_buff"], 0.6)
        self.assertEqual(pumpkin_reduced["math"]["evergreen_buff"], 0.0)
        self.assertGreater(pumpkin_maxed["amount"], pumpkin_reduced["amount"])

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_chip_rarity_changes_hypercharge_and_evergreen_scaling(self, _mock_prices):
        rare = get_leaderboard(
            plots=3,
            fortune=100,
            gh_yield_upgrade=9,
            gh_speed_upgrade=9,
            unique_crops=12,
            harvest_harbinger=False,
            infini_vacuum=True,
            dark_cacao=False,
            hypercharge_level=10,
            hypercharge_rarity="rare",
            evergreen_chip_level=10,
            evergreen_chip_rarity="rare",
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
        )
        legendary = get_leaderboard(
            plots=3,
            fortune=100,
            gh_yield_upgrade=9,
            gh_speed_upgrade=9,
            unique_crops=12,
            harvest_harbinger=False,
            infini_vacuum=True,
            dark_cacao=False,
            hypercharge_level=10,
            hypercharge_rarity="legendary",
            evergreen_chip_level=10,
            evergreen_chip_rarity="legendary",
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
        )

        self.assertAlmostEqual(rare["metadata"]["fortune_breakdown"]["affected_multiplier"], 1.3, places=6)
        self.assertAlmostEqual(legendary["metadata"]["fortune_breakdown"]["affected_multiplier"], 1.5, places=6)
        self.assertAlmostEqual(rare["metadata"]["yield_breakdown"]["evergreen_bonus"], 0.2, places=6)
        self.assertAlmostEqual(legendary["metadata"]["yield_breakdown"]["evergreen_bonus"], 0.3, places=6)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_chip_levels_are_clamped_by_rarity(self, _mock_prices):
        result = get_leaderboard(
            plots=3,
            fortune=2500,
            gh_yield_upgrade=9,
            gh_speed_upgrade=9,
            unique_crops=12,
            hypercharge_level=20,
            hypercharge_rarity="rare",
            evergreen_chip_level=20,
            evergreen_chip_rarity="rare",
            overdrive_chip_level=20,
            overdrive_chip_rarity="rare",
            overdrive_crop="Pumpkin",
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
        )

        self.assertAlmostEqual(result["metadata"]["fortune_breakdown"]["affected_multiplier"], 1.3, places=6)
        self.assertAlmostEqual(result["metadata"]["yield_breakdown"]["evergreen_bonus"], 0.2, places=6)
        self.assertEqual(result["metadata"]["yield_breakdown"]["overdrive_bonus"], 50.0)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_overdrive_bonus_only_applies_to_matching_crop(self, _mock_prices):
        baseline = get_leaderboard(
            plots=3,
            fortune=0,
            gh_yield_upgrade=0,
            gh_speed_upgrade=0,
            unique_crops=0,
            evergreen_chip_level=0,
            improved_harvest_boost=False,
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
        )
        with_overdrive = get_leaderboard(
            plots=3,
            fortune=0,
            gh_yield_upgrade=0,
            gh_speed_upgrade=0,
            unique_crops=0,
            evergreen_chip_level=0,
            improved_harvest_boost=False,
            overdrive_chip_level=20,
            overdrive_chip_rarity="legendary",
            overdrive_crop="Pumpkin",
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
        )

        devourer_baseline = next((m for m in baseline["leaderboard"] if m["mutationName"] == "Devourer"), None)
        devourer_overdrive = next((m for m in with_overdrive["leaderboard"] if m["mutationName"] == "Devourer"), None)
        self.assertIsNotNone(devourer_baseline)
        self.assertIsNotNone(devourer_overdrive)

        pumpkin_baseline = next((y for y in devourer_baseline["breakdown"]["yields"] if y["name"] == "Pumpkin"), None)
        pumpkin_overdrive = next((y for y in devourer_overdrive["breakdown"]["yields"] if y["name"] == "Pumpkin"), None)
        mushroom_baseline = next((y for y in devourer_baseline["breakdown"]["yields"] if y["name"] == "Mushroom"), None)
        mushroom_overdrive = next((y for y in devourer_overdrive["breakdown"]["yields"] if y["name"] == "Mushroom"), None)

        self.assertIsNotNone(pumpkin_baseline)
        self.assertIsNotNone(pumpkin_overdrive)
        self.assertIsNotNone(mushroom_baseline)
        self.assertIsNotNone(mushroom_overdrive)
        self.assertGreater(pumpkin_overdrive["amount"], pumpkin_baseline["amount"])
        self.assertAlmostEqual(mushroom_overdrive["amount"], mushroom_baseline["amount"], places=6)
        self.assertEqual(pumpkin_overdrive["math"]["overdrive_bonus"], 140.0)
        self.assertEqual(mushroom_overdrive["math"]["overdrive_bonus"], 0.0)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_legacy_greenhouse_upgrade_still_feeds_split_defaults(self, _mock_prices):
        legacy = get_leaderboard(
            plots=3,
            fortune=2500,
            gh_upgrade=4,
            unique_crops=12,
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
        )

        self.assertEqual(legacy["metadata"]["yield_breakdown"]["greenhouse_yield_upgrade"], 4)
        self.assertEqual(legacy["metadata"]["speed_breakdown"]["greenhouse_speed_upgrade"], 4)

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
    def test_veilshroom_matches_other_one_cycle_common_mutations(self, _mock_prices):
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
        ashwreath = next((m for m in result["leaderboard"] if m["mutationName"] == "Ashwreath"), None)
        self.assertIsNotNone(veil)
        self.assertIsNotNone(ashwreath)
        self.assertEqual(veil["breakdown"]["growth_stages"], 1)
        self.assertEqual(ashwreath["breakdown"]["growth_stages"], 1)
        self.assertAlmostEqual(veil["breakdown"]["estimated_time_hours"], result["metadata"]["cycle_time_hours"], places=6)
        self.assertAlmostEqual(veil["breakdown"]["estimated_time_hours"], ashwreath["breakdown"]["estimated_time_hours"], places=6)
        expected_hours = ((1.0 / DEFAULT_METRIC_SPAWN_CHANCE) + 1.0) * result["metadata"]["cycle_time_hours"]
        self.assertAlmostEqual(veil["hourly"]["expected_hours"], expected_hours, places=6)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_profit_per_hour_matches_expected_cycle_model(self, _mock_prices):
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
            expected_hours = mutation["hourly"]["expected_hours"]
            self.assertIsNotNone(expected_hours)
            self.assertAlmostEqual(mutation["profit_per_hour"], mutation["profit"] / expected_hours, places=6)
            self.assertAlmostEqual(mutation["profit_per_hour"], mutation["hourly"]["profit_per_hour"], places=6)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_public_leaderboard_exposes_growth_cycle_metric_and_omits_removed_cycle_metrics(self, _mock_prices):
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
            growth_stages = mutation["breakdown"]["growth_stages"]
            spawn_chance = LONELILY_METRIC_SPAWN_CHANCE if mutation["mutationName"] == "Lonelily" else DEFAULT_METRIC_SPAWN_CHANCE
            expected_cycles = (1.0 / spawn_chance) + growth_stages
            self.assertAlmostEqual(
                mutation["profit_per_growth_cycle"],
                mutation["profit"] / expected_cycles,
                places=6,
            )
            self.assertAlmostEqual(mutation["hourly"]["expected_cycles"], expected_cycles, places=6)
            self.assertIn("warning_messages", mutation)
            self.assertNotIn("profit_per_cycle", mutation)
            self.assertNotIn("break_even_cycles", mutation)
            self.assertNotIn("break_even_cycles_display", mutation)
            self.assertNotIn("profit_per_cycle", mutation["hourly"])
            self.assertNotIn("break_even_cycles", mutation["hourly"])
            self.assertNotIn("break_even_cycles_display", mutation["hourly"])

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_invalid_string_modes_fall_back_to_safe_defaults(self, _mock_prices):
        result = get_leaderboard(
            plots=3,
            fortune=2500,
            gh_upgrade=9,
            unique_crops=12,
            mode=" definitely-not-valid ",
            setup_mode="oops",
            sell_mode="still-nope",
            target_crop="not-a-real-crop",
            maxed_crops="Mushroom, Mushroom, nope",
        )

        self.assertGreater(len(result["leaderboard"]), 0)
        self.assertEqual(result["metadata"]["missing_crops"].count("Mushroom"), 0)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_special_mutations_expose_warning_messages(self, _mock_prices):
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

        messages_by_name = {
            mutation["mutationName"]: mutation.get("warning_messages", [])
            for mutation in result["leaderboard"]
        }
        self.assertTrue(any("Devourer can spread" in msg for msg in messages_by_name["Devourer"]))
        self.assertTrue(any("120 growth stages" in msg for msg in messages_by_name["Magic Jellybean"]))
        self.assertTrue(any("raw multiplier there is 60x" in msg for msg in messages_by_name["All-in Aloe"]))

    @patch("api.index.get_bazaar_prices", return_value={"Magic Jellybean": {"buyPrice": 1000, "sellPrice": 900}})
    def test_profit_per_hour_uses_profit_per_harvest_divided_by_expected_hours(self, _mock_prices):
        result = get_leaderboard(
            plots=1,
            fortune=2500,
            gh_upgrade=9,
            unique_crops=12,
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
            mutation_chance=0.25,
            per_harvest_cost=50.0,
        )

        jellybean = next((m for m in result["leaderboard"] if m["mutationName"] == "Magic Jellybean"), None)
        self.assertIsNotNone(jellybean)

        expected_hours = ((1.0 / DEFAULT_METRIC_SPAWN_CHANCE) + jellybean["breakdown"]["growth_stages"]) * result["metadata"]["cycle_time_hours"]
        self.assertAlmostEqual(jellybean["profit_per_hour"], jellybean["profit"] / expected_hours, places=6)

    @patch("api.index.get_bazaar_prices", return_value={"All-in Aloe": {"buyPrice": 1_250_000, "sellPrice": 1_000_000}})
    def test_all_in_aloe_profit_metrics_use_expected_cycle_model(self, _mock_prices):
        result = get_leaderboard(
            plots=1,
            fortune=2500,
            gh_upgrade=9,
            unique_crops=12,
            mode="profit",
            setup_mode="buy_order",
            sell_mode="sell_offer",
            target_crop=None,
            maxed_crops="",
            mutation_chance=0.25,
        )

        aloe = next((m for m in result["leaderboard"] if m["mutationName"] == "All-in Aloe"), None)
        self.assertIsNotNone(aloe)

        expected_cycles = (1.0 / DEFAULT_METRIC_SPAWN_CHANCE) + aloe["breakdown"]["growth_stages"]
        expected_hours = expected_cycles * result["metadata"]["cycle_time_hours"]
        self.assertAlmostEqual(aloe["profit_per_growth_cycle"], aloe["profit"] / expected_cycles, places=6)
        self.assertAlmostEqual(aloe["profit_per_hour"], aloe["profit"] / expected_hours, places=6)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_lonelily_uses_full_harvest_breakdown_but_special_timing_metrics(self, _mock_prices):
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
            mutation_chance=0.25,
            harvest_mode="full",
            custom_time_hours=24.0,
        )

        lonelily = next((m for m in result["leaderboard"] if m["mutationName"] == "Lonelily"), None)
        self.assertIsNotNone(lonelily)
        lonelily_yield = next((y for y in lonelily["breakdown"]["yields"] if y["name"] == "Lonelily"), None)
        self.assertIsNotNone(lonelily_yield)
        self.assertAlmostEqual(lonelily_yield["amount"], 75.0, places=6)
        expected_cycles = (1.0 / LONELILY_METRIC_SPAWN_CHANCE) + lonelily["breakdown"]["growth_stages"]
        self.assertAlmostEqual(lonelily["hourly"]["p"], LONELILY_METRIC_SPAWN_CHANCE, places=9)
        self.assertAlmostEqual(lonelily["profit_per_growth_cycle"], lonelily["profit"] / expected_cycles, places=6)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_merged_mushroom_yield_sums_base_drop_for_formula_display(self, _mock_prices):
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

        devourer = next((m for m in result["leaderboard"] if m["mutationName"] == "Devourer"), None)
        self.assertIsNotNone(devourer)

        mushroom = next((y for y in devourer["breakdown"]["yields"] if y["name"] == "Mushroom"), None)
        self.assertIsNotNone(mushroom)
        self.assertAlmostEqual(mushroom["math"]["base"], 1900.0, places=6)

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
    def test_hourly_mode_uses_expected_cycle_formula(self, _mock_prices):
        plots = 2
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
            mutation_chance=0.25,
            per_harvest_cost=5.0,
        )

        lonelily = next((m for m in result["leaderboard"] if m["mutationName"] == "Lonelily"), None)
        self.assertIsNotNone(lonelily)

        expected_cycles = (1.0 / LONELILY_METRIC_SPAWN_CHANCE) + lonelily["breakdown"]["growth_stages"]
        expected_hours = expected_cycles * result["metadata"]["cycle_time_hours"]
        self.assertAlmostEqual(lonelily["hourly"]["expected_cycles"], expected_cycles, places=6)
        self.assertAlmostEqual(lonelily["hourly"]["profit_per_hour_selected"], lonelily["profit"] / expected_hours, places=6)


if __name__ == "__main__":
    unittest.main()
