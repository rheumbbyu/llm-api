# LLM Inference API

A small FastAPI server that serves text generation the way a production LLM API does: validated requests, structured responses, a model loaded once at startup, concurrency and rate limits, error handling, tests, and token streaming.

Built step by step for **Week 3B: Serving LLM Inference APIs with FastAPI** (Post-Graduate Certificate in Generative AI and Agentic AI). The "model" is an echo stub, so the whole API runs without a GPU or any model download.

To make the ideas easier to remember, these notes compare the API to a **hospital lab**.

---

## Quick start

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                   # install the exact locked dependencies
uv run uvicorn app.main:app --reload      # start the server
```

Then open:

| URL | What it is |
|---|---|
| http://localhost:8000/docs | Interactive API docs (Swagger UI) |
| http://localhost:8000/demo | Browser demo: watch tokens stream in |

Run the tests:

```bash
uv run pytest
```

---

## Endpoints

| Method | Path | Purpose | Hospital analogy |
|---|---|---|---|
| GET | `/` | Hello message | Front door greeting |
| GET | `/health` | Liveness check with uptime | Taking the hospital's pulse |
| GET | `/info` | Model name, version, max tokens | Sign on the door |
| GET | `/readiness` | 200 if the model is loaded, else 503 | "Is the machine calibrated yet?" |
| POST | `/v1/generate` | Generate text and return a full report | Submit a sample, get a lab report |
| GET | `/v1/generate/{request_id}` | Look up a past result | Find a result by its barcode |
| POST | `/v1/generate/stream` | Stream tokens as Server-Sent Events | Lab phones results through one at a time |
| GET | `/demo` | HTML page that shows the stream (hidden from `/docs`) | Viewing window into the lab |

### Example request

```bash
curl -X POST http://localhost:8000/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "Once upon a time"}'
```

```json
{
  "request_id": "3f9a1c2e-...",
  "generated_text": "[ECHO] Once upon a time",
  "prompt_tokens": 4,
  "completion_tokens": 5,
  "total_tokens": 9,
  "elapsed_ms": 50.24,
  "model": "echo-stub"
}
```

### Streaming

```bash
curl -N -X POST http://localhost:8000/v1/generate/stream \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "Tell me a story"}'
```

```
data: {"token": "[STREAM] "}

data: {"token": "Tell "}

...

data: [DONE]
```

---

## Project layout

```
llm-api/
├── app/
│   ├── main.py              # The building: app, lifespan, CORS, rate limiter, error handler, /demo
│   ├── engine.py            # The machine room: EchoEngine + ml_models
│   ├── limiter.py           # The sign-in sheet: shared rate limiter
│   ├── routers/
│   │   ├── health.py        # Admin wing: /health, /info, /readiness
│   │   └── generate.py      # Testing wing: /v1/generate, lookup, streaming
│   ├── schemas/
│   │   ├── request.py       # Intake form: GenerateRequest
│   │   └── response.py      # Lab report: GenerateResponse, APIError
│   └── static/
│       └── demo.html        # Streaming demo page
├── tests/
│   └── test_api.py          # Robot QC: automated tests
├── pyproject.toml           # Equipment list (dependencies)
└── uv.lock                  # Exact lot numbers (locked versions)
```

---

## What we built, exercise by exercise

### Exercise A: project setup with uv

- `uv init` created the project, and `uv add` installed FastAPI, Uvicorn and later slowapi.
- **`pyproject.toml`** is the equipment list. **`uv.lock`** records exact versions (the lot numbers), so anyone gets an identical setup.
- **`.venv`** is a clean room: this project's packages are kept separate from the rest of the computer.

### Exercise B: `/health` and `/info`

- A **router** is a wing of the hospital. `health.py` is the Admin wing.
- A router does nothing until `app.include_router(...)` puts it on the hospital map.
- `/health` uses `time.monotonic()` to report how long the server has been up.

### Exercise C: the `/v1/generate` endpoint

- **Request schema** (`GenerateRequest`): the intake form. `Field(...)` sets required fields and allowed ranges (e.g. `temperature` must be 0–2). Pydantic is the triage nurse: a bad form gets **422** before any work is done.
- **`field_validator`**: the empty-tube check. It strips whitespace and rejects prompts that are only spaces.
- **Response schema** (`GenerateResponse`): the standard lab report. It includes a `request_id` (barcode), token counts (for billing) and `elapsed_ms` (turnaround time).
- **Lookup by barcode**: every report is filed in an in-memory dict (`_history`), and `GET /v1/generate/{request_id}` returns it, or **404** if not found.

### Exercise D: loading the model

- **`EchoEngine`** lives in its own file. Swapping in a real LLM only means changing `engine.py`; the routes stay the same.
- **Lifespan**: the model is loaded once at startup (morning calibration) and released at shutdown, never once per request.
- **`async` / `await`**: while the model works, the server keeps serving other requests.
- **`/readiness`** returns **503** until the model is loaded, then `{"status": "ready"}`.
- `ml_models` lives in `engine.py`, not `main.py`, to avoid a **circular import**.

### Exercise E: production hardening

| Feature | How | Status code | Analogy |
|---|---|---|---|
| Concurrency limit | `asyncio.Semaphore(2)` | 503 + `Retry-After` | Only 2 machines; "we're full, come back shortly" |
| Timeout | `asyncio.wait_for(..., timeout=10)` | 504 | Stop waiting on a jammed machine |
| CORS | `CORSMiddleware`, localhost only | — | Approved list of referring clinics |
| Global error handler | `@app.exception_handler(Exception)` | 500 + `request_id` | Calm incident note for the patient; full report in the internal log |
| Rate limit (bonus) | slowapi, `5/minute` per IP | 429 | Each patient may submit 5 samples a minute |
| Tests | pytest + `TestClient` | — | Robot QC running control samples |

### Exercise F: streaming

- `token_generator` is an async **generator**: `yield` hands over one token at a time instead of `return`ing everything at once.
- `StreamingResponse` with `media_type="text/event-stream"` sends **Server-Sent Events**: each message is `data: ...` followed by a blank line, ending with `data: [DONE]`.
- `Cache-Control: no-cache` and `X-Accel-Buffering: no` stop proxies from bundling the tokens together.
- **Bonus:** `/demo` reads the stream with `fetch`. The slides suggest `EventSource`, but that only supports GET, and prompts should not go in URLs.

---

## Tests

`tests/test_api.py` runs four checks:

| Test | Checks |
|---|---|
| `test_health` | `/health` returns 200 and `status: ok` |
| `test_generate_echo` | A valid prompt returns a full report (positive control) |
| `test_empty_prompt_rejected` | A whitespace-only prompt gets 422 (negative control) |
| `test_rate_limit` | The 6th request in a minute gets 429 |

The `client` fixture opens the app with `with TestClient(app)`, so the lifespan runs and the model is loaded. It also calls `limiter.reset()` before each test, so one test's requests don't affect the next.

---

## Status codes used

| Code | Meaning here |
|---|---|
| 200 | Success |
| 404 | No result with that `request_id` |
| 422 | Request failed validation |
| 429 | Rate limit exceeded |
| 500 | Unexpected server error (with an incident `request_id`) |
| 503 | Server busy, or model not ready yet |
| 504 | Generation timed out |

---

## Ideas for next steps

- Replace `EchoEngine` with a real LLM (a Hugging Face model or a hosted API).
- Make streaming come from the engine instead of the router.
- Add request logging middleware (method, path, status, duration).
- Add a test for the streaming endpoint.
