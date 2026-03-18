# myna

`myna` is a local FastAPI server that mimics core OpenAI-compatible REST API endpoints for
development and automated testing.

## Run locally

```bash
uv sync
uv run uvicorn myna.main:app --reload --port 8000
```

## SDK usage (Python and JS)

You can keep this in `README` for now. A dedicated docs page is only useful once this
section becomes large or versioned.

### Python (openai SDK)

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

### JavaScript/TypeScript (openai SDK)

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

## Endpoints

- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/completions`
- `POST /v1/embeddings`
- `POST /v1/images/generations`
- `POST /v1/audio/speech`
- `POST /v1/audio/transcriptions`
- `POST /v1/audio/translations`

## Scenario header

Use `X-Mock-Scenario` (or `?scenario=`) to inject delays and failures.

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer test" \
  -H "X-Mock-Scenario: delay=500,error=rate_limit" \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-chat-v1","messages":[{"role":"user","content":"hi"}]}'
```

## Examples

### List models

```bash
curl http://localhost:8000/v1/models
```

### Chat completion (non-streaming)

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

### Chat completion (streaming SSE)

```bash
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"mock-chat-v1",
    "stream":true,
    "messages":[{"role":"user","content":"Stream this response."}]
  }'
```

### JSON mode using tool schema

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"mock-chat-v1",
    "response_format":{"type":"json_object"},
    "messages":[{"role":"user","content":"Return structured output"}],
    "tools":[
      {
        "type":"function",
        "function":{
          "name":"create_item",
          "parameters":{
            "type":"object",
            "properties":{
              "title":{"type":"string"},
              "priority":{"type":"integer"},
              "done":{"type":"boolean"}
            }
          }
        }
      }
    ]
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

### Image generation (url vs base64)

```bash
curl http://localhost:8000/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a cat in a bike basket","response_format":"url"}'

curl http://localhost:8000/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a cat in a bike basket","response_format":"b64_json"}'
```

### Audio speech (wav or mp3)

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

### Scenario examples

```bash
# deterministic auth error
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

## Using Myna as pytest mock endpoint for your tool

If your code under test calls an LLM endpoint over HTTP, load the built-in Myna pytest
fixtures and inject its base URL via env var/config.

```python
# tests/conftest.py
pytest_plugins = ["myna.pytest_plugin"]
```

Or import fixtures directly in `conftest.py`:

```python
from myna.pytest_plugin import myna, myna_base_url, myna_scenario
```

```python
# app/tool.py
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
```

```python
# tests/test_tool.py
import os

from app.tool import summarize


def test_summarize_uses_mock_endpoint(myna_base_url):
    os.environ["LLM_BASE_URL"] = myna_base_url
    os.environ["LLM_API_KEY"] = "mock"
    os.environ["LLM_MODEL"] = "mock-chat-v1"

    out = summarize("hello from pytest")
    assert "Mock response" in out
```

```python
# tests/test_tool_errors.py
import os
import pytest

from app.tool import summarize


@pytest.mark.parametrize("myna_scenario", ["error=rate_limit"], indirect=True)
def test_retry_path_with_rate_limit(myna, monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", myna.base_url)
    monkeypatch.setenv("LLM_API_KEY", "mock")
    monkeypatch.setenv("LLM_MODEL", "mock-chat-v1")

    # Use myna.headers() or myna.url_with_scenario() in your HTTP client path.
    # For OpenAI SDK wrappers, pass scenario headers through your transport hook.
    headers = myna.headers()
    assert headers["X-Mock-Scenario"] == "error=rate_limit"
```

Provided fixtures:
- `myna_base_url`: starts one Myna server per test session and returns `/v1` base URL.
- `myna_scenario`: optional indirect-param fixture for scenario strings.
- `myna`: helper object with `base_url`, `headers(...)`, and `url_with_scenario(...)`.

## Tests

```bash
uv run pytest
```

## Publish to GitHub and PyPI

### 1) Create git repo and push to GitHub

```bash
git init
git add .
git commit -m "Initial release: myna mock API server"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 2) Configure PyPI trusted publishing

In PyPI:
- Create project `myna` (or claim name if available).
- Go to project settings > Publishing.
- Add a trusted publisher with:
- Owner: your GitHub org/user
- Repository: your repo name
- Workflow: `.github/workflows/ci-publish.yml`
- Environment: `pypi`

In GitHub:
- Repo settings > Environments > create environment `pypi`.

### 3) Release by pushing a version tag

Version comes from `pyproject.toml` (`[project].version`).

```bash
git tag v0.1.0
git push origin v0.1.0
```

This triggers GitHub Actions to run lint/tests and publish to PyPI on tag push.
