# STACK

This repo trains and packages the **[Bros](https://github.com/jasenmichael/bros) app internal specialist**. Production runtime is the Bros **Ollama sidecar**. Host Ollama is a dev convenience only.

## Training (this repository)

- Python 3.10+ (developed on 3.12)
- uv for the virtualenv and dependencies
- PyTorch 2.11 CUDA 13 (`cu130` extra index in `pyproject.toml`; CPU fallback if CUDA is missing)
- Hugging Face Transformers, Datasets, TRL SFT, PEFT LoRA
- Base model: `HuggingFaceTB/SmolLM2-135M-Instruct` (~135M parameters)

Do not install bitsandbytes / QLoRA. 135M LoRA fits in 16 GB VRAM in bf16 or fp16.

## Conversion

- An existing llama.cpp checkout (not vendored)
- `convert_hf_to_gguf.py` for FP16 GGUF
- `llama-quantize` for Q4_K_M (this build fell back to Q4_0 at 91,726,752 bytes because Q4_K_M was 105,453,984 bytes)

## Production (Bros app sidecar)

- [jasenmichael/bros](https://github.com/jasenmichael/bros) git submodule `vendor/bros-model`
- Packaged file `models/bros-q4_k_m.gguf`
- Modelfile `ollama/Modelfile`
- Bros copies `models/` + `ollama/` + `scripts/` onto `$BROS_HOST_DATA_DIR/ollama/bros-model` and bind-mounts that tree at `/bros-model:ro` into `bros-sc-ollama`
- Inside the sidecar: `bash /bros-model/scripts/install-ollama.sh` registers Ollama name `bros`
- The Bros app does not need Python, PyTorch, Transformers, or Hugging Face at runtime

```text
Bros app
    sidecar Ollama API (http://ollama:11434)
        bros
            Label: title
```

Standalone `git clone` + `bash scripts/install-ollama.sh` needs a local Ollama daemon and is for development only.

## Hardware notes

This machine: NVIDIA GeForce RTX 3080 Laptop GPU, 16 GB VRAM. Training defaults assume CUDA. Scripts still detect CPU and run there if CUDA is unavailable.
