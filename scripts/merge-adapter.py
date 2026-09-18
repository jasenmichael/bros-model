#!/usr/bin/env python3
"""Merge a trained LoRA adapter into the base model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.config import BASE_MODEL, DEFAULT_MERGED_DIR, DEFAULT_OUTPUT_DIR  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge a Bros LoRA adapter into the base model.")
    parser.add_argument("--model", default=BASE_MODEL)
    parser.add_argument("--adapter", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_MERGED_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dtype = torch.float32
    print(f"loading base {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=dtype)
    model = PeftModel.from_pretrained(model, args.adapter)
    merged = model.merge_and_unload()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(output_dir), safe_serialization=True)
    tokenizer.save_pretrained(str(output_dir))
    print(f"saved merged model to {output_dir}")


if __name__ == "__main__":
    main()
