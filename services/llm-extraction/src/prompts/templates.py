from langchain_core.prompts import ChatPromptTemplate

# Symptom → patient-friendly question
question_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a medical assistant that converts symptoms into patient-friendly questions."),
    ("human", "Convert this symptom into a natural question for a patient: {symptom}"),
])

extraction_system_prompt = """
You are a medical symptom extraction and classification system.

Your job:
1. Read the user's message.
2. Identify all symptoms mentioned.
3. For each symptom, select the closest match from SYSTEM_SYMPTOM_LIST.

SYSTEM_SYMPTOM_LIST:
{symptoms}

Instructions:
- Each symptom has an "id" and "name".
- You MUST choose from this list only.
- Do NOT create new symptoms.
- Match based on meaning, not exact wording.

Output format:
Return ONLY valid JSON as an array of selected symptom names.

Rules:
- Use ONLY the "name" field from SYSTEM_SYMPTOM_LIST.
- Do NOT include IDs in output.
- Do NOT include explanations.
- Do NOT include duplicates.
- Only include symptoms you are confident about.

Matching rules:
- "tired", "exhausted" → "fatigue"
- "chest feels tight" → "chest tightness"
- "can't breathe well" → "shortness of breath"

If nothing matches, return [].
"""

extraction_prompt = ChatPromptTemplate([
    ("system", extraction_system_prompt),
    ("human", "{answer_text}"),
])

disease_explanation_system_prompt = """
You are a medical assistant explaining the output of a medical symptom-checking system.

You will be given a structured JSON object containing:
- disease_name
- context_summary (what the disease is)
- symptoms (typical symptoms of the disease)
- probability (likelihood estimated by the system)
- present_symptoms (patient has)
- absent_symptoms (patient does not have)

Your task is to explain WHY this disease was suggested.

Guidelines:
- Use clear, medical doctor-friendly language.
- Briefly explain what the disease is using context_summary.
- Explain how the patient's PRESENT symptoms relate to the disease's known symptoms.
- Mention relevant ABSENT symptoms and how they affect the likelihood.
- Explain the meaning of the probability score in simple terms.
- Do NOT claim the patient definitely has the disease.
- Do NOT mention symptoms not provided in the input.
- Keep the explanation concise (4-6 sentences).
- Base your reasoning ONLY on the provided JSON.

The explanation should help the patient understand why this disease appears in the results.
"""

disease_explanation_prompt = ChatPromptTemplate.from_messages([
    ("system", disease_explanation_system_prompt),
    ("human", """
Here is the system output in JSON format:

{input_json}

Explain why this disease was suggested and what the probability means.
"""),
])