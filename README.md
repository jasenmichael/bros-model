# Bros specialist model

This repository is the **[Bros](https://github.com/jasenmichael/bros) app internal specialist** — a small Ollama model installed into the Bros **Ollama sidecar**. It is not a standalone chatbot and it is not listed in Chat or Providers. Users of the Bros app never select it.

- Model repo: https://github.com/jasenmichael/bros-model
- Bros app: https://github.com/jasenmichael/bros

The first shipped skill is **chat labeling**: take the first user message of a chat and return a concise 2–5 word label. Later Bros-app mini-tasks use the same 135M model, the same Ollama name (`bros`), and more training data. Training, convert, and llama.cpp sections below are for people who will add those skills.

Packaged artifacts:

- GGUF: `models/bros-q4_k_m.gguf`
- Modelfile: `ollama/Modelfile`
- Install: `scripts/install-ollama.sh`

## How the Bros app installs it

[Bros](https://github.com/jasenmichael/bros) vendors this repo as git submodule `vendor/bros-model`.

When the Ollama sidecar starts (`startSidecar('ollama')`) and when `GET /api/providers` sees that sidecar running, Bros `ensureInternalBrosModel()`:

1. Copies `models/`, `ollama/`, and `scripts/` onto `$BROS_HOST_DATA_DIR/ollama/bros-model`
2. Bind-mounts that tree into the sidecar: `${BROS_HOST_DATA_DIR}/ollama/bros-model:/bros-model:ro`
3. Exec inside `bros-sc-ollama`: `bash /bros-model/scripts/install-ollama.sh` (`ollama create bros -f ollama/Modelfile`)
4. Writes the created model into sidecar `/root/.ollama` (`$BROS_HOST_DATA_DIR/ollama/root/.ollama`)

Skip if sidecar tags already include `bros` and the GGUF size/mtime stamp matches. Missing GGUF: Bros logs once and skips; chat still works (title fallback).

The Bros app calls this model for auto-titles only. After the first successful assistant reply, `generateChatTitle` POSTs to sidecar DNS `http://ollama:11434/api/chat` with `model: "bros"`, `stream: false`, and one user message `Label: ${first user prompt}`. That is not the conversation chat model. Name `bros` is reserved (not listed; pull/delete returns 400).

Production/runtime install is that sidecar path. Do not treat a host `ollama create` as how Bros users get the model.

## Releasing a new model

1. Train, merge, convert, and commit the updated GGUF in this repo (see [Train more things / development](#train-more-things--development)).
2. Tag a release on [jasenmichael/bros-model](https://github.com/jasenmichael/bros-model).
3. Bump the pinned submodule in [jasenmichael/bros](https://github.com/jasenmichael/bros) to that tag/commit, then ship a **new Bros version**.

Prefer a new Bros release over asking operators to swap GGUFs by hand. Bros consumes a pinned submodule commit; `./bros update` recopies into the sidecar when the GGUF size/mtime stamp differs.

## Dev: standalone Ollama install

Use this only to develop or try the model on a **local Ollama daemon**. You do not need Python, PyTorch, or training to run the packaged GGUF. This is a convenience — not the Bros production path.

**Prerequisites:** [Ollama](https://ollama.com) installed and the daemon running. If it is not already up, start it in another terminal:

```bash
ollama serve
```

If the daemon is not on `localhost` (default port 11434), set **`OLLAMA_HOST`** before any `ollama` command — the CLI honors it:

```bash
export OLLAMA_HOST=http://your-host:11434
```

```bash
git clone https://github.com/jasenmichael/bros-model.git
cd bros-model
```

Shallow clone (smaller download, no full history):

```bash
git clone --depth 1 https://github.com/jasenmichael/bros-model.git
cd bros-model
```

Register the packaged model as **`bros`**:

```bash
bash scripts/install-ollama.sh
```

(`scripts/build-ollama.sh` is the same command — it delegates to `install-ollama.sh`.) The script resolves the repo root from its own path, so it also works from the Bros submodule checkout at `vendor/bros-model`.

Try it:

```bash
ollama run bros
```

At the prompt, send the same tagged format the model was trained on (first user message of a chat):

```text
Label: How do I configure Docker networking?
```

Expected reply — **label only**, no explanation:

```text
Docker Networking
```

### Missing packaged model

If install fails with:

```text
missing packaged model: .../models/bros-q4_k_m.gguf
```

this checkout has **no packaged GGUF** — clone a release or branch that includes `models/bros-q4_k_m.gguf`, or follow [Train more things / development](#train-more-things--development) to build one yourself.

## Train more things / development

Use this path to add new Bros-app mini-tasks to the **same 135M model**. The Ollama name stays **`bros`**.

### 1. Keep old examples (avoid catastrophic forgetting)

A 135M model will forget labeling if you train only on new data. **Keep every existing labeling row** in `data/source.jsonl` when you add skills.

### 2. Add new JSONL rows

Append rows with a new `"task"` value and a **new tag** in the prompt (for example `Title:`):

```json
{"prompt": "Label: How do I configure Docker networking?", "completion": "Docker Networking", "task": "label"}
{"prompt": "Title: Weekly standup notes from Tuesday", "completion": "Tuesday Standup", "task": "title"}
```

Rules:

- **`Label:` tasks** (and any task that uses the label rules): prompt must start with `Label:`, completion must be **2–5 words**, **no punctuation**.
- **Other tasks**: set `"task"` to something other than `label`; only a non-empty completion is required.
- Prompts must be **unique** across the file.

The Bros app must send the **same tag** the model was trained with, for example `Label: ...` or `Title: ...`.

### 3. Prepare splits

```bash
python scripts/prepare-data.py
```

Optional flags: `--source`, `--seed`, `--train-ratio`, `--validation-ratio`.

Writes `data/train.jsonl`, `data/validation.jsonl`, and `data/test.jsonl` (80 / 10 / 10, seed 42).

### 4. Train

**First-ever train** (v1 labeling only) — Hugging Face base, no `--model` override:

```bash
python training/train.py
```

**Later skills** — continue from the merged checkpoint after stage 1:

```bash
python training/train.py --model output/merged
```

Defaults (3080-sized): 3 epochs, learning rate `2e-4`, batch 8, gradient accumulation 2, max length 512, output `output/adapter/`. Merge after each stage; **do not stack LoRAs forever**.

Install Python deps first (see [Installing dependencies](#installing-dependencies)).

### 5. Merge, convert, commit, reinstall

```bash
python scripts/merge-adapter.py
bash scripts/convert-to-gguf.sh /path/to/llama.cpp
```

Requires merged weights at `output/merged/` and an existing [llama.cpp](#installing--using-llamacpp) checkout with `convert_hf_to_gguf.py` and `llama-quantize`.

Commit the updated `models/bros-q4_k_m.gguf` if it still fits under GitHub’s **100 MB** file limit. Then reinstall into a local Ollama daemon for a smoke test:

```bash
bash scripts/install-ollama.sh
```

To ship it to Bros users, tag a release and bump the submodule — see [Releasing a new model](#releasing-a-new-model). Do not ask operators to run `ollama create` on a host daemon.

### 6. Modelfile tweaks for longer replies

`ollama/Modelfile` sets **`num_predict 16`** for short labels. If a later skill needs longer output, raise `num_predict` there, then run `bash scripts/install-ollama.sh` again.

## Why the model is tiny

The Bros app vendors this repo and installs the GGUF into the **Ollama sidecar**. The packaged GGUF should stay **under 100 MB** so it can live in GitHub (100 MB file limit) and ship inside that sidecar. A 135M instruct model quantized to Q4 is the right size. Do not swap in a larger base model to add skills.

## Base model

`HuggingFaceTB/SmolLM2-135M-Instruct` (~135M parameters, ChatML).

## Training approach

Supervised fine-tuning with LoRA / PEFT. Libraries: Hugging Face Transformers, Datasets, TRL `SFTTrainer`, PEFT, PyTorch.

v1 trains only the `Label:` skill. The JSONL format, `--model` continue-from-merged flag, and Ollama install path are built so later skills are more data plus a retrain, not a new project.

## Dataset format

JSONL:

```json
{"prompt": "Label: How do I configure Docker networking?", "completion": "Docker Networking", "task": "label"}
```

- `prompt` / `completion` are required.
- `task` defaults to `label`. Label rows must start with `Label:` and the completion must be 2–5 words with no punctuation.
- Other task values (later) only require a non-empty completion.

Canonical file: `data/source.jsonl`. Splits: `data/train.jsonl`, `data/validation.jsonl`, `data/test.jsonl` (80 / 10 / 10, seed 42, no prompt overlap).

The Bros app must send the same tag the model was trained with:

```text
Label: How do I configure Docker networking?
```

Expected style of reply:

```text
Docker Networking
```

## Installing dependencies

Python 3.10+ (3.12 used here). [uv](https://docs.astral.sh/uv/) is recommended.

```bash
UV_HTTP_TIMEOUT=600 uv sync
```

Large CUDA wheels can exceed uv's default 30s HTTP timeout. Set `UV_HTTP_TIMEOUT=600` (or higher) if `uv sync` fails mid-download.

This machine has an RTX 3080 (16 GB). `pyproject.toml` pulls **CUDA 13** PyTorch 2.11 from the `cu130` wheel index (already used successfully on this box). Confirm after sync:

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

If that index does not match your driver, use the current command from [pytorch.org](https://pytorch.org/get-started/locally/) and adjust `tool.uv.sources`.

CPU fallback (slow): remove the `pytorch-cu130` source in `pyproject.toml` and install the default CPU `torch`. Training scripts detect CUDA and do not hard-code it.

Seed: **42** (documented in `training/config.py` and the data split).

## Preparing data

```bash
python scripts/prepare-data.py
```

Optional flags: `--source`, `--seed`, `--train-ratio`, `--validation-ratio`.

The script validates rows, rejects duplicate prompts, shuffles with the seed, and writes the three splits.

## Training

```bash
python training/train.py
```

Defaults (3080-sized): 3 epochs, learning rate `2e-4`, batch 8, gradient accumulation 2, max length 512, output `output/adapter/`.

```bash
python training/train.py \
  --epochs 3 \
  --learning-rate 2e-4 \
  --batch-size 8 \
  --grad-accum 2 \
  --max-length 512 \
  --output-dir output/adapter \
  --seed 42
```

Continue from a previous merged checkpoint (later skills):

```bash
python training/train.py --model output/merged
```

Continue an existing LoRA:

```bash
python training/train.py --adapter output/adapter
```

Smoke test (one optimizer step):

```bash
python training/train.py --max-steps 1 --output-dir output/adapter-smoke
```

## Evaluating

```bash
python training/evaluate.py
```

Prints `PROMPT:` / `EXPECTED:` / `PREDICTED:` for every test row, then:

- exact match rate
- valid-label rate (2–5 words, no punctuation)
- average generated label length in words

Exact match is only one indicator. It does not measure semantic quality.

```bash
python training/evaluate.py --limit 20 --adapter output/adapter
```

## Merging the adapter

```bash
python scripts/merge-adapter.py
```

Writes a full Hugging Face model to `output/merged/` (needed for GGUF conversion).

## Installing / using llama.cpp

This repo does **not** vendor llama.cpp. Clone or reuse a checkout that has `convert_hf_to_gguf.py` and `llama-quantize`.

Example already on this machine:

```text
/home/me/.unsloth/llama.cpp
```

Generic install:

```bash
git clone https://github.com/ggml-org/llama.cpp
# build llama-quantize using the project's current instructions
```

## Packaged model (`models/bros-q4_k_m.gguf`)

Production and Ollama use a single quantized GGUF checked into git so clones can install without retraining. Training artifacts under `output/` stay gitignored.

| Item | Value |
|------|-------|
| Path | `models/bros-q4_k_m.gguf` |
| Ollama model name | `bros` |
| Quantization used | **Q4_0** (~87.5 MiB / 91,726,752 bytes) |
| Filename | Kept as `bros-q4_k_m.gguf` for stable paths |

The convert script tries **Q4_K_M** first, then falls back automatically: **Q4_K_M → Q4_0 → Q3_K_M** if the file would exceed GitHub’s 100 MB limit. On this build, Q4_K_M was 105,453,984 bytes (just over 100 MB), so the packaged file is Q4_0. Target: stay under 100 MB.

## Converting to GGUF (after training)

Only needed when you retrain and need a fresh packaged file. Requires merged weights at `output/merged/` and a llama.cpp checkout (see above).

```bash
bash scripts/convert-to-gguf.sh /path/to/llama.cpp
```

The script uses `.venv/bin/python` when present so llama.cpp can import torch. Override with `PYTHON=/path/to/python`.

Steps performed:

1. FP16 GGUF → gitignored `output/gguf/bros-f16.gguf`
2. Quantize to `models/bros-q4_k_m.gguf` with the fallback chain above
3. Print the selected quant type and byte size

After a successful convert, commit the updated `models/bros-q4_k_m.gguf` if it still fits under 100 MB. Then [release](#releasing-a-new-model) via a Bros submodule bump — not a host-daemon install for operators.

## Ollama runtime

Production is the **Bros Ollama sidecar** only. The Bros app calls the sidecar Ollama API (`http://ollama:11434`); it does not need Python, PyTorch, Transformers, or Hugging Face at runtime. Host `ollama serve` is a [dev convenience](#dev-standalone-ollama-install), not how operators install the model.

```text
Bros app
    sidecar Ollama API (http://ollama:11434)
        bros
            Label: title
```

For the sidecar wiring, see [How the Bros app installs it](#how-the-bros-app-installs-it).

### Modelfile (`ollama/Modelfile`)

The Modelfile references the packaged GGUF and sets conservative inference for short labels:

- **ChatML template** (SmolLM2 `<|im_start|>` / `<|im_end|>` message format)
- **SYSTEM** prompt: Bros is a specialist; follow the task tag; for `Label:` return a 2–5 word label only (no punctuation, no explanation)
- **`temperature 0`**, **`num_predict 16`**, `top_p 0.1`, `top_k 10`, `seed 42`
- Stop tokens for ChatML boundaries

Raise `num_predict` in the Modelfile if a later skill needs more than 16 tokens, then rerun `bash scripts/install-ollama.sh`.

What `scripts/install-ollama.sh` does:

- Resolves this repo root (works from a submodule path)
- Requires `models/bros-q4_k_m.gguf` — fails with a clear error if missing
- Runs `ollama create bros -f ollama/Modelfile` (override name with `OLLAMA_MODEL_NAME`)

Non-interactive; safe for CI and app install hooks.

## Limitations

- 135M is small. Labels will miss nuance and sometimes fail exact match.
- Exact match is a weak metric.
- v1 is labeling only; other Bros skills are not in the starter set.
- Greedy decoding and a 16-token cap favor short labels, not long answers.
- Quantization (Q4) costs some quality versus the merged fp16/bf16 checkpoint.
- CPU training works but is slow.
- This repository does not implement the Bros application. Runtime lives in [jasenmichael/bros](https://github.com/jasenmichael/bros).

## Reproducibility

- Random seed: `42`
- Split: 80 / 10 / 10 from `data/source.jsonl`
- Base model id is pinned by name, not a commit hash (Hugging Face updates can change weights)
- Dependency lower bounds are in `pyproject.toml`; install current compatible releases
