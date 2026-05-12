import json
import re
from typing import Any, Dict, List, Optional

import pandas as pd
from rapidfuzz import fuzz, process

# Optional: only needed if you enable LLM fallback
# from openai import OpenAI


# =========================
# CONFIG
# =========================

INPUT_CSV = "diseases.csv"
OUTPUT_CSV = "diseases_with_domains.csv"
DISEASE_COLUMN = "disease_name"

USE_LLM_FALLBACK = False
OPENAI_MODEL = "gpt-4.1-mini"

ALLOWED_DOMAINS = {
    "Allergy and Immunology",
    "Cardiovascular / Cardiology",
    "Dermatology",
    "Dentistry / Oral Health",
    "Endocrinology",
    "ENT / Otolaryngology",
    "Gastroenterology / Hepatology",
    "Genetics / Genomic Medicine",
    "Hematology",
    "Infectious Diseases",
    "Musculoskeletal",
    "Nephrology",
    "Neurology",
    "Oncology",
    "Ophthalmology",
    "Psychiatry",
    "Respiratory / Pulmonology",
    "Rheumatology",
    "Urology",
    "Emergency / Trauma Medicine",
}

# Optional
# client = OpenAI() if USE_LLM_FALLBACK else None


# =========================
# MASTER DISEASE MAP
# canonical_name -> primary + secondary
# =========================

DISEASE_DOMAIN_MAP: Dict[str, Dict[str, List[str] | str]] = {
    "abdominal aortic aneurysm": {
        "primary_domain": "Cardiovascular / Cardiology",
        "secondary_domains": [],
    },
    "abdominal hernia": {
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": [],
    },
    "abscess of nose": {
        "primary_domain": "ENT / Otolaryngology",
        "secondary_domains": ["Infectious Diseases"],
    },
    "abscess of the lung": {
        "primary_domain": "Respiratory / Pulmonology",
        "secondary_domains": ["Infectious Diseases"],
    },
    "abscess of the pharynx": {
        "primary_domain": "ENT / Otolaryngology",
        "secondary_domains": ["Infectious Diseases"],
    },
    "acanthosis nigricans": {
        "primary_domain": "Dermatology",
        "secondary_domains": ["Endocrinology"],
    },
    "ascariasis": {
        "primary_domain": "Infectious Diseases",
        "secondary_domains": ["Gastroenterology / Hepatology"],
    },
    "achalasia": {
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": [],
    },
    "acne": {
        "primary_domain": "Dermatology",
        "secondary_domains": [],
    },
    "actinic keratosis": {
        "primary_domain": "Dermatology",
        "secondary_domains": ["Oncology"],
    },
    "acute bronchiolitis": {
        "primary_domain": "Respiratory / Pulmonology",
        "secondary_domains": ["Infectious Diseases"],
    },
    "acute bronchitis": {
        "primary_domain": "Respiratory / Pulmonology",
        "secondary_domains": ["Infectious Diseases"],
    },
    "acute bronchospasm": {
        "primary_domain": "Respiratory / Pulmonology",
        "secondary_domains": [],
    },
    "acute fatty liver of pregnancy": {
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": ["Endocrinology"],
    },
    "acute glaucoma": {
        "primary_domain": "Ophthalmology",
        "secondary_domains": [],
    },
    "acute kidney injury": {
        "primary_domain": "Nephrology",
        "secondary_domains": [],
    },
    "acute otitis media": {
        "primary_domain": "ENT / Otolaryngology",
        "secondary_domains": ["Infectious Diseases"],
    },
    "acute pancreatitis": {
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": [],
    },
    "acute respiratory distress syndrome": {
        "primary_domain": "Respiratory / Pulmonology",
        "secondary_domains": ["Emergency / Trauma Medicine"],
    },
    "acute sinusitis": {
        "primary_domain": "ENT / Otolaryngology",
        "secondary_domains": ["Infectious Diseases"],
    },
    "acute stress reaction": {
        "primary_domain": "Psychiatry",
        "secondary_domains": [],
    },
    "adhesive capsulitis of the shoulder": {
        "primary_domain": "Musculoskeletal",
        "secondary_domains": [],
    },
    "adjustment reaction": {
        "primary_domain": "Psychiatry",
        "secondary_domains": [],
    },
    "adrenal adenoma": {
        "primary_domain": "Endocrinology",
        "secondary_domains": ["Oncology"],
    },
    "adrenal cancer": {
        "primary_domain": "Oncology",
        "secondary_domains": ["Endocrinology"],
    },
    "alcohol abuse": {
        "primary_domain": "Psychiatry",
        "secondary_domains": [],
    },
    "alcohol intoxication": {
        "primary_domain": "Emergency / Trauma Medicine",
        "secondary_domains": ["Psychiatry"],
    },
    "alcohol withdrawal": {
        "primary_domain": "Psychiatry",
        "secondary_domains": ["Emergency / Trauma Medicine"],
    },
    "alcoholic liver disease": {
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": ["Psychiatry"],
    },
    "allergy": {
        "primary_domain": "Allergy and Immunology",
        "secondary_domains": [],
    },
    "allergy to animals": {
        "primary_domain": "Allergy and Immunology",
        "secondary_domains": [],
    },
    "alopecia": {
        "primary_domain": "Dermatology",
        "secondary_domains": [],
    },
    "alzheimers disease": {
        "primary_domain": "Neurology",
        "secondary_domains": ["Psychiatry"],
    },
    "amblyopia": {
        "primary_domain": "Ophthalmology",
        "secondary_domains": [],
    },
    "amyloidosis": {
        "primary_domain": "Hematology",
        "secondary_domains": [],
    },
    "amyotrophic lateral sclerosis": {
        "primary_domain": "Neurology",
        "secondary_domains": [],
    },
    "anal fissure": {
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": [],
    },
    "anal fistula": {
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": [],
    },
    "asthma": {
        "primary_domain": "Respiratory / Pulmonology",
        "secondary_domains": [],
    },
    "chronic obstructive pulmonary disease": {
        "primary_domain": "Respiratory / Pulmonology",
        "secondary_domains": [],
    },
    "type 2 diabetes": {
        "primary_domain": "Endocrinology",
        "secondary_domains": [],
    },
    "type 1 diabetes": {
        "primary_domain": "Endocrinology",
        "secondary_domains": [],
    },
    "diabetic retinopathy": {
        "primary_domain": "Endocrinology",
        "secondary_domains": ["Ophthalmology"],
    },
    "diabetic nephropathy": {
        "primary_domain": "Endocrinology",
        "secondary_domains": ["Nephrology"],
    },
    "hypertension": {
        "primary_domain": "Cardiovascular / Cardiology",
        "secondary_domains": ["Nephrology"],
    },
    "myocardial infarction": {
        "primary_domain": "Cardiovascular / Cardiology",
        "secondary_domains": [],
    },
    "stroke": {
        "primary_domain": "Neurology",
        "secondary_domains": ["Cardiovascular / Cardiology"],
    },
    "epilepsy": {
        "primary_domain": "Neurology",
        "secondary_domains": [],
    },
    "psoriasis": {
        "primary_domain": "Dermatology",
        "secondary_domains": ["Allergy and Immunology"],
    },
    "psoriatic arthritis": {
        "primary_domain": "Rheumatology",
        "secondary_domains": ["Dermatology"],
    },
    "systemic lupus erythematosus": {
        "primary_domain": "Rheumatology",
        "secondary_domains": ["Dermatology", "Nephrology"],
    },
    "crohn disease": {
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": ["Allergy and Immunology"],
    },
    "ulcerative colitis": {
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": ["Allergy and Immunology"],
    },
    "depression": {
        "primary_domain": "Psychiatry",
        "secondary_domains": [],
    },
    "anxiety disorder": {
        "primary_domain": "Psychiatry",
        "secondary_domains": [],
    },
    "breast cancer": {
        "primary_domain": "Oncology",
        "secondary_domains": [],
    },
    "chronic kidney disease": {
        "primary_domain": "Nephrology",
        "secondary_domains": [],
    },
    "endometriosis": {
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": [],
    },
}


# =========================
# ALIAS MAP
# alias -> canonical_name
# =========================

ALIAS_MAP = {
    "abdominal hermia": "abdominal hernia",
    "copd": "chronic obstructive pulmonary disease",
    "t2d": "type 2 diabetes",
    "type ii diabetes": "type 2 diabetes",
    "diabetes mellitus type ii": "type 2 diabetes",
    "diabetes mellitus type 2": "type 2 diabetes",
    "type i diabetes": "type 1 diabetes",
    "diabetes mellitus type i": "type 1 diabetes",
    "heart attack": "myocardial infarction",
    "mi": "myocardial infarction",
    "sle": "systemic lupus erythematosus",
    "ibd crohn": "crohn disease",
    "crohns disease": "crohn disease",
    "uc": "ulcerative colitis",
    "ckd": "chronic kidney disease",
    "high blood pressure": "hypertension",
    "cva": "stroke",
    "als": "amyotrophic lateral sclerosis",
    "ards": "acute respiratory distress syndrome",
    "alzheimers": "alzheimers disease",
    "acute kidney failure": "acute kidney injury",
}


# =========================
# ANATOMY KEYWORDS
# =========================

ANATOMY_TO_DOMAIN = {
    "pulmonary": "Respiratory / Pulmonology",
    "lung": "Respiratory / Pulmonology",
    "bronch": "Respiratory / Pulmonology",
    "trache": "Respiratory / Pulmonology",
    "pleura": "Respiratory / Pulmonology",
    "respiratory": "Respiratory / Pulmonology",
    "heart": "Cardiovascular / Cardiology",
    "cardiac": "Cardiovascular / Cardiology",
    "aortic": "Cardiovascular / Cardiology",
    "coronary": "Cardiovascular / Cardiology",
    "vascular": "Cardiovascular / Cardiology",
    "liver": "Gastroenterology / Hepatology",
    "hepatic": "Gastroenterology / Hepatology",
    "pancrea": "Gastroenterology / Hepatology",
    "intestinal": "Gastroenterology / Hepatology",
    "bowel": "Gastroenterology / Hepatology",
    "stomach": "Gastroenterology / Hepatology",
    "gastric": "Gastroenterology / Hepatology",
    "anal": "Gastroenterology / Hepatology",
    "rectal": "Gastroenterology / Hepatology",
    "esoph": "Gastroenterology / Hepatology",
    "oesoph": "Gastroenterology / Hepatology",
    "kidney": "Nephrology",
    "renal": "Nephrology",
    "nephr": "Nephrology",
    "bladder": "Urology",
    "prostate": "Urology",
    "prostatic": "Urology",
    "ureter": "Urology",
    "urethra": "Urology",
    "urinary": "Urology",
    "testicular": "Urology",
    "nose": "ENT / Otolaryngology",
    "nasal": "ENT / Otolaryngology",
    "pharynx": "ENT / Otolaryngology",
    "throat": "ENT / Otolaryngology",
    "ear": "ENT / Otolaryngology",
    "sinus": "ENT / Otolaryngology",
    "tonsil": "ENT / Otolaryngology",
    "otitis": "ENT / Otolaryngology",
    "eye": "Ophthalmology",
    "ocular": "Ophthalmology",
    "retina": "Ophthalmology",
    "cornea": "Ophthalmology",
    "glaucoma": "Ophthalmology",
    "skin": "Dermatology",
    "hair": "Dermatology",
    "nail": "Dermatology",
    "cutaneous": "Dermatology",
    "shoulder": "Musculoskeletal",
    "ankle": "Musculoskeletal",
    "arm": "Musculoskeletal",
    "wrist": "Musculoskeletal",
    "elbow": "Musculoskeletal",
    "knee": "Musculoskeletal",
    "hip": "Musculoskeletal",
    "joint": "Musculoskeletal",
    "bone": "Musculoskeletal",
    "muscle": "Musculoskeletal",
    "tendon": "Musculoskeletal",
    "adrenal": "Endocrinology",
    "thyroid": "Endocrinology",
    "pituitary": "Endocrinology",
    "brain": "Neurology",
    "neuro": "Neurology",
    "spinal": "Neurology",
    "nerve": "Neurology",
    "blood": "Hematology",
    "haemat": "Hematology",
    "hemat": "Hematology",
    "genetic": "Genetics / Genomic Medicine",
    "chromosom": "Genetics / Genomic Medicine",
}


# =========================
# KEYWORD RULES
# =========================

RULES = [
    {
        "name": "diabetic_retinopathy",
        "patterns_any": ["diabetic retinopathy"],
        "primary_domain": "Endocrinology",
        "secondary_domains": ["Ophthalmology"],
        "confidence": 0.95,
    },
    {
        "name": "diabetic_nephropathy",
        "patterns_any": ["diabetic nephropathy"],
        "primary_domain": "Endocrinology",
        "secondary_domains": ["Nephrology"],
        "confidence": 0.95,
    },
    {
        "name": "rheumatology_specific",
        "patterns_any": [
            "rheumatoid arthritis",
            "lupus",
            "sjogren",
            "scleroderma",
            "vasculitis",
            "ankylosing spondylitis",
            "psoriatic arthritis",
            "connective tissue disease",
            "myositis",
            "gout",
        ],
        "primary_domain": "Rheumatology",
        "secondary_domains": [],
        "confidence": 0.91,
    },
    {
        "name": "allergy_immunology",
        "patterns_any": [
            "allergy",
            "allergic",
            "anaphylaxis",
            "immunodeficiency",
            "angioedema",
            "mast cell",
        ],
        "primary_domain": "Allergy and Immunology",
        "secondary_domains": [],
        "confidence": 0.89,
    },
    {
        "name": "diabetes",
        "patterns_any": ["diabetes", "diabetic", "thyroid", "adrenal", "pituitary"],
        "primary_domain": "Endocrinology",
        "secondary_domains": [],
        "confidence": 0.86,
    },
    {
        "name": "respiratory",
        "patterns_any": [
            "asthma",
            "copd",
            "bronchitis",
            "bronchiolitis",
            "pneumonia",
            "respiratory",
            "pulmonary",
            "emphysema",
        ],
        "primary_domain": "Respiratory / Pulmonology",
        "secondary_domains": [],
        "confidence": 0.87,
    },
    {
        "name": "cardiology",
        "patterns_any": [
            "hypertension",
            "myocardial",
            "angina",
            "arrhythmia",
            "heart failure",
            "cardiac",
            "coronary",
            "aneurysm",
        ],
        "primary_domain": "Cardiovascular / Cardiology",
        "secondary_domains": [],
        "confidence": 0.87,
    },
    {
        "name": "neurology",
        "patterns_any": [
            "stroke",
            "epilepsy",
            "migraine",
            "multiple sclerosis",
            "parkinson",
            "neuropathy",
            "alzheimer",
            "seizure",
        ],
        "primary_domain": "Neurology",
        "secondary_domains": [],
        "confidence": 0.87,
    },
    {
        "name": "dermatology",
        "patterns_any": [
            "psoriasis",
            "eczema",
            "dermatitis",
            "acne",
            "urticaria",
            "rash",
            "alopecia",
            "keratosis",
        ],
        "primary_domain": "Dermatology",
        "secondary_domains": [],
        "confidence": 0.87,
    },
    {
        "name": "gastroenterology",
        "patterns_any": [
            "crohn",
            "ulcerative colitis",
            "hepatitis",
            "pancreatitis",
            "gastritis",
            "cirrhosis",
            "achalasia",
            "anal fissure",
            "anal fistula",
            "liver disease",
        ],
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": [],
        "confidence": 0.87,
    },
    {
        "name": "psychiatry",
        "patterns_any": [
            "depression",
            "anxiety",
            "bipolar",
            "schizophrenia",
            "ocd",
            "ptsd",
            "adjustment reaction",
            "stress reaction",
            "alcohol abuse",
            "alcohol withdrawal",
        ],
        "primary_domain": "Psychiatry",
        "secondary_domains": [],
        "confidence": 0.87,
    },
    {
        "name": "oncology",
        "patterns_any": [
            "cancer",
            "carcinoma",
            "lymphoma",
            "leukemia",
            "leukaemia",
            "melanoma",
            "tumour",
            "tumor",
            "adenoma",
            "neoplasm",
            "malignant",
        ],
        "primary_domain": "Oncology",
        "secondary_domains": [],
        "confidence": 0.86,
    },
    {
        "name": "nephrology",
        "patterns_any": [
            "kidney",
            "renal",
            "nephro",
            "acute kidney injury",
            "chronic kidney disease",
        ],
        "primary_domain": "Nephrology",
        "secondary_domains": [],
        "confidence": 0.86,
    },
    {
        "name": "ophthalmology",
        "patterns_any": [
            "retinopathy",
            "glaucoma",
            "cataract",
            "uveitis",
            "macular",
            "eye",
            "amblyopia",
        ],
        "primary_domain": "Ophthalmology",
        "secondary_domains": [],
        "confidence": 0.86,
    },
    {
        "name": "ent",
        "patterns_any": [
            "otitis",
            "sinusitis",
            "pharyngitis",
            "tonsillitis",
            "laryngitis",
            "rhinitis",
            "nose",
            "ear",
            "pharynx",
        ],
        "primary_domain": "ENT / Otolaryngology",
        "secondary_domains": [],
        "confidence": 0.86,
    },
    {
        "name": "hematology",
        "patterns_any": [
            "anemia",
            "anaemia",
            "thrombocytopenia",
            "hemophilia",
            "haemophilia",
            "sickle cell",
            "thalassemia",
            "thalassaemia",
            "amyloidosis",
        ],
        "primary_domain": "Hematology",
        "secondary_domains": [],
        "confidence": 0.86,
    },
]


# =========================
# PATTERN FAMILY RULES
# =========================

PATTERN_RULES = [
    {
        "name": "fracture_general",
        "starts_with": "fracture of",
        "contains_any": [],
        "primary_domain": "Musculoskeletal",
        "secondary_domains": ["Emergency / Trauma Medicine"],
        "confidence": 0.98,
    },
    {
        "name": "dislocation_general",
        "starts_with": "dislocation of",
        "contains_any": [],
        "primary_domain": "Musculoskeletal",
        "secondary_domains": ["Emergency / Trauma Medicine"],
        "confidence": 0.98,
    },
    {
        "name": "injury_general",
        "starts_with": "injury of",
        "contains_any": [],
        "primary_domain": "Emergency / Trauma Medicine",
        "secondary_domains": [],
        "confidence": 0.97,
    },
    {
        "name": "open_wound_general",
        "starts_with": "open wound of",
        "contains_any": [],
        "primary_domain": "Emergency / Trauma Medicine",
        "secondary_domains": [],
        "confidence": 0.97,
    },
    {
        "name": "poisoning_due_to",
        "starts_with": "poisoning due to",
        "contains_any": [],
        "primary_domain": "Emergency / Trauma Medicine",
        "secondary_domains": [],
        "confidence": 0.99,
    },
    {
        "name": "foreign_body_eye",
        "starts_with": "foreign body in",
        "contains_any": ["eye", "ocular"],
        "primary_domain": "Ophthalmology",
        "secondary_domains": ["Emergency / Trauma Medicine"],
        "confidence": 0.96,
    },
    {
        "name": "foreign_body_ear",
        "starts_with": "foreign body in",
        "contains_any": ["ear"],
        "primary_domain": "ENT / Otolaryngology",
        "secondary_domains": ["Emergency / Trauma Medicine"],
        "confidence": 0.96,
    },
    {
        "name": "foreign_body_gi",
        "starts_with": "foreign body in",
        "contains_any": ["gastrointestinal", "stomach", "bowel", "intestinal", "esophagus", "oesophagus"],
        "primary_domain": "Gastroenterology / Hepatology",
        "secondary_domains": ["Emergency / Trauma Medicine"],
        "confidence": 0.96,
    },
    {
        "name": "foreign_body_default",
        "starts_with": "foreign body in",
        "contains_any": [],
        "primary_domain": None,
        "secondary_domains": ["Emergency / Trauma Medicine"],
        "confidence": 0.93,
    },
    {
        "name": "abscess_ent",
        "starts_with": "abscess of",
        "contains_any": ["nose", "pharynx", "tonsil", "ear"],
        "primary_domain": "ENT / Otolaryngology",
        "secondary_domains": ["Infectious Diseases"],
        "confidence": 0.94,
    },
    {
        "name": "abscess_lung",
        "starts_with": "abscess of",
        "contains_any": ["lung"],
        "primary_domain": "Respiratory / Pulmonology",
        "secondary_domains": ["Infectious Diseases"],
        "confidence": 0.94,
    },
    {
        "name": "abscess_skin",
        "starts_with": "abscess of",
        "contains_any": ["skin", "scalp"],
        "primary_domain": "Dermatology",
        "secondary_domains": ["Infectious Diseases"],
        "confidence": 0.93,
    },
    {
        "name": "abscess_default",
        "starts_with": "abscess of",
        "contains_any": [],
        "primary_domain": None,
        "secondary_domains": ["Infectious Diseases"],
        "confidence": 0.90,
    },
    {
        "name": "fungal_infection_skin",
        "starts_with": "fungal infection of",
        "contains_any": ["skin", "hair", "nail"],
        "primary_domain": "Dermatology",
        "secondary_domains": ["Infectious Diseases"],
        "confidence": 0.95,
    },
    {
        "name": "fungal_infection_default",
        "starts_with": "fungal infection of",
        "contains_any": [],
        "primary_domain": "Infectious Diseases",
        "secondary_domains": [],
        "confidence": 0.90,
    },
]


# =========================
# HELPERS
# =========================

def normalize(text: str) -> str:
    text = str(text).lower().strip()

    text = text.replace("“", "").replace("”", "").replace('"', "").replace("'", "")
    text = text.replace("&", " and ")
    text = text.replace("/", " ")

    replacements = {
        "hermia": "hernia",
        "injury to ": "injury of ",
        "open wound from ": "open wound of ",
        "foreign body within ": "foreign body in ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\bunspecified\b", " ", text)
    text = re.sub(r"\bnos\b", " ", text)
    text = re.sub(r"\bwithout\b", " ", text)
    text = re.sub(r"\bsecondary to\b", " ", text)

    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def validate_domains(primary_domain: Optional[str], secondary_domains: List[str]) -> None:
    if primary_domain is not None and primary_domain not in ALLOWED_DOMAINS:
        raise ValueError(f"Invalid primary domain: {primary_domain}")

    for d in secondary_domains:
        if d not in ALLOWED_DOMAINS:
            raise ValueError(f"Invalid secondary domain: {d}")


def clean_secondary_domains(primary_domain: Optional[str], secondary_domains: List[str]) -> List[str]:
    cleaned: List[str] = []
    seen = set()
    for d in secondary_domains:
        if d != primary_domain and d not in seen:
            cleaned.append(d)
            seen.add(d)
    return cleaned


def make_result(
    *,
    normalized_name: str,
    canonical_name: Optional[str],
    primary_domain: Optional[str],
    secondary_domains: List[str],
    confidence: float,
    assignment_method: str,
    needs_review: bool,
) -> Dict[str, Any]:
    secondary_domains = clean_secondary_domains(primary_domain, secondary_domains)
    validate_domains(primary_domain, secondary_domains)

    return {
        "normalized_name": normalized_name,
        "canonical_name": canonical_name,
        "primary_domain": primary_domain,
        "secondary_domains": secondary_domains,
        "confidence": round(float(confidence), 2),
        "assignment_method": assignment_method,
        "needs_review": bool(needs_review),
    }


def exact_match(name: str) -> Optional[Dict[str, Any]]:
    if name not in DISEASE_DOMAIN_MAP:
        return None

    record = DISEASE_DOMAIN_MAP[name]
    return make_result(
        normalized_name=name,
        canonical_name=name,
        primary_domain=record["primary_domain"],
        secondary_domains=list(record["secondary_domains"]),
        confidence=0.99,
        assignment_method="exact",
        needs_review=False,
    )


def alias_match(name: str) -> Optional[Dict[str, Any]]:
    canonical = ALIAS_MAP.get(name)
    if not canonical:
        return None

    record = DISEASE_DOMAIN_MAP.get(canonical)
    if not record:
        return None

    return make_result(
        normalized_name=name,
        canonical_name=canonical,
        primary_domain=record["primary_domain"],
        secondary_domains=list(record["secondary_domains"]),
        confidence=0.98,
        assignment_method="alias",
        needs_review=False,
    )


def anatomy_match(name: str) -> Optional[Dict[str, Any]]:
    for keyword, domain in ANATOMY_TO_DOMAIN.items():
        if keyword in name:
            return make_result(
                normalized_name=name,
                canonical_name=None,
                primary_domain=domain,
                secondary_domains=[],
                confidence=0.78,
                assignment_method=f"anatomy:{keyword}",
                needs_review=True,
            )
    return None


def rule_match(name: str) -> Optional[Dict[str, Any]]:
    for rule in RULES:
        if any(pattern in name for pattern in rule["patterns_any"]):
            return make_result(
                normalized_name=name,
                canonical_name=None,
                primary_domain=rule["primary_domain"],
                secondary_domains=list(rule["secondary_domains"]),
                confidence=rule["confidence"],
                assignment_method=f"rule:{rule['name']}",
                needs_review=rule["confidence"] < 0.90,
            )
    return None


def pattern_rule_match(name: str) -> Optional[Dict[str, Any]]:
    for rule in PATTERN_RULES:
        if not name.startswith(rule["starts_with"]):
            continue

        contains_any = rule.get("contains_any", [])
        if contains_any and not any(term in name for term in contains_any):
            continue

        primary_domain = rule["primary_domain"]
        secondary_domains = list(rule["secondary_domains"])

        if primary_domain is None:
            anatomy = anatomy_match(name)
            if anatomy:
                primary_domain = anatomy["primary_domain"]

        return make_result(
            normalized_name=name,
            canonical_name=None,
            primary_domain=primary_domain,
            secondary_domains=secondary_domains,
            confidence=rule["confidence"],
            assignment_method=f"pattern:{rule['name']}",
            needs_review=(rule["confidence"] < 0.95 or primary_domain is None),
        )

    return None


def fuzzy_match(name: str, threshold: int = 88) -> Optional[Dict[str, Any]]:
    choices = list(DISEASE_DOMAIN_MAP.keys())
    match = process.extractOne(name, choices, scorer=fuzz.ratio)
    if not match:
        return None

    matched_name, score, _ = match
    if score < threshold:
        return None

    record = DISEASE_DOMAIN_MAP[matched_name]
    confidence = score / 100.0

    return make_result(
        normalized_name=name,
        canonical_name=matched_name,
        primary_domain=record["primary_domain"],
        secondary_domains=list(record["secondary_domains"]),
        confidence=confidence,
        assignment_method="fuzzy",
        needs_review=confidence < 0.93,
    )


# Optional
# def llm_fallback(disease_name: str) -> Dict[str, Any]:
#     prompt = f"""
# You are assigning a medical taxonomy domain.
# Only choose from this list:
# {sorted(ALLOWED_DOMAINS)}
#
# Disease: "{disease_name}"
#
# Return strict JSON:
# {{
#   "primary_domain": "one domain or null",
#   "secondary_domains": ["zero or more domains"],
#   "confidence": 0.0
# }}
# """
#     response = client.responses.create(
#         model=OPENAI_MODEL,
#         input=prompt,
#     )
#     text = response.output_text.strip()
#     data = json.loads(text)
#
#     return make_result(
#         normalized_name=normalize(disease_name),
#         canonical_name=None,
#         primary_domain=data.get("primary_domain"),
#         secondary_domains=data.get("secondary_domains", []),
#         confidence=float(data.get("confidence", 0.0)),
#         assignment_method="llm",
#         needs_review=float(data.get("confidence", 0.0)) < 0.90,
#     )


def assign_domains(disease_name: str) -> Dict[str, Any]:
    normalized_name = normalize(disease_name)

    result = exact_match(normalized_name)
    if result:
        return result

    result = alias_match(normalized_name)
    if result:
        return result

    result = pattern_rule_match(normalized_name)
    if result:
        return result

    result = rule_match(normalized_name)
    if result:
        return result

    result = anatomy_match(normalized_name)
    if result:
        return result

    result = fuzzy_match(normalized_name)
    if result:
        return result

    # Optional
    # if USE_LLM_FALLBACK:
    #     return llm_fallback(disease_name)

    return make_result(
        normalized_name=normalized_name,
        canonical_name=None,
        primary_domain=None,
        secondary_domains=[],
        confidence=0.0,
        assignment_method="unresolved",
        needs_review=True,
    )


# =========================
# MAIN
# =========================

def main() -> None:
    df = pd.read_csv(INPUT_CSV)

    if DISEASE_COLUMN not in df.columns:
        raise ValueError(
            f"Column '{DISEASE_COLUMN}' not found in CSV. "
            f"Available columns: {list(df.columns)}"
        )

    results = df[DISEASE_COLUMN].apply(assign_domains).apply(pd.Series)
    output_df = pd.concat([df, results], axis=1)

    output_df["secondary_domains"] = output_df["secondary_domains"].apply(json.dumps)
    output_df = output_df.sort_values(
        by=[DISEASE_COLUMN],
        ascending=[True]
    )

    output_df.to_csv(OUTPUT_CSV, index=False)

    print(f"Saved output to: {OUTPUT_CSV}")
    print("\nAssignment method counts:")
    print(output_df["assignment_method"].value_counts(dropna=False))
    print("\nRows needing review:")
    print(output_df["needs_review"].value_counts(dropna=False))
    print("\nTop unresolved examples:")
    unresolved = output_df[output_df["assignment_method"] == "unresolved"][DISEASE_COLUMN].head(20)
    for item in unresolved:
        print("-", item)


if __name__ == "__main__":
    main()