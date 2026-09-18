# PLAN

Current engineering plan for Bros.

1. Prepare JSONL from `data/source.jsonl` (`task=label` for v1).
2. LoRA SFT `HuggingFaceTB/SmolLM2-135M-Instruct` with TRL.
3. Evaluate on `data/test.jsonl`.
4. Merge adapter into `output/merged/`.
5. Convert FP16 GGUF, quantize under 100 MB, copy to `models/bros-q4_k_m.gguf`.
6. `scripts/install-ollama.sh` creates Ollama model `bros`.

Later Bros-app skills: append tagged examples to `data/source.jsonl`, mix with labeling rows, train from `output/merged`, merge, quantize, reinstall. Do not drop old labeling data.
