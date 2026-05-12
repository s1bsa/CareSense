from fastapi import APIRouter, Request
import numpy as np
from src.services.scoring import scoreDiseases, suggestSymptoms
from src.utils.config_loader import settings
from src.utils.data_loader import load_data

router = APIRouter()

probs = None
beliefs = None
symptoms = set()
nonsymptoms = set()
unconfirmed_symptoms = set()
question_count = 0
last_suggested_symptom = ""


def init_routes(p, b):
    global probs, beliefs, symptoms, nonsymptoms, unconfirmed_symptoms, question_count, last_suggested_symptom
    probs = p
    beliefs = b
    symptoms = set()
    nonsymptoms = set()
    unconfirmed_symptoms = set()
    question_count = 0
    last_suggested_symptom = ""


def _normalize_extracted_symptoms(value):
    if not isinstance(value, list):
        return []
    return [symptom for symptom in value if isinstance(symptom, str)]


def _score_last_suggested_symptom(is_present):
    global beliefs
    beliefs = scoreDiseases(beliefs, probs, last_suggested_symptom, is_present)


def _build_ranked_diseases(n_top):
    shifted = beliefs - beliefs.max()
    percentages = np.exp(shifted)
    percentages = percentages / percentages.sum()
    return percentages.sort_values(ascending=False).head(n_top)


@router.post("/next")
async def next_symptom(request: Request):
    global beliefs, symptoms, nonsymptoms, unconfirmed_symptoms, question_count, last_suggested_symptom

    data = await request.json()
    extracted = _normalize_extracted_symptoms(data.get("extractedSymptoms", []))
    choice = data.get("choice")

    question_count += 1

    quick_opts = settings['logic']['quick_options']
    session_id = settings['logic']['default_session_id']
    n_top = settings['logic']['n_diseases_output']

    #handle extractions
    for symptom in extracted:
        if symptom in probs.columns and symptom not in symptoms:
            beliefs = scoreDiseases(beliefs, probs, symptom, True)
            symptoms.add(symptom)

    #handle button clicks
    if choice in quick_opts and last_suggested_symptom:
        if choice == "yes":
            _score_last_suggested_symptom(True)
            symptoms.add(last_suggested_symptom)
        elif choice == "no":
            _score_last_suggested_symptom(False)
            nonsymptoms.add(last_suggested_symptom)
        elif choice == "maybe":
            unconfirmed_symptoms.add(last_suggested_symptom)

    recommendations = suggestSymptoms(beliefs, probs, symptoms, nonsymptoms, unconfirmed_symptoms)
    if recommendations:
        next_symptom_name = recommendations[0]
        last_suggested_symptom = next_symptom_name
        next_question_text = f"Do you have {next_symptom_name}?"
        next_question_id = next_symptom_name
    else:
        next_question_text = "Diagnosis complete."
        next_question_id = "done"

    top10_series = _build_ranked_diseases(n_top)

    top10 = [
        {"disease": disease, "score": float(score)}
        for disease, score in top10_series.items()
    ]
        
    top_score = float(top10_series.iloc[0]) if len(top10_series) > 0 else 0.0
    
    #stopping condition, sets 'end' flag to true and returns present symptoms
    end = top_score > settings['logic']['confidence_threshold'] or question_count >= settings['logic']['max_questions_asked']

    return {
        "sessionId": session_id,
        "top10": top10,
        "nextQuestionId": next_question_id,
        "nextQuestionText": next_question_text,
        "quickOptions": quick_opts,
        "assistantNote": None,
        "end": end,
        "diagnosed": not question_count >= settings['logic']['max_questions_asked'],
        "presentSymptoms": list(symptoms) if end else [],
        "absentSymptoms": list(nonsymptoms) if end else [],
        "unconfirmedSymptoms": list(unconfirmed_symptoms) if end else []
    }


#resets beliefs and session
@router.post("/reset")
async def reset_beliefs(request: Request):
    global beliefs
    
    probs, _priors, beliefs = load_data()
    init_routes(probs, beliefs)

    return {"status": "reset", "message": "Session reset successfully"}