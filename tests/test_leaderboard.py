import unittest
from unittest.mock import patch

from api.index import (
    DEFAULT_SPECIAL_MULTIPLIER_BY_MUTATION,
    MANUAL_DATA,
    get_leaderboard,
)
from mut_calc import compute_profit_rates


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
    def test_growth_stages_allow_zero_for_instant_mutations(self, _mock_prices):
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
        self.assertEqual(veil["breakdown"]["growth_stages"], 0)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_profit_per_hour_uses_renewal_model_output(self, _mock_prices):
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
            model_hour = mutation["hourly"]["profit_per_hour"]

            self.assertAlmostEqual(mutation["profit_per_hour"], model_hour, places=6)

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
            if growth_stages > 0:
                self.assertAlmostEqual(
                    mutation["profit_per_growth_cycle"],
                    mutation["profit"] / growth_stages,
                    places=6,
                )
            else:
                self.assertIsNone(mutation["profit_per_growth_cycle"])
            self.assertIn("warning_messages", mutation)
            self.assertNotIn("profit_per_cycle", mutation)
            self.assertNotIn("break_even_cycles", mutation)
            self.assertNotIn("break_even_cycles_display", mutation)
            self.assertNotIn("profit_per_cycle", mutation["hourly"])
            self.assertNotIn("break_even_cycles", mutation["hourly"])
            self.assertNotIn("break_even_cycles_display", mutation["hourly"])

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
        self.assertTrue(any("Magic Jellybean takes much longer" in msg for msg in messages_by_name["Magic Jellybean"]))
        self.assertTrue(any("raw multiplier there is 60x" in msg for msg in messages_by_name["All-in Aloe"]))

    @patch("api.index.get_bazaar_prices", return_value={"Magic Jellybean": {"buyPrice": 1000, "sellPrice": 900}})
    def test_profit_per_hour_includes_harvest_multiplier_in_v_net(self, _mock_prices):
        plots = 1
        result = get_leaderboard(
            plots=plots,
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

        jelly_data = MANUAL_DATA["Magic Jellybean"]
        special = float(
            jelly_data.get(
                "effective_special_multiplier",
                jelly_data.get(
                    "special_multiplier",
                    DEFAULT_SPECIAL_MULTIPLIER_BY_MUTATION.get("Magic Jellybean", 1.0),
                ),
            )
        )

        cycle_time_hours = result["metadata"]["cycle_time_hours"]
        expected = compute_profit_rates({
            "m": plots,
            "x": jellybean["breakdown"]["base_limit"],
            "p": jellybean["hourly"]["p"],
            "tau": cycle_time_hours,
            "g": jellybean["breakdown"]["growth_stages"],
            "v": jellybean["mut_price"] * special,
            "per_harvest_cost": 50.0,
        })

        self.assertAlmostEqual(jellybean["profit_per_hour"], expected["profit_per_hour"], places=6)

    @patch("api.index.get_bazaar_prices", return_value={"All-in Aloe": {"buyPrice": 1_250_000, "sellPrice": 1_000_000}})
    def test_all_in_aloe_profit_per_hour_uses_effective_special_multiplier(self, _mock_prices):
        plots = 1
        result = get_leaderboard(
            plots=plots,
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

        aloe_data = MANUAL_DATA["All-in Aloe"]
        special = float(
            aloe_data.get(
                "effective_special_multiplier",
                aloe_data.get(
                    "special_multiplier",
                    DEFAULT_SPECIAL_MULTIPLIER_BY_MUTATION.get("All-in Aloe", 1.0),
                ),
            )
        )

        cycle_time_hours = result["metadata"]["cycle_time_hours"]
        base_inputs = {
            "m": plots,
            "x": aloe["breakdown"]["base_limit"],
            "p": aloe["hourly"]["p"],
            "tau": cycle_time_hours,
            "g": aloe["breakdown"]["growth_stages"],
            "per_harvest_cost": 0.0,
        }
        expected_with_special = compute_profit_rates({
            **base_inputs,
            "v": aloe["mut_price"] * special,
        })
        expected_without_special = compute_profit_rates({
            **base_inputs,
            "v": aloe["mut_price"],
        })

        self.assertAlmostEqual(aloe["profit_per_hour"], expected_with_special["profit_per_hour"], places=6)
        self.assertNotAlmostEqual(aloe["profit_per_hour"], expected_without_special["profit_per_hour"], places=6)

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_lonelily_override_affects_profit_mode_mutation_count(self, _mock_prices):
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
        # 25 per plot * 3 plots * 0.02 chance over 1 cycle
        self.assertAlmostEqual(lonelily_yield["amount"], 1.5, places=6)
        self.assertAlmostEqual(lonelily["profit_per_growth_cycle"], lonelily["profit"], places=6)

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
    def test_hourly_mode_uses_renewal_model_formula(self, _mock_prices):
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

        cycle_time_hours = result["metadata"]["cycle_time_hours"]
        expected = compute_profit_rates({
            "m": plots,
            "x": lonelily["breakdown"]["base_limit"],
            "p": lonelily["hourly"]["p"],
            "tau": cycle_time_hours,
            "g": lonelily["breakdown"]["growth_stages"],
            "v": lonelily["mut_price"],
            "per_harvest_cost": 5.0,
        })

        self.assertAlmostEqual(lonelily["hourly"]["profit_per_hour_selected"], expected["profit_per_hour"], places=6)


if __name__ == "__main__":
    unittest.main()
