from pathlib import Path

# Define the root directory of the project
ROOT_DIR = Path(__file__).resolve().parent

# Define paths for commonly used files
MEMORY_FILE = ROOT_DIR / ".pocketflow_memory.json"

# App Defaults - LLM Configuration
LLM_BASE_URL = "http://localhost:1234/v1"
LLM_API_KEY = "lm-studio"
LLM_MODEL = "local-model"
