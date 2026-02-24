import unittest
import math
from unittest.mock import patch

from api.index import (
    DEFAULT_SPECIAL_MULTIPLIER_BY_MUTATION,
    MANUAL_DATA,
    compute_break_even_cycles,
    format_break_even_cycles,
    get_leaderboard,
)
from mut_calc import compute_profit_rates


class LeaderboardTests(unittest.TestCase):
    def test_break_even_cycles_known_case(self):
        cycles = compute_break_even_cycles(200_000.0, 10_000.0)
        self.assertEqual(cycles, 20.0)
        self.assertEqual(format_break_even_cycles(cycles), "20")

    def test_break_even_cycles_non_positive_rate_is_never(self):
        self.assertIsNone(compute_break_even_cycles(200_000.0, 0.0))
        self.assertIsNone(compute_break_even_cycles(200_000.0, -1.0))
        self.assertEqual(format_break_even_cycles(None), "Never")
        self.assertEqual(format_break_even_cycles(0.0), "Never")
        self.assertEqual(format_break_even_cycles(-2.0), "Never")

    def test_break_even_cycles_non_finite_inputs_are_never(self):
        self.assertIsNone(compute_break_even_cycles(float("nan"), 10_000.0))
        self.assertIsNone(compute_break_even_cycles(200_000.0, float("nan")))
        self.assertIsNone(compute_break_even_cycles(float("inf"), 10_000.0))
        self.assertIsNone(compute_break_even_cycles(200_000.0, float("inf")))
        self.assertEqual(format_break_even_cycles(float("nan")), "Never")
        self.assertEqual(format_break_even_cycles(float("inf")), "Never")

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_break_even_display_is_never_for_non_positive_cycle_value(self, _mock_prices):
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

        checked_any = False
        for mutation in result["leaderboard"]:
            cycle_value = mutation["profit_per_cycle"]
            if not math.isfinite(cycle_value) or cycle_value <= 0:
                checked_any = True
                self.assertEqual(mutation["break_even_cycles_display"], "Never")
                self.assertIsNone(mutation["break_even_cycles"])

        if not checked_any:
            self.skipTest("No non-positive cycle values in fixture to validate 'Never' display.")

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
    def test_profit_per_cycle_uses_renewal_model_output(self, _mock_prices):
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
            model_cycle = mutation["hourly"]["profit_per_cycle"]
            model_hour = mutation["hourly"]["profit_per_hour"]
            cycle_time_hours = mutation["hourly"]["tau_hours"]

            self.assertAlmostEqual(mutation["profit_per_cycle"], model_cycle, places=6)
            self.assertAlmostEqual(mutation["profit_per_hour"], model_hour, places=6)
            self.assertAlmostEqual(
                mutation["profit_per_hour"],
                mutation["profit_per_cycle"] / cycle_time_hours,
                places=6,
            )

    @patch("api.index.get_bazaar_prices", return_value={})
    def test_profit_per_cycle_and_per_harvest_are_distinct_metrics(self, _mock_prices):
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

        any_diff = any(
            abs(mutation["profit_per_cycle"] - mutation["profit"]) > 1e-9
            for mutation in result["leaderboard"]
        )
        self.assertTrue(any_diff)

    @patch("api.index.get_bazaar_prices", return_value={"Magic Jellybean": {"buyPrice": 1000, "sellPrice": 900}})
    def test_profit_per_cycle_includes_harvest_multiplier_in_v_net(self, _mock_prices):
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

        self.assertAlmostEqual(jellybean["profit_per_cycle"], expected["profit_per_cycle"], places=6)

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
