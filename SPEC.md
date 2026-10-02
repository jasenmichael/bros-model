# SPEC

This repository is the **[Bros](https://github.com/jasenmichael/bros) app internal specialist** — a small local language model installed into the Bros **Ollama sidecar**.

It is not a general-purpose chatbot and it is not listed in Chat or Providers. The Bros app calls it for short, well-defined jobs. Users never select it.

- Model: https://github.com/jasenmichael/bros-model
- App: https://github.com/jasenmichael/bros

Bros vendors this repo as git submodule `vendor/bros-model`. At runtime the app copies the packaged tree onto sidecar data and runs `bash scripts/install-ollama.sh` inside `bros-sc-ollama` (`ollama create bros`). Ollama name `bros` is reserved.

## v1 behavior

First shipped skill: chat labeling.

After the first successful assistant reply, the Bros app POSTs to sidecar DNS `http://ollama:11434/api/chat` with `model: "bros"` and one user message:

```text
Label: How do I configure a Cloudflare tunnel with Docker?
```

Bros returns only a concise 2–5 word title-like label:

```text
Cloudflare Docker Setup
```

Rules for `Label:`:

- 2–5 words
- descriptive, title-like
- no punctuation
- no quotation marks
- no explanation, markdown, or extra sentences
- one label only

That call is not the conversation chat model. If generate fails, the app keeps `New chat` or the first line of the prompt.

## Later skills

The same 135M model, same Ollama name (`bros`), same git-submodule + sidecar install path.

New Bros-app mini-tasks are additional JSONL examples plus a retrain from the merged checkpoint. Each skill uses a distinct tag (`Label:`, later `Title:`, and so on). The app must send the same tag the model was trained with.

Do not replace Bros with a larger base model to add skills.

## Releases

New GGUFs are tagged in this repo. Typical path: bump the pinned submodule in [jasenmichael/bros](https://github.com/jasenmichael/bros) and ship a new Bros version. Prefer that over asking Bros users to swap GGUFs or run `ollama create` on a host daemon.

## Non-goals

- General conversation
- Cloud inference APIs at runtime
- Training a foundation model from scratch
- Implementing the Bros application in this repository
- Host Ollama as the production install path (dev convenience only)
