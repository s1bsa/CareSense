from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.config_loader import settings


BASE_DIR = Path(__file__).resolve().parents[2]


def load_data():
    data_dir = Path(settings['data']['directory'])
    probs_file = settings['data']['probs_file']
    priors_file = settings['data']['priors_file']
    alpha = settings['data']['alpha']

    if not data_dir.exists():
        data_dir = BASE_DIR / "data"
    
    probs_path = data_dir / probs_file
    priors_path = data_dir / priors_file
    
    probs = pd.read_csv(probs_path, index_col=0)
    priors = pd.read_csv(priors_path, index_col=0).squeeze()

    probs = (probs + alpha) / (1 + 2 * alpha)
    
    beliefs = np.log(priors)
    
    return probs, priors, beliefs
