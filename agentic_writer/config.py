import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# We don't raise error here to allow import without env var (e.g. during tests if mocked), 
# but app startup should check it.

# Model Configurations
MODELS = {
    "gemini-3-pro": {
        "id": "gemini-3-pro-preview", 
        "display_name": "Gemini 3 Pro",
        "context_window": 1048576
    },
    "gemini-2.5-pro": {
        "id": "gemini-2.5-pro",
        "display_name": "Gemini 2.5 Pro",
        "context_window": 1048576
    },
    "gemini-2.5-flash": {
        "id": "gemini-2.5-flash",
        "display_name": "Gemini 2.5 Flash",
        "context_window": 1048576
    }
}

DEFAULT_MODEL = "gemini-3-pro"
