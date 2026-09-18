# PLAN

Current engineering plan for the Bros app internal specialist ([jasenmichael/bros-model](https://github.com/jasenmichael/bros-model)). Runtime install is the [Bros](https://github.com/jasenmichael/bros) Ollama sidecar, not a host daemon.

## Train / package

1. Prepare JSONL from `data/source.jsonl` (`task=label` for v1).
2. LoRA SFT `HuggingFaceTB/SmolLM2-135M-Instruct` with TRL.
3. Evaluate on `data/test.jsonl`.
4. Merge adapter into `output/merged/`.
5. Convert FP16 GGUF, quantize under 100 MB, copy to `models/bros-q4_k_m.gguf`.
6. `scripts/install-ollama.sh` creates Ollama model `bros` (dev: local daemon; production: Bros runs this inside `bros-sc-ollama`).

Later Bros-app skills: append tagged examples to `data/source.jsonl`, mix with labeling rows, train from `output/merged`, merge, quantize, reinstall. Do not drop old labeling data.

## Releasing a new model

1. Train, merge, convert, commit the GGUF in this repo.
2. Tag a release on jasenmichael/bros-model.
3. Bump submodule `vendor/bros-model` in [jasenmichael/bros](https://github.com/jasenmichael/bros) to that tag/commit.
4. Ship a new Bros version so sidecar `ensureInternalBrosModel` recopies when the GGUF stamp differs.

Prefer a Bros release over asking operators to swap GGUFs by hand.
