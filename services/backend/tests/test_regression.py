import unittest

from tests.support import SCENARIOS, run_api_scenario


class RegressionScenarioTests(unittest.TestCase):
    def test_representative_diseases_finish_within_expected_rank_window(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario.name):
                result = run_api_scenario(scenario)
                self.assertLessEqual(result.final_rank, scenario.expected_max_rank)
                self.assertGreater(len(result.steps), 0)
                self.assertTrue(result.seed_symptom)

    def test_seed_step_improves_over_prior_for_each_scenario(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario.name):
                result = run_api_scenario(scenario)
                self.assertLessEqual(result.steps[0].target_rank, result.prior_rank)
