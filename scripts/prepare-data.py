#!/usr/bin/env python3
"""Validate, shuffle, and split Bros JSONL examples."""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.config import (  # noqa: E402
    DEFAULT_SEED,
    LABEL_TAG,
    LABEL_TASK,
    MAX_LABEL_WORDS,
    MIN_LABEL_WORDS,
)

PUNCTUATION_RE = re.compile(r"""[!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~]""")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Bros train/validation/test JSONL splits.")
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT / "data" / "source.jsonl",
        help="Source JSONL with prompt/completion rows.",
    )
    parser.add_argument("--train-out", type=Path, default=ROOT / "data" / "train.jsonl")
    parser.add_argument("--validation-out", type=Path, default=ROOT / "data" / "validation.jsonl")
    parser.add_argument("--test-out", type=Path, default=ROOT / "data" / "test.jsonl")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--validation-ratio", type=float, default=0.1)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(f"Source file not found: {path}")
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            rows.append(row)
    return rows


def word_count(text: str) -> int:
    return len(text.split())


def is_valid_label(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if PUNCTUATION_RE.search(stripped):
        return False
    if '"' in stripped or "'" in stripped:
        return False
    return MIN_LABEL_WORDS <= word_count(stripped) <= MAX_LABEL_WORDS


def normalize_row(row: dict, line_number: int) -> dict:
    if not isinstance(row, dict):
        raise SystemExit(f"line {line_number}: row must be a JSON object")
    prompt = row.get("prompt")
    completion = row.get("completion")
    task = row.get("task", LABEL_TASK)
    if not isinstance(prompt, str) or not prompt.strip():
        raise SystemExit(f"line {line_number}: prompt must be a non-empty string")
    if not isinstance(completion, str) or not completion.strip():
        raise SystemExit(f"line {line_number}: completion must be a non-empty string")
    if not isinstance(task, str) or not task.strip():
        raise SystemExit(f"line {line_number}: task must be a non-empty string")
    prompt = prompt.strip()
    completion = completion.strip()
    task = task.strip()
    if task == LABEL_TASK:
        if not prompt.startswith(LABEL_TAG):
            raise SystemExit(
                f"line {line_number}: label-task prompt must start with {LABEL_TAG!r}"
            )
        if not is_valid_label(completion):
            raise SystemExit(
                f"line {line_number}: label {completion!r} must be "
                f"{MIN_LABEL_WORDS}-{MAX_LABEL_WORDS} words with no punctuation"
            )
    return {"prompt": prompt, "completion": completion, "task": task}


def split_rows(
    rows: list[dict],
    seed: int,
    train_ratio: float,
    validation_ratio: float,
) -> tuple[list[dict], list[dict], list[dict]]:
    if train_ratio <= 0 or validation_ratio < 0 or train_ratio + validation_ratio >= 1:
        raise SystemExit("train-ratio and validation-ratio must leave a test remainder")
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * train_ratio)
    n_val = int(n * validation_ratio)
    train = shuffled[:n_train]
    validation = shuffled[n_train : n_train + n_val]
    test = shuffled[n_train + n_val :]
    if not train or not validation or not test:
        raise SystemExit(f"split produced an empty set (n={n}); need more examples")
    return train, validation, test


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    raw_rows = load_jsonl(args.source)
    rows = [normalize_row(row, i) for i, row in enumerate(raw_rows, start=1)]
    seen: dict[str, int] = {}
    duplicates: list[str] = []
    unique_rows: list[dict] = []
    for index, row in enumerate(rows, start=1):
        key = row["prompt"]
        if key in seen:
            duplicates.append(f"line {index} duplicates line {seen[key]}: {key[:80]!r}")
            continue
        seen[key] = index
        unique_rows.append(row)
    if duplicates:
        preview = "\n".join(duplicates[:20])
        extra = "" if len(duplicates) <= 20 else f"\n... and {len(duplicates) - 20} more"
        raise SystemExit(f"duplicate prompts:\n{preview}{extra}")

    train, validation, test = split_rows(
        unique_rows, args.seed, args.train_ratio, args.validation_ratio
    )
    write_jsonl(args.train_out, train)
    write_jsonl(args.validation_out, validation)
    write_jsonl(args.test_out, test)
    print(
        f"wrote {len(train)} train, {len(validation)} validation, {len(test)} test "
        f"(source={len(unique_rows)}, seed={args.seed})"
    )


if __name__ == "__main__":
    main()
