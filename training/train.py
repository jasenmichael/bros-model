#!/usr/bin/env python3
"""Supervised LoRA fine-tune for Bros."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, PeftModel, TaskType
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
from trl import SFTConfig, SFTTrainer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.config import (  # noqa: E402
    BASE_MODEL,
    DEFAULT_BATCH_SIZE,
    DEFAULT_EPOCHS,
    DEFAULT_GRAD_ACCUM,
    DEFAULT_LEARNING_RATE,
    DEFAULT_MAX_LENGTH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SEED,
    DEFAULT_TRAIN_PATH,
    DEFAULT_VALIDATION_PATH,
    LORA_ALPHA,
    LORA_DROPOUT,
    LORA_R,
    LORA_TARGET_MODULES,
    SYSTEM_PROMPT,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune Bros with LoRA SFT.")
    parser.add_argument("--model", default=BASE_MODEL, help="Base or previously merged model path.")
    parser.add_argument(
        "--adapter",
        default=None,
        help="Optional existing LoRA adapter to continue training.",
    )
    parser.add_argument("--train-data", default=DEFAULT_TRAIN_PATH)
    parser.add_argument("--eval-data", default=DEFAULT_VALIDATION_PATH)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--epochs", type=float, default=DEFAULT_EPOCHS)
    parser.add_argument("--learning-rate", type=float, default=DEFAULT_LEARNING_RATE)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--grad-accum", type=int, default=DEFAULT_GRAD_ACCUM)
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--max-steps", type=int, default=-1, help="If > 0, overrides epochs.")
    parser.add_argument(
        "--eval-batch-size",
        type=int,
        default=None,
        help="Defaults to --batch-size.",
    )
    return parser.parse_args()


def precision_flags() -> tuple[torch.dtype, bool, bool]:
    if torch.cuda.is_available():
        if torch.cuda.is_bf16_supported():
            return torch.bfloat16, True, False
        return torch.float16, False, True
    return torch.float32, False, False


def to_conversation(example: dict) -> dict:
    return {
        "prompt": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": example["prompt"]},
        ],
        "completion": [
            {"role": "assistant", "content": example["completion"]},
        ],
    }


def load_jsonl_conversations(path: str) -> object:
    dataset = load_dataset("json", data_files=path, split="train")
    keep = {"prompt", "completion"}
    drop = [name for name in dataset.column_names if name not in keep]
    mapped = dataset.map(to_conversation, remove_columns=drop)
    return mapped


def load_trainable_model(model_name: str, adapter: str | None, dtype: torch.dtype):
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name, dtype=dtype)
    if torch.cuda.is_available():
        model.to("cuda")
    if adapter:
        model = PeftModel.from_pretrained(model, adapter, is_trainable=True)
        return tokenizer, model, None
    peft_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=list(LORA_TARGET_MODULES),
    )
    return tokenizer, model, peft_config


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    dtype, use_bf16, use_fp16 = precision_flags()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device} dtype={dtype} bf16={use_bf16} fp16={use_fp16}")

    tokenizer, model, peft_config = load_trainable_model(args.model, args.adapter, dtype)
    train_dataset = load_jsonl_conversations(args.train_data)
    eval_dataset = load_jsonl_conversations(args.eval_data)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    eval_batch = args.eval_batch_size or args.batch_size

    sft_kwargs = dict(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=eval_batch,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        max_length=args.max_length,
        packing=False,
        completion_only_loss=True,
        logging_steps=10,
        seed=args.seed,
        bf16=use_bf16,
        fp16=use_fp16,
        report_to="none",
        gradient_checkpointing=False,
    )
    if args.max_steps > 0:
        sft_kwargs["eval_strategy"] = "steps"
        sft_kwargs["eval_steps"] = max(args.max_steps, 1)
        sft_kwargs["save_strategy"] = "no"
    else:
        sft_kwargs["eval_strategy"] = "epoch"
        sft_kwargs["save_strategy"] = "epoch"

    trainer = SFTTrainer(
        model=model,
        args=SFTConfig(**sft_kwargs),
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"saved adapter to {output_dir}")


if __name__ == "__main__":
    main()
