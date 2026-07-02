"""ARI configuration."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FACTS_DIR = REPO / "cronqvn" / "facts"
QUESTIONS_FILE = REPO / "cronqvn" / "out" / "questions.json"
ARTIFACTS_DIR = REPO / "ari" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# Ollama (used at inference / evaluate phase)
OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = "qwen3:14b"
EMBED_MODEL = "nomic-embed-text"
LLM_TEMPERATURE = 0.0
LLM_NUM_CTX = 8192

# OpenAI (used at learn phase — paper-faithful methodology induction)
# Set OPENAI_API_KEY in the environment.
OPENAI_BASE_URL = "https://api.openai.com/v1"
OPENAI_MODEL = "gpt-4o"
OPENAI_EMBED_MODEL = "text-embedding-3-small"
OPENAI_TEMPERATURE = 0.0
OPENAI_SEED = 319

# ARI hyper-parameters (per paper §4.1)
N_CLUSTERS = 4
N_MEMORY_SAMPLES = 200       # historical reasoning samples to learn from
MAX_REASONING_STEPS = 5
TOP_K_ACTIONS = 12           # semantic top-K filtration
TOP_K_RELATIONS = 5          # câu hỏi mở: top-K pid theo cosine(câu hỏi, nhãn pid)
MAX_CANDIDATES_PER_RELATION = 80  # hard cap before semantic filter

# Eval
TEST_SAMPLE_SIZE = 200       # stratified subset (per paper)

# Cross-encoder reranker (cascade sau cosine). Tắt mặc định -> core vẫn
# stdlib-only; torch/transformers/pyvi chỉ load khi bật.
USE_CROSS_ENCODER = False
CE_COSINE_TOPN = 30                       # cosine giữ N trước khi đưa cross-encoder
CE_MODEL_DIR = ARTIFACTS_DIR / "ce_model"
CE_DATASET = ARTIFACTS_DIR / "ce_dataset.jsonl"
CE_BASE_MODEL = "vinai/phobert-base"
CE_MAX_LEN = 256
