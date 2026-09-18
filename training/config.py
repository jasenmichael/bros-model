"""Shared training and inference settings for Bros."""

from __future__ import annotations

BASE_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
DEFAULT_SEED = 42
DEFAULT_OUTPUT_DIR = "output/adapter"
DEFAULT_MERGED_DIR = "output/merged"
DEFAULT_TRAIN_PATH = "data/train.jsonl"
DEFAULT_VALIDATION_PATH = "data/validation.jsonl"
DEFAULT_TEST_PATH = "data/test.jsonl"
DEFAULT_PACKAGED_GGUF = "models/bros-q4_k_m.gguf"
OLLAMA_MODEL_NAME = "bros"

SYSTEM_PROMPT = (
    "You are Bros, a small specialist model for the Bros app.\n"
    "Follow the task tag at the start of the user message.\n"
    "Label: generate a concise 2-5 word label for the user's first message. "
    "Return only the label. No punctuation. No explanation."
)

LABEL_TASK = "label"
LABEL_TAG = "Label:"
MIN_LABEL_WORDS = 2
MAX_LABEL_WORDS = 5
MAX_NEW_TOKENS = 16

# GPU-first defaults for an RTX 3080 16 GB. CLI can lower these for CPU.
DEFAULT_EPOCHS = 3
DEFAULT_LEARNING_RATE = 2e-4
DEFAULT_BATCH_SIZE = 8
DEFAULT_GRAD_ACCUM = 2
DEFAULT_MAX_LENGTH = 512

LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LORA_TARGET_MODULES = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]
