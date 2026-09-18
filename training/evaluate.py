#!/usr/bin/env python3
"""Generate labels for the Bros test split and print simple format metrics."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.config import (  # noqa: E402
    BASE_MODEL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SEED,
    DEFAULT_TEST_PATH,
    LABEL_TASK,
    MAX_LABEL_WORDS,
    MAX_NEW_TOKENS,
    MIN_LABEL_WORDS,
    SYSTEM_PROMPT,
)

PUNCTUATION_RE = re.compile(r"""[!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~]""")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Bros on the test JSONL split.")
    parser.add_argument("--model", default=BASE_MODEL)
    parser.add_argument("--adapter", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--test-data", default=DEFAULT_TEST_PATH)
    parser.add_argument("--max-new-tokens", type=int, default=MAX_NEW_TOKENS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--limit", type=int, default=0, help="If > 0, evaluate only the first N rows.")
    return parser.parse_args()


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def is_valid_label(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if PUNCTUATION_RE.search(stripped):
        return False
    words = stripped.split()
    return MIN_LABEL_WORDS <= len(words) <= MAX_LABEL_WORDS


def decode_completion(tokenizer, sequences, prompt_length: int) -> str:
    generated = sequences[0][prompt_length:]
    text = tokenizer.decode(generated, skip_special_tokens=True)
    text = text.replace("<|im_end|>", "").replace("<|im_start|>", "")
    return text.strip().splitlines()[0].strip() if text.strip() else ""


def load_model(model_name: str, adapter: str | None):
    tokenizer = AutoTokenizer.from_pretrained(adapter or model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else (
        torch.float16 if torch.cuda.is_available() else torch.float32
    )
    kwargs = {"dtype": dtype}
    model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
    if torch.cuda.is_available():
        model.to("cuda")
    if adapter:
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return tokenizer, model


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    test_path = Path(args.test_data)
    rows = load_rows(test_path)
    if args.limit > 0:
        rows = rows[: args.limit]
    tokenizer, model = load_model(args.model, args.adapter)

    exact = 0
    valid = 0
    lengths: list[int] = []

    for row in rows:
        prompt = row["prompt"]
        expected = row["completion"].strip()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        encoded = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        )
        input_ids = encoded["input_ids"] if isinstance(encoded, dict) else encoded
        if hasattr(input_ids, "input_ids"):
            input_ids = input_ids.input_ids
        input_ids = input_ids.to(next(model.parameters()).device)
        prompt_length = input_ids.shape[-1]
        with torch.inference_mode():
            output = model.generate(
                input_ids,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        predicted = decode_completion(tokenizer, output, prompt_length)
        print("PROMPT:")
        print(prompt)
        print("EXPECTED:")
        print(expected)
        print("PREDICTED:")
        print(predicted)
        print()

        if predicted == expected:
            exact += 1
        task = row.get("task", LABEL_TASK)
        if task == LABEL_TASK:
            if is_valid_label(predicted):
                valid += 1
            lengths.append(len(predicted.split()) if predicted else 0)
        else:
            if predicted:
                valid += 1
            lengths.append(len(predicted.split()) if predicted else 0)

    n = len(rows) or 1
    avg_len = sum(lengths) / len(lengths) if lengths else 0.0
    print(f"examples: {len(rows)}")
    print(f"exact match rate: {exact / n:.3f} ({exact}/{len(rows)})")
    print(f"valid-label rate: {valid / n:.3f} ({valid}/{len(rows)})")
    print(f"average generated label length: {avg_len:.2f} words")
    print("Exact match is only one indicator. It does not measure semantic quality.")


if __name__ == "__main__":
    main()
