from __future__ import annotations

import importlib
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from src.utils.config_loader import settings

settings["data"]["directory"] = str(BACKEND_DIR / "data")

from src.api import routes as route_module
from src.services.scoring import scoreDiseases, suggestSymptoms
from src.utils.data_loader import load_data

deduction_backend = importlib.import_module("src.main")


def reset_state() -> tuple[Any, Any, Any]:
    probs, priors, beliefs = load_data()
    route_module.init_routes(probs, beliefs.copy())
    deduction_backend.probs = probs
    deduction_backend.priors = priors
    deduction_backend.beliefs = beliefs
    return probs, priors, beliefs


def get_current_state() -> tuple[Any, Any, Any]:
    return route_module.probs, deduction_backend.priors, route_module.beliefs


def get_ranked_diseases(current_beliefs=None):
    beliefs = route_module.beliefs if current_beliefs is None else current_beliefs
    shifted = beliefs - beliefs.max()
    percentages = np.exp(shifted)
    return percentages / percentages.sum()


def build_top10(current_beliefs=None):
    ranked = get_ranked_diseases(current_beliefs).sort_values(ascending=False)
    return [
        {"disease": disease, "score": float(score)}
        for disease, score in ranked.head(settings["logic"]["n_diseases_output"]).items()
    ]


PROBS, PRIORS, _ = reset_state()
QUICK_OPTIONS = list(settings["logic"]["quick_options"])
DEFAULT_SESSION_ID = settings["logic"]["default_session_id"]

SYMPTOM_BASELINE = PROBS.mean(axis=0)
PRIOR_RANKING = PRIORS.sort_values(ascending=False)
PRIOR_RANK_MAP = {disease: index + 1 for index, disease in enumerate(PRIOR_RANKING.index)}


@dataclass(frozen=True)
class Scenario:
    name: str
    target_disease: str
    expected_max_rank: int
    steps: int = 4
    threshold: float = 0.5
    min_seed_probability: float = 0.45


@dataclass
class ScenarioStepResult:
    step_index: int
    evaluated_symptom: str
    submitted_answer: str
    next_question_id: str
    next_question_text: str
    target_rank: int
    target_score: float
    top_disease: str
    top_score: float


@dataclass
class ScenarioResult:
    scenario_name: str
    target_disease: str
    prior_rank: int
    seed_symptom: str
    expected_max_rank: int
    final_rank: int
    final_score: float
    top_disease: str
    top_score: float
    passed: bool
    steps: list[ScenarioStepResult]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SCENARIOS = [
    Scenario("Common cold trajectory", "common cold", expected_max_rank=3),
    Scenario("Asthma trajectory", "asthma", expected_max_rank=3),
    Scenario("Appendicitis trajectory", "appendicitis", expected_max_rank=2),
    Scenario("Migraine trajectory", "migraine", expected_max_rank=5),
    Scenario("UTI trajectory", "urinary tract infection", expected_max_rank=2),
    Scenario("Acute bronchitis trajectory", "acute bronchitis", expected_max_rank=2),
    Scenario("Acute sinusitis trajectory", "acute sinusitis", expected_max_rank=5),
    Scenario("Diverticulitis trajectory", "diverticulitis", expected_max_rank=2),
    Scenario("Gout trajectory", "gout", expected_max_rank=2),
    Scenario("Esophagitis trajectory", "esophagitis", expected_max_rank=5),
    Scenario("Anxiety trajectory", "anxiety", expected_max_rank=2),
    Scenario("Cystitis trajectory", "cystitis", expected_max_rank=2),
]


def choose_seed_symptom(target_disease: str, min_seed_probability: float = 0.45) -> str:
    target_row = PROBS.loc[target_disease]
    eligible = target_row[target_row >= min_seed_probability]

    if eligible.empty:
        eligible = target_row.sort_values(ascending=False).head(25)

    discriminative = (eligible / SYMPTOM_BASELINE.loc[eligible.index]).sort_values(ascending=False)
    return str(discriminative.index[0])


def answer_for_target(target_disease: str, symptom: str, threshold: float) -> str:
    probability = float(PROBS.loc[target_disease, symptom])
    return "yes" if probability >= threshold else "no"


def get_target_snapshot(target_disease: str) -> tuple[int, float, str, float]:
    ranking = get_ranked_diseases().sort_values(ascending=False)
    target_rank = int(ranking.index.get_loc(target_disease)) + 1
    target_score = float(ranking.loc[target_disease])
    top_disease = str(ranking.index[0])
    top_score = float(ranking.iloc[0])
    return target_rank, target_score, top_disease, top_score


def assert_valid_response_shape(testcase, payload: dict[str, Any]) -> None:
    testcase.assertIn("sessionId", payload)
    testcase.assertIn("top10", payload)
    testcase.assertIn("nextQuestionId", payload)
    testcase.assertIn("nextQuestionText", payload)
    testcase.assertIn("quickOptions", payload)
    testcase.assertIn("end", payload)
    testcase.assertIn("presentSymptoms", payload)
    testcase.assertIn("absentSymptoms", payload)
    testcase.assertIn("unconfirmedSymptoms", payload)
    testcase.assertIsInstance(payload["top10"], list)
    testcase.assertIsInstance(payload["quickOptions"], list)
    testcase.assertIsInstance(payload["presentSymptoms"], list)
    testcase.assertIsInstance(payload["absentSymptoms"], list)
    testcase.assertIsInstance(payload["unconfirmedSymptoms"], list)


def run_api_scenario(
    scenario: Scenario,
    client: TestClient | None = None,
) -> ScenarioResult:
    owns_client = client is None
    if client is None:
        client = TestClient(deduction_backend.app)

    reset_state()
    seed_symptom = choose_seed_symptom(
        scenario.target_disease,
        min_seed_probability=scenario.min_seed_probability,
    )

    try:
        response = client.post(
            "/api/next",
            json={"extractedSymptoms": [seed_symptom], "choice": None},
        )
        response.raise_for_status()
        payload = response.json()

        target_rank, target_score, top_disease, top_score = get_target_snapshot(
            scenario.target_disease
        )

        steps = [
            ScenarioStepResult(
                step_index=1,
                evaluated_symptom=seed_symptom,
                submitted_answer=seed_symptom,
                next_question_id=str(payload["nextQuestionId"]),
                next_question_text=str(payload["nextQuestionText"]),
                target_rank=target_rank,
                target_score=target_score,
                top_disease=top_disease,
                top_score=top_score,
            )
        ]

        for step_index in range(2, scenario.steps + 1):
            if payload.get("end"):
                break

            symptom = str(payload["nextQuestionId"])
            if symptom == "done":
                break

            answer = answer_for_target(scenario.target_disease, symptom, scenario.threshold)
            response = client.post(
                "/api/next",
                json={"extractedSymptoms": [], "choice": answer},
            )
            response.raise_for_status()
            payload = response.json()

            target_rank, target_score, top_disease, top_score = get_target_snapshot(
                scenario.target_disease
            )

            steps.append(
                ScenarioStepResult(
                    step_index=step_index,
                    evaluated_symptom=symptom,
                    submitted_answer=answer,
                    next_question_id=str(payload["nextQuestionId"]),
                    next_question_text=str(payload["nextQuestionText"]),
                    target_rank=target_rank,
                    target_score=target_score,
                    top_disease=top_disease,
                    top_score=top_score,
                )
            )
    finally:
        if owns_client:
            client.close()

    final_step = steps[-1]
    return ScenarioResult(
        scenario_name=scenario.name,
        target_disease=scenario.target_disease,
        prior_rank=int(PRIOR_RANK_MAP[scenario.target_disease]),
        seed_symptom=seed_symptom,
        expected_max_rank=scenario.expected_max_rank,
        final_rank=int(final_step.target_rank),
        final_score=float(final_step.target_score),
        top_disease=final_step.top_disease,
        top_score=float(final_step.top_score),
        passed=final_step.target_rank <= scenario.expected_max_rank,
        steps=steps,
    )


def run_all_scenarios() -> list[ScenarioResult]:
    with TestClient(deduction_backend.app) as client:
        return [run_api_scenario(scenario, client=client) for scenario in SCENARIOS]
