# llm_manager_config.py

import os

def load_mistral_config():
    return {
        "model": "mistral-small-latest",
        "api_key": os.getenv("MISTRAL_API_KEY"),
        "temperature": 0,
        "max_retries": 2,
    }
