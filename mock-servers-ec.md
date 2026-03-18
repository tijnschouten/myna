# Myna — Technische Omschrijving

**Project:** `myna`  
**Stack:** Python 3.12, FastAPI, uv, Ruff, pytest  
**Doel:** Lokale, volledig geparametriseerde nep-implementatie van de OpenAI REST API voor ontwikkeling en geautomatiseerd testen.

---

## 1. Doelstelling

Een zelfgehoste HTTP-server die de OpenAI API-interface nabootst zonder echte modelaanroepen te doen. Applicaties hoeven enkel `base_url` aan te passen; alle SDK-aanroepen (Python, JS, curl) werken ongewijzigd. De server ondersteunt happy-path dummy-responses, streaming SSE, JSON-schema-aware output, en geparametriseerde foutinjectie voor sad-path testing.

---

## 2. Ondersteunde Endpoints

| Endpoint | Methode | Bijzonderheden |
|---|---|---|
| `/v1/models` | GET | Geeft vaste modellijst terug |
| `/v1/chat/completions` | POST | Normaal + streaming SSE + JSON mode |
| `/v1/embeddings` | POST | Geeft vector van floats terug (configureerbare dimensie) |
| `/v1/images/generations` | POST | Geeft placeholder-URL of base64 stub terug |
| `/v1/audio/speech` | POST | Geeft WAV/MP3 stub terug (silence of toon) |
| `/v1/audio/transcriptions` | POST | Geeft dummy transcriptietekst terug |
| `/v1/audio/translations` | POST | Idem, vertaald naar Engels dummy-tekst |
| `/v1/completions` | POST | Legacy text completion (doorgestuurd naar chat-logica) |

---

## 3. Scenario-systeem (foutinjectie)

Gedrag wordt gestuurd via de `X-Mock-Scenario` request-header (of identieke querystring `?scenario=`). Dit maakt tests volledig deterministisch.

### Formaat

```
X-Mock-Scenario: <scenario>[,<scenario>...]
```

Meerdere scenario's zijn combineerbaar. De **eerste fout**-scenario die matcht wint.

### Beschikbare scenario's

| Scenario | Omschrijving |
|---|---|
| *(geen header)* | Happy path: geldige dummy-response |
| `error=rate_limit` | HTTP 429 met `error.type: rate_limit_exceeded` |
| `error=auth` | HTTP 401 met `error.type: invalid_api_key` |
| `error=context_length` | HTTP 400 met `error.type: context_length_exceeded` |
| `error=server` | HTTP 500 met `error.type: server_error` |
| `error=timeout` | Wacht `delay_ms` ms, daarna HTTP 504 |
| `delay=<ms>` | Voegt vertraging toe vóór normale response (bijv. `delay=2000`) |
| `stream_truncate` | SSE-stream stopt halverwege, zonder `[DONE]` |
| `json_invalid` | Geeft syntactisch ongeldige JSON terug (voor JSON mode) |
| `empty_choices` | Geeft lege `choices: []` array terug |
| `chaos=<0..1>` | Kans per request dat een willekeurig foutscenario getriggerd wordt |

### Voorbeeld

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer test" \
  -H "X-Mock-Scenario: delay=500,error=rate_limit" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"hoi"}]}'
```

---

## 4. JSON Mode

Wanneer de request `response_format: { type: "json_object" }` bevat, inspecteert de mock het gevraagde schema (indien meegestuurd als system prompt of tool-definitie) en genereert een syntactisch kloppend JSON-object met dummy-waarden per type:

| JSON Schema type | Dummy waarde |
|---|---|
| `string` | `"lorem ipsum"` |
| `integer` | `42` |
| `number` | `3.14` |
| `boolean` | `true` |
| `array` | `["item_1", "item_2"]` |
| `object` | Recursief gevuld op basis van `properties` |

Bij scenario `json_invalid` wordt expres malformed JSON teruggegeven (ontbrekende sluithaak e.d.).

---

## 5. Streaming (SSE)

Bij `stream: true` in de request stuurt de server een `text/event-stream` response die het OpenAI chunk-formaat nabootst:

```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"delta":{"content":"Lorem"},...}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"delta":{"content":" ipsum"},...}]}

data: [DONE]
```

Tokens worden één voor één gestreamd met een configureerbare `chunk_delay_ms` (standaard: 30 ms). Bij scenario `stream_truncate` stopt de stream na 3 chunks zonder `[DONE]`.

---

## 6. Projectstructuur

```
myna/
├── pyproject.toml          # uv + ruff + pytest config
├── .python-version         # 3.12
├── src/
│   └── myna/
│       ├── main.py         # FastAPI app factory
│       ├── config.py       # Settings via pydantic-settings
│       ├── scenarios.py    # Scenario-parsing en -dispatching
│       ├── generators.py   # Dummy-data generatie (tekst, JSON, audio)
│       ├── routers/
│       │   ├── chat.py
│       │   ├── embeddings.py
│       │   ├── images.py
│       │   ├── audio.py
│       │   └── models.py
│       └── middleware/
│           └── scenario_middleware.py
└── tests/
    ├── conftest.py          # TestClient fixture
    ├── test_chat.py
    ├── test_streaming.py
    ├── test_scenarios.py
    └── test_json_mode.py
```

---

## 7. Configuratie

Via omgevingsvariabelen (of `.env`), beheerd met `pydantic-settings`:

| Variabele | Default | Omschrijving |
|---|---|---|
| `MOCK_PORT` | `8000` | Luisterpoort |
| `MOCK_DEFAULT_MODEL` | `gpt-4o` | Model in responses |
| `MOCK_CHUNK_DELAY_MS` | `30` | Vertraging per SSE-chunk |
| `MOCK_EMBEDDING_DIMS` | `1536` | Grootte embedding-vector |
| `MOCK_REQUIRE_AUTH` | `false` | Valideer `Authorization`-header |
| `MOCK_CHAOS_RATE` | `0.0` | Globale chaos-kans (0–1) |
| `MOCK_LOG_REQUESTS` | `true` | Log inkomende requests naar stdout |

---

## 8. Tooling & standaarden

### Package management — uv

```bash
uv sync              # installeer dependencies
uv run uvicorn myna.main:app --reload
```

### Linting & formatting — Ruff

Geconfigureerd in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
```

Pre-commit hook via `ruff check . && ruff format .`.

### Testen — pytest

```bash
uv run pytest              # alle tests
uv run pytest -k streaming # gefilterd
uv run pytest --cov=myna
```

Conventies:
- Elke router heeft een bijbehorend testbestand
- Scenarios worden getest via parametrize over alle foutcodes
- Streaming tests valideren chunk-volgorde en aanwezigheid van `[DONE]`
- Geen echte netwerkaanroepen: alleen `TestClient` (HTTPX)

---

## 9. Starten

```bash
# Lokaal
uv run uvicorn myna.main:app --port 8000

# Docker
docker build -t myna .
docker run -p 8000:8000 -e MOCK_CHAOS_RATE=0.1 myna
```

Gebruik in applicatie:

```python
from openai import OpenAI

client = OpenAI(
    api_key="mock",
    base_url="http://localhost:8000/v1"
)
```

---

## 10. Uitbreidingen (buiten scope v1)

- Anthropic API-compatibiliteitslaag (`/v1/messages`)
- Stateful conversatiegeheugen (context bijhouden over turns)
- Web UI voor scenario-configuratie per endpoint
- OpenTelemetry-tracing van mock-requests
