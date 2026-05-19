"""ARI configuration."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FACTS_DIR = REPO / "cronqvn" / "facts"
QUESTIONS_FILE = REPO / "cronqvn" / "out" / "questions.json"
ARTIFACTS_DIR = REPO / "ari" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# Ollama
OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = "qwen2.5:7b"
EMBED_MODEL = "nomic-embed-text"
LLM_TEMPERATURE = 0.0
LLM_NUM_CTX = 8192

# ARI hyper-parameters (per paper §4.1)
N_CLUSTERS = 10
N_MEMORY_SAMPLES = 200       # historical reasoning samples to learn from
MAX_REASONING_STEPS = 5
TOP_K_ACTIONS = 12           # semantic top-K filtration
MAX_CANDIDATES_PER_RELATION = 80  # hard cap before semantic filter

# Eval
TEST_SAMPLE_SIZE = 200       # stratified subset (per paper)
