# SPEC

Bros is a small local specialist language model for the Bros app.

It is not a general-purpose chatbot. It is installed into the app's Ollama and called for short, well-defined jobs.

## v1 behavior

First shipped skill: chat labeling.

The Bros app sends the first user message of a chat with a task tag:

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

## Later skills

The same 135M model, same Ollama name (`bros`), same git-install path.

New Bros-app mini-tasks are additional JSONL examples plus a retrain from the merged checkpoint. Each skill uses a distinct tag (`Label:`, later `Title:`, and so on). The app must send the same tag the model was trained with.

Do not replace Bros with a larger base model to add skills.

## Non-goals

- General conversation
- Cloud inference APIs at runtime
- Training a foundation model from scratch
- Implementing the Bros application in this repository
