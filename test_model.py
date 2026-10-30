"""Automated tests for model.py  (run:  python -m unittest -v)."""
import unittest
from dataclasses import replace

import numpy as np

from model import (Scenario, Params, default_scenarios, validate_scenarios,
                   validate_params, evaluate_scenario, expected_summary,
                   expected_net_value, expected_demand, expected_value_grid,
                   optimize, optimize_bruteforce, monte_carlo,
                   sensitivity_costs, sensitivity_one_at_a_time,
                   scenarios_to_dataframe, scenarios_from_dataframe)


def tiny_example():
    """Two-scenario example that can be solved by hand.

    Scenario A: p=0.5, 1 general, 1 emergency (total demand 2)
    Scenario B: p=0.5, 3 general, 1 emergency (total demand 4)
    benefit emergency=10, general=4; cost bed=1.0, staff=0.5 (1.5 per unit of C)
    Marginal value of the k-th unit of capacity (B=S=k):
      k=1: emergency in both        -> 10      > 1.5  (add)
      k=2: general in A and B       -> 0.5*4+0.5*4 = 4 > 1.5 (add)
      k=3: general only in B        -> 0.5*4 = 2       > 1.5 (add)
      k=4: general only in B        -> 2               > 1.5 (add)
      k=5: nobody needs it          -> 0       < 1.5   (stop)
    So optimum is B=S=4.  Benefit: A=14, B=22 -> E=18; cost=4*1.5=6; EV=12.
    """
    sc = [Scenario("A", 0.5, 1, 1), Scenario("B", 0.5, 3, 1)]
    p = Params(benefit_general=4, benefit_emergency=10, cost_bed=1.0,
               cost_staff=0.5, max_beds=6, max_staff=6)
    return sc, p


class TestValidation(unittest.TestCase):
    def test_valid_default_scenarios(self):
        validate_scenarios(default_scenarios())  # should not raise

    def test_probabilities_sum_to_one(self):
        self.assertAlmostEqual(sum(s.probability for s in default_scenarios()), 1.0)

    def test_probabilities_not_summing_to_one(self):
        bad = [Scenario("a", 0.5, 1, 1), Scenario("b", 0.4, 2, 2)]
        with self.assertRaises(ValueError):
            validate_scenarios(bad)

    def test_negative_probability(self):
        bad = [Scenario("a", -0.2, 1, 1), Scenario("b", 1.2, 2, 2)]
        with self.assertRaises(ValueError):
            validate_scenarios(bad)

    def test_negative_demand(self):
        with self.assertRaises(ValueError):
            validate_scenarios([Scenario("a", 1.0, -1, 5)])
        with self.assertRaises(ValueError):
            validate_scenarios([Scenario("a", 1.0, 5, -1)])

    def test_empty_scenarios(self):
        with self.assertRaises(ValueError):
            validate_scenarios([])

    def test_negative_params(self):
        with self.assertRaises(ValueError):
            validate_params(Params(cost_bed=-1))
        with self.assertRaises(ValueError):
            validate_params(Params(max_beds=-1))


class TestScenarioEvaluation(unittest.TestCase):
    def setUp(self):
        self.p = Params()
        self.normal = Scenario("Normal", 0.5, 60, 12)

    def test_effective_capacity_is_min(self):
        r = evaluate_scenario(50, 30, self.normal, self.p)
        self.assertEqual(r["effective_capacity"], 30)

    def test_emergency_first_priority(self):
        # capacity 10 < 12 emergency: all capacity goes to emergency patients
        r = evaluate_scenario(10, 10, self.normal, self.p)
        self.assertEqual(r["emergency_served"], 10)
        self.assertEqual(r["general_served"], 0)
        self.assertEqual(r["emergency_unserved"], 2)
        self.assertEqual(r["general_unserved"], 60)

    def test_leftover_capacity_serves_general(self):
        r = evaluate_scenario(30, 30, self.normal, self.p)
        self.assertEqual(r["emergency_served"], 12)
        self.assertEqual(r["general_served"], 18)

    def test_full_service_with_excess_capacity(self):
        r = evaluate_scenario(100, 100, self.normal, self.p)
        self.assertEqual(r["total_unserved"], 0)
        self.assertEqual(r["service_rate"], 1.0)

    def test_benefit_and_cost_calculation(self):
        # B=30, S=20 -> C=20: 12 emergency + 8 general
        r = evaluate_scenario(30, 20, self.normal, self.p)
        self.assertEqual(r["benefit"], 12 * 2500 + 8 * 1000)       # 38000
        self.assertEqual(r["cost"], 30 * 250 + 20 * 180)            # 11100
        self.assertEqual(r["net_value"], 38000 - 11100)

    def test_zero_capacity_boundary(self):
        r = evaluate_scenario(0, 0, self.normal, self.p)
        self.assertEqual(r["total_served"], 0)
        self.assertEqual(r["net_value"], 0)
        self.assertEqual(r["service_rate"], 0.0)

    def test_one_resource_zero_means_no_service(self):
        self.assertEqual(evaluate_scenario(50, 0, self.normal, self.p)["total_served"], 0)
        self.assertEqual(evaluate_scenario(0, 50, self.normal, self.p)["total_served"], 0)

    def test_negative_allocation_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_scenario(-1, 5, self.normal, self.p)

    def test_capacity_exactly_equals_total_demand(self):
        r = evaluate_scenario(72, 72, self.normal, self.p)
        self.assertEqual(r["total_unserved"], 0)


class TestExpectedValue(unittest.TestCase):
    def test_hand_computed_default_allocation(self):
        # Hand calculation for B=S=72 (see README / report):
        # Low: 8*2500+40*1000=60000; Normal: 12*2500+60*1000=90000;
        # High: 20*2500+52*1000=102000; cost=72*430=30960
        # E[benefit]=0.2*60000+0.5*90000+0.3*102000=87600; EV=87600-30960=56640
        r = expected_summary(72, 72, default_scenarios(), Params())
        self.assertAlmostEqual(r["expected_benefit"], 87600.0)
        self.assertAlmostEqual(r["resource_cost"], 30960.0)
        self.assertAlmostEqual(r["expected_net_value"], 56640.0)

    def test_expected_demand(self):
        d = expected_demand(default_scenarios())
        self.assertAlmostEqual(d["general"], 63.5)
        self.assertAlmostEqual(d["emergency"], 13.6)
        self.assertAlmostEqual(d["total"], 77.1)

    def test_expected_equals_probability_weighted_sum(self):
        sc, p = default_scenarios(), Params()
        manual = sum(s.probability * evaluate_scenario(60, 55, s, p)["net_value"] for s in sc)
        self.assertAlmostEqual(expected_net_value(60, 55, sc, p), manual)

    def test_vectorised_grid_matches_scalar_function(self):
        sc, p = default_scenarios(), Params(max_beds=40, max_staff=40)
        grid = expected_value_grid(sc, p)
        for b, s in [(0, 0), (10, 25), (25, 10), (40, 40), (17, 17)]:
            self.assertAlmostEqual(grid[b, s], expected_net_value(b, s, sc, p))


class TestOptimization(unittest.TestCase):
    def test_hand_solvable_example(self):
        sc, p = tiny_example()
        r = optimize(sc, p)
        self.assertEqual((r["beds"], r["staff"]), (4, 4))
        self.assertAlmostEqual(r["expected_net_value"], 12.0)

    def test_matches_bruteforce_default(self):
        sc, p = default_scenarios(), Params(max_beds=100, max_staff=100)
        a, b = optimize(sc, p), optimize_bruteforce(sc, p)
        self.assertEqual((a["beds"], a["staff"]), (b["beds"], b["staff"]))
        self.assertAlmostEqual(a["expected_net_value"], b["expected_net_value"])

    def test_default_result_is_global_optimum(self):
        sc, p = default_scenarios(), Params()
        r = optimize(sc, p)
        grid = expected_value_grid(sc, p)
        self.assertAlmostEqual(r["expected_net_value"], grid.max())
        # independent marginal-analysis check: unit k adds 800 up to k=72 (>430), 300 after (<430)
        self.assertEqual(r["effective_capacity"], 72)

    def test_resource_bounds_respected(self):
        sc = default_scenarios()
        p = Params(max_beds=30, max_staff=50)
        r = optimize(sc, p)
        self.assertLessEqual(r["beds"], 30)
        self.assertLessEqual(r["staff"], 50)
        self.assertGreaterEqual(r["beds"], 0)
        self.assertEqual(r["beds"], 30)      # bound is binding
        self.assertEqual(r["staff"], 30)     # staff above beds would be wasted cost

    def test_zero_capacity_limit(self):
        r = optimize(default_scenarios(), Params(max_beds=0, max_staff=0))
        self.assertEqual((r["beds"], r["staff"]), (0, 0))
        self.assertAlmostEqual(r["expected_net_value"], 0.0)

    def test_resources_too_expensive_gives_zero(self):
        r = optimize(default_scenarios(), Params(cost_bed=5000, cost_staff=5000))
        self.assertEqual(r["effective_capacity"], 0)

    def test_never_buys_unmatched_resources(self):
        r = optimize(default_scenarios(), Params())
        self.assertEqual(r["beds"], r["staff"])

    def test_invalid_scenarios_rejected_by_optimizer(self):
        with self.assertRaises(ValueError):
            optimize([Scenario("a", 0.9, 1, 1)], Params())

    def test_changing_probabilities_changes_optimum(self):
        low = [Scenario("L", 0.9, 40, 8), Scenario("H", 0.1, 85, 20)]
        high = [Scenario("L", 0.1, 40, 8), Scenario("H", 0.9, 85, 20)]
        p = Params()
        self.assertLess(optimize(low, p)["effective_capacity"],
                        optimize(high, p)["effective_capacity"])


class TestMonteCarlo(unittest.TestCase):
    def setUp(self):
        self.sc, self.p = default_scenarios(), Params()

    def test_reproducible_with_same_seed(self):
        a = monte_carlo(72, 72, self.sc, self.p, 5000, seed=7)
        b = monte_carlo(72, 72, self.sc, self.p, 5000, seed=7)
        np.testing.assert_array_equal(a["values"], b["values"])
        self.assertEqual(a["mean"], b["mean"])

    def test_different_seed_differs(self):
        a = monte_carlo(72, 72, self.sc, self.p, 5000, seed=1)
        b = monte_carlo(72, 72, self.sc, self.p, 5000, seed=2)
        self.assertFalse(np.array_equal(a["values"], b["values"]))

    def test_mean_close_to_exact_expected_value(self):
        exact = expected_net_value(72, 72, self.sc, self.p)
        mc = monte_carlo(72, 72, self.sc, self.p, 100000, seed=42)
        self.assertAlmostEqual(mc["mean"], exact, delta=0.01 * exact)

    def test_statistics_consistent(self):
        mc = monte_carlo(72, 72, self.sc, self.p, 2000, seed=3)
        self.assertLessEqual(mc["min"], mc["p5"])
        self.assertLessEqual(mc["p5"], mc["median"])
        self.assertLessEqual(mc["median"], mc["p95"])
        self.assertLessEqual(mc["p95"], mc["max"])
        self.assertEqual(int(mc["scenario_counts"].sum()), 2000)

    def test_values_only_take_scenario_outcomes(self):
        mc = monte_carlo(72, 72, self.sc, self.p, 500, seed=5)
        allowed = {evaluate_scenario(72, 72, s, self.p)["net_value"] for s in self.sc}
        self.assertTrue(set(np.unique(mc["values"])).issubset(allowed))

    def test_invalid_n_sims(self):
        with self.assertRaises(ValueError):
            monte_carlo(10, 10, self.sc, self.p, 0)


class TestSensitivity(unittest.TestCase):
    def setUp(self):
        self.sc = default_scenarios()
        self.p = Params(max_beds=100, max_staff=100)

    def test_table_shape_and_columns(self):
        df = sensitivity_costs(self.sc, self.p, [200, 250, 300], [150, 180])
        self.assertEqual(len(df), 6)
        for col in ["bed_cost", "staff_cost", "opt_beds", "opt_staff", "expected_net_value"]:
            self.assertIn(col, df.columns)

    def test_reoptimisation_matches_direct_call(self):
        df = sensitivity_costs(self.sc, self.p, [300], [200])
        direct = optimize(self.sc, replace(self.p, cost_bed=300, cost_staff=200))
        row = df.iloc[0]
        self.assertEqual(row["opt_beds"], direct["beds"])
        self.assertAlmostEqual(row["expected_net_value"], direct["expected_net_value"])

    def test_higher_costs_never_increase_value_or_capacity(self):
        df = sensitivity_costs(self.sc, self.p, [150, 250, 400, 600], [180])
        self.assertTrue(df["expected_net_value"].is_monotonic_decreasing)
        self.assertTrue(df["effective_capacity"].is_monotonic_decreasing)

    def test_known_threshold(self):
        # per-unit cost 430 < 800 -> C=72 ; per-unit cost 900 > 800 but < 2000 -> C=12 ... check 500 and 900
        a = optimize(self.sc, replace(self.p, cost_bed=300, cost_staff=200))   # 500 < 800
        b = optimize(self.sc, replace(self.p, cost_bed=500, cost_staff=400))   # 900 > 800
        self.assertEqual(a["effective_capacity"], 72)
        self.assertLess(b["effective_capacity"], 72)

    def test_one_at_a_time_benefit(self):
        df = sensitivity_one_at_a_time(self.sc, self.p, "benefit_general", [200, 1000, 2000])
        self.assertEqual(len(df), 3)
        self.assertTrue(df["effective_capacity"].is_monotonic_increasing)


class TestCsvRoundTrip(unittest.TestCase):
    def test_round_trip(self):
        sc = default_scenarios()
        self.assertEqual(scenarios_from_dataframe(scenarios_to_dataframe(sc)), sc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
