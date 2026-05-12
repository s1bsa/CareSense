import unittest

import numpy as np
import pandas as pd

from src.services.scoring import scoreDiseases, suggestSymptoms
from tests.support import PROBS, PRIORS, build_top10, get_ranked_diseases, reset_state


class EngineLogicTests(unittest.TestCase):
    def setUp(self):
        reset_state()

    def test_score_diseases_applies_positive_log_update(self):
        beliefs = np.log(PRIORS.copy())
        symptom = "fever"

        updated = scoreDiseases(
            beliefs.copy(),
            PROBS,
            symptom,
            True,
        )
        expected = beliefs + np.log(PROBS[symptom])

        pd.testing.assert_series_equal(updated, expected)

    def test_score_diseases_applies_negative_log_update(self):
        beliefs = np.log(PRIORS.copy())
        symptom = "fever"

        updated = scoreDiseases(
            beliefs.copy(),
            PROBS,
            symptom,
            False,
        )
        expected = beliefs + np.log(1 - PROBS[symptom])

        pd.testing.assert_series_equal(updated, expected)

    def test_suggest_symptoms_excludes_already_asked_entries(self):
        beliefs = np.log(PRIORS.copy())
        asked = {"fever", "cough"}

        suggestions = suggestSymptoms(
            beliefs,
            PROBS,
            asked,
            set(),
            set(),
        )

        self.assertLessEqual(len(suggestions), 3)
        self.assertEqual(len(suggestions), len(set(suggestions)))
        self.assertTrue(set(suggestions).isdisjoint(asked))

    def test_get_ranked_diseases_returns_normalized_distribution(self):
        ranked = get_ranked_diseases(np.log(PRIORS.copy()))

        self.assertAlmostEqual(float(ranked.sum()), 1.0, places=9)
        self.assertTrue((ranked > 0).all())

    def test_build_top10_is_sorted_descending(self):
        top10 = build_top10(np.log(PRIORS.copy()))
        scores = [row["score"] for row in top10]

        self.assertEqual(len(top10), 10)
        self.assertEqual(scores, sorted(scores, reverse=True))
