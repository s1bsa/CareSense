import unittest
from unittest import mock

from fastapi.testclient import TestClient

from src.api import routes as route_module
from tests.support import (
    DEFAULT_SESSION_ID,
    PROBS,
    QUICK_OPTIONS,
    assert_valid_response_shape,
    build_top10,
    deduction_backend,
    reset_state,
)


class ApiBehaviorTests(unittest.TestCase):
    def setUp(self):
        reset_state()
        self.client = TestClient(deduction_backend.app)

    def tearDown(self):
        self.client.close()

    def test_known_extracted_symptom_returns_ranked_payload(self):
        response = self.client.post(
            "/api/next",
            json={"extractedSymptoms": ["suprapubic pain"], "choice": None},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        assert_valid_response_shape(self, payload)
        self.assertEqual(payload["sessionId"], DEFAULT_SESSION_ID)
        self.assertEqual(len(payload["top10"]), 10)
        self.assertEqual(payload["quickOptions"], QUICK_OPTIONS)

        top_scores = [row["score"] for row in payload["top10"]]
        self.assertEqual(top_scores, sorted(top_scores, reverse=True))
        self.assertNotEqual(payload["nextQuestionId"], "done")

    def test_quick_option_advances_without_reasking_the_same_symptom(self):
        first = self.client.post(
            "/api/next",
            json={"extractedSymptoms": ["suprapubic pain"], "choice": None},
        ).json()
        asked_symptom = first["nextQuestionId"]

        second = self.client.post(
            "/api/next",
            json={"extractedSymptoms": [], "choice": "yes"},
        ).json()

        assert_valid_response_shape(self, second)
        self.assertNotEqual(second["nextQuestionId"], asked_symptom)
        self.assertNotEqual(second["nextQuestionId"], "suprapubic pain")

    def test_unknown_extracted_symptom_is_ignored_but_response_is_valid(self):
        response = self.client.post(
            "/api/next",
            json={"extractedSymptoms": ["definitely-not-a-real-symptom"], "choice": None},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        assert_valid_response_shape(self, payload)
        self.assertEqual(len(payload["top10"]), 10)
        self.assertEqual(payload["quickOptions"], QUICK_OPTIONS)
        self.assertIn(payload["nextQuestionId"], {"done", *PROBS.columns})

    def test_yes_without_seed_still_produces_valid_response(self):
        response = self.client.post("/api/next", json={"extractedSymptoms": [], "choice": "yes"})
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        assert_valid_response_shape(self, payload)
        self.assertEqual(len(payload["top10"]), 10)
        self.assertIn(payload["nextQuestionId"], {"done", *PROBS.columns})

    def test_response_top10_matches_internal_ranking(self):
        payload = self.client.post(
            "/api/next",
            json={"extractedSymptoms": ["suprapubic pain"], "choice": None},
        ).json()
        internal_top10 = build_top10()

        self.assertEqual(
            [row["disease"] for row in payload["top10"]],
            [row["disease"] for row in internal_top10],
        )

    def test_done_response_is_returned_when_no_more_candidates_exist(self):
        with mock.patch.object(route_module, "suggestSymptoms", return_value=[]):
            response = self.client.post(
                "/api/next",
                json={"extractedSymptoms": ["suprapubic pain"], "choice": None},
            )
            payload = response.json()

        self.assertEqual(payload["nextQuestionId"], "done")
        self.assertEqual(payload["nextQuestionText"], "Diagnosis complete.")

    def test_maybe_choice_tracks_unconfirmed_symptoms(self):
        first = self.client.post(
            "/api/next",
            json={"extractedSymptoms": ["suprapubic pain"], "choice": None},
        ).json()

        second = self.client.post(
            "/api/next",
            json={"extractedSymptoms": [], "choice": "maybe"},
        ).json()

        assert_valid_response_shape(self, second)
        self.assertIn(first["nextQuestionId"], route_module.unconfirmed_symptoms)
