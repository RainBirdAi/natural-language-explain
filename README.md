# nl-explain

An HTTP service that turns a Rainbird session's **evidence** into a
human-readable, natural-language **explanation**.

Given a fact and session, it:

1. Accepts an HTTP request with `fact_id` and `session_id` (required), plus an
   optional `evidence_key` and an optional `language` ISO 639 code (defaults to
   `en`). The Rainbird base URL comes from the `RAINBIRD_API_URL` env var.
2. Fetches the reasoning evidence from the
   [Rainbird evidence endpoint](https://docs.rainbird.ai/rainbird/developer-docs/api-reference/evidence).
3. Removes synthetic facts from the evidence.
4. Normalises unix timestamps to a readable `dd-mm-yyyy` format.
5. Sends the processed evidence + the base prompt (`prompt.txt`) + the target
   language to **Google Gemini** (via Vertex AI) and returns the explanation.

## Project layout

```
app/
  main.py              # FastAPI app + /healthz
  config.py            # settings from env / .env
  models.py            # request/response schemas
  api/routes.py        # POST /explain pipeline
  services/
    rainbird.py        # (1-2) call the evidence endpoint
    evidence.py        # (3-4) strip synthetic facts + normalise dates
    gemini.py          # (5)   generate the explanation via Vertex AI
prompt.txt             # base prompt template sent to Gemini
tests/                 # unit tests for the evidence processing
```

## Requirements

- Python 3.12+
- A Google Cloud project with Vertex AI enabled, and credentials available via
  Application Default Credentials (ADC). Gemini is authenticated with **GCP
  roles**, not an API key.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # then fill in GCP_PROJECT_ID (and GCP_LOCATION if needed)

# Local GCP credentials (one-time):
gcloud auth application-default login
```

The authenticating principal needs the **Vertex AI User**
(`roles/aiplatform.user`) role on the project.

## Run

```bash
uvicorn app.main:app --reload
```

Interactive API docs: http://127.0.0.1:8000/docs

### Example request

```bash
curl -X POST http://127.0.0.1:8000/explain \
  -H 'Content-Type: application/json' \
  -d '{
    "fact_id": "<fact-id>",
    "session_id": "<session-id>"
  }'
```

`fact_id` and `session_id` are required; `evidence_key` (only needed when
evidence is secured in Rainbird) and `language` (defaults to `en`) are optional.
Add `?debug=true` to also receive the processed evidence in the response.

## Configuration

| Variable                   | Default            | Purpose                                            |
| -------------------------- | ------------------ | -------------------------------------------------- |
| `GCP_PROJECT_ID`           | _(required)_       | Google Cloud project for Vertex AI.                |
| `GCP_LOCATION`             | `global`           | Vertex AI location (model-dependent).              |
| `GEMINI_MODEL`             | `gemini-3.8-flash` | Gemini model used for the explanation.             |
| `GEMINI_TEMPERATURE`       | `0.2`              | Generation temperature.                            |
| `PROMPT_PATH`              | `prompt.txt`       | Path to the base prompt template.                  |
| `RAINBIRD_API_URL`         | _(required)_       | Base URL of the Rainbird API.                      |
| `RAINBIRD_TIMEOUT_SECONDS` | `30`               | HTTP timeout for the evidence request.             |

## Tests

```bash
pytest
```

## Processing notes

See [`app/services/evidence.py`](app/services/evidence.py).

- **Synthetic facts** are removed: any node whose `factID` begins with the
  literal prefix `WA:XX` is dropped (real facts use `WA:RF` / `WA:AF` / `WA:KF`).
- **Timestamps** are treated as epoch **milliseconds** (the Rainbird/JS
  convention) and normalised to `dd-mm-yyyy` wherever they appear: the `time`
  field, date-typed fact values (`dataType`/`type` = `date`), and flattened
  condition values (`objectType` = `date`).
