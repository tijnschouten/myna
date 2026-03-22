# Myna

Myna is a local mock server for OpenAI-compatible APIs.

Use it when you want your application to talk to a predictable HTTP endpoint during local
development or tests without calling a real model provider.

Package name: `mock-myna`  
Import path: `myna`  
[PyPI](https://pypi.org/project/mock-myna/) | [GHCR](https://github.com/tijnschouten/myna/pkgs/container/myna)

## What it provides

- OpenAI-style REST endpoints under `/v1`
- Stable mock responses for local development
- Scenario controls for delays and error injection
- A pytest plugin that starts the server and captures outgoing requests
- One-shot seeded responses for parser and failure-path tests

## Structured JSON mode

For chat completions with `response_format.type` set to `json_object` or `json_schema`, Myna inspects the provided JSON Schema and generates stable mock values by schema shape.

- `string` fields default to `"lorem ipsum"`
- String `format` values are recognized for `date`, `date-time`, `email`, `uri`/`url`, and `uuid`
- `integer`, `number`, and `boolean` fields return typed values
- `array` fields are populated from their `items` schema
- `object` fields are populated from `properties`
- Dict-like schemas using `additionalProperties` generate a small mock map with generated values
- `anyOf` and `oneOf` prefer non-`null` variants when both typed and nullable branches are present

## Supported endpoints

- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/completions`
- `POST /v1/embeddings`
- `POST /v1/images/generations`
- `POST /v1/audio/speech`
- `POST /v1/audio/transcriptions`
- `POST /v1/audio/translations`

## Quick start

### Run locally

```bash
uv sync
uv run uvicorn myna.main:app --reload --port 8000
```

The server will be available at `http://localhost:8000/v1`.

### Run with Docker

```bash
docker build -t myna .
docker run --rm -p 8000:8000 myna
```

## Using it with the OpenAI SDK

Point your client at the local `/v1` base URL and use any placeholder API key.

### Python

```python
from openai import OpenAI

client = OpenAI(
    api_key="mock",
    base_url="http://localhost:8000/v1",
)

resp = client.chat.completions.create(
    model="mock-chat-v1",
    messages=[{"role": "user", "content": "Say hello"}],
)

print(resp.choices[0].message.content)
```

### JavaScript / TypeScript

```ts
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "mock",
  baseURL: "http://localhost:8000/v1",
});

const resp = await client.chat.completions.create({
  model: "mock-chat-v1",
  messages: [{ role: "user", content: "Say hello" }],
});

console.log(resp.choices[0]?.message?.content);
```

## Example requests

### List models

```bash
curl http://localhost:8000/v1/models
```

### Chat completion

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"mock-chat-v1",
    "messages":[
      {"role":"system","content":"You are concise."},
      {"role":"user","content":"Give me one sentence about Amsterdam."}
    ]
  }'
```

### Streaming chat completion

```bash
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"mock-chat-v1",
    "stream":true,
    "messages":[{"role":"user","content":"Stream this response."}]
  }'
```

### Legacy completions

```bash
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-chat-v1","prompt":"Write a short greeting."}'
```

### Embeddings

```bash
curl http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model":"mock-embedding-v1",
    "input":["first text","second text"]
  }'
```

### Image generation

```bash
curl http://localhost:8000/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a cat in a bike basket","response_format":"url"}'

curl http://localhost:8000/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a cat in a bike basket","response_format":"b64_json"}'
```

### Audio speech

```bash
curl http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-tts-v1","input":"Hello world","response_format":"wav"}' \
  --output speech.wav

curl http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-tts-v1","input":"Hello world","response_format":"mp3"}' \
  --output speech.mp3
```

### Audio transcription and translation

```bash
curl http://localhost:8000/v1/audio/transcriptions \
  -F "file=@sample.wav" \
  -F "model=mock-asr-v1"

curl http://localhost:8000/v1/audio/translations \
  -F "file=@sample.wav" \
  -F "model=mock-asr-v1"
```

## Scenario controls

Use `X-Mock-Scenario` or the `scenario` query parameter to inject delays and failures.

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer test" \
  -H "X-Mock-Scenario: delay=500,error=rate_limit" \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-chat-v1","messages":[{"role":"user","content":"hi"}]}'
```

Examples:

```bash
# auth error
curl http://localhost:8000/v1/chat/completions \
  -H "X-Mock-Scenario: error=auth" \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-chat-v1","messages":[{"role":"user","content":"hello"}]}'

# delay + server error
curl http://localhost:8000/v1/chat/completions \
  -H "X-Mock-Scenario: delay=1200,error=server" \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-chat-v1","messages":[{"role":"user","content":"hello"}]}'

# truncate SSE stream without [DONE]
curl -N http://localhost:8000/v1/chat/completions \
  -H "X-Mock-Scenario: stream_truncate" \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-chat-v1","stream":true,"messages":[{"role":"user","content":"hello"}]}'
```

## Pytest integration

Myna ships with a pytest plugin that starts a local server and gives you helpers for URL
construction, scenario injection, request inspection, and response seeding.

Enable the plugin:

```python
# tests/conftest.py
pytest_plugins = ["myna.pytest_plugin"]
```

Or import the fixtures directly:

```python
from myna.pytest_plugin import myna, myna_base_url, myna_scenario, myna_url
```

### Typical test setup

```python
import os

from openai import OpenAI


def summarize(text: str) -> str:
    client = OpenAI(
        api_key=os.getenv("LLM_API_KEY", "mock"),
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:8000/v1"),
    )
    resp = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "mock-chat-v1"),
        messages=[{"role": "user", "content": text}],
    )
    return resp.choices[0].message.content or ""


def test_summarize_uses_mock_endpoint(myna_base_url, monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", myna_base_url)
    monkeypatch.setenv("LLM_API_KEY", "mock")
    monkeypatch.setenv("LLM_MODEL", "mock-chat-v1")

    out = summarize("hello from pytest")
    assert "Mock response" in out
```

### Scenario-aware tests

```python
import pytest


@pytest.mark.parametrize("myna_scenario", ["error=rate_limit"], indirect=True)
def test_retry_path_with_rate_limit(myna, monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", myna.base_url)
    headers = myna.headers()

    assert headers["X-Mock-Scenario"] == "error=rate_limit"
```

If your code accepts a path instead of a full URL:

```python
api_endpoint = myna.path_with_scenario("/audio/transcriptions", "error=rate_limit")
assert api_endpoint == "/audio/transcriptions?scenario=error%3Drate_limit"
```

### Request capture

Use the `myna` fixture to inspect what your application actually sent:

- `myna.last_request`: most recent request, or `None`
- `myna.requests`: all captured requests for the current test
- `myna.clear_requests()`: clear capture history

Captured request records include:

- `method`, `path`, `query`, `headers`, `content_type`
- `json` for JSON payloads
- `form` and `files` for form and multipart uploads
- `body_text` and `body_base64` for raw-body assertions

Example:

```python
def test_run_transcription_sends_correct_fields(myna, monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", myna.base_url)

    run_transcription(TEST_AUDIO)

    req = myna.last_request
    assert req is not None
    assert req.form["model"] == "whisper-mock"
    assert req.form["language"] == "nl"
    assert req.files["file"]["content_type"] == "audio/wav"
```

Internal instrumentation endpoints under `/__myna` power this feature. Requests to those
internal endpoints are not added to the capture log.

### One-shot seeded responses

For parser or error-path tests, seed the next matching response without patching your HTTP
client:

```python
def test_handles_empty_or_malformed_output(myna):
    myna.next_response(
        {"choices": [{"message": {"content": ""}}]},
        path="/chat/completions",
    )

    out = run_summary("input")
    assert out == ""
```

`myna.next_response(...)` matches by method and path and is consumed after one request.

Available helpers:

- `myna.base_url`
- `myna.headers(...)`
- `myna.path_with_scenario(...)`
- `myna.url_with_scenario(...)`
- `myna.last_request`
- `myna.requests`
- `myna.clear_requests()`
- `myna.next_response(...)`
- `myna.clear_seeded_responses()`
- `myna_url`
- `myna_base_url`
- `myna_scenario`

Scope notes:

- Use `myna` when you need request capture or seeded responses.
- Use `myna_url` when you only want the resolved base URL plus the `myna` helper lifecycle.
- Use `myna_base_url` for a session-scoped server when request inspection is not needed.

## Development

### Run tests

```bash
uv run pytest
```

## Changelog

Release history lives in [CHANGELOG.md](./CHANGELOG.md).
