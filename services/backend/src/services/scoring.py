import numpy as np
from src.utils.config_loader import settings

def scoreDiseases(beliefs, probs, symptom, present):
    if present:
        beliefs = beliefs + np.log(probs[symptom])
    else:
        beliefs = beliefs + np.log(1 - probs[symptom])
    return beliefs


def suggestSymptoms(beliefs, probs, symptoms, nonsymptoms, unconfirmed_symptoms):
    k = settings['logic']['k_suggestions']
    n_top = settings['logic']['n_top_diseases']
    
    top_n_index = beliefs.nlargest(n_top).index
    top_probs = probs.loc[top_n_index]

    asked = symptoms | nonsymptoms | unconfirmed_symptoms
    candidates = top_probs.drop(columns=asked, errors="ignore")

    if candidates.shape[1] == 0:
        return []

    variances = candidates.var()
    return variances.sort_values(ascending=False).head(k).index.tolist()
