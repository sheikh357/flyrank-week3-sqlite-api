# Task API

This is a small FastAPI CRUD API for the FlyRank Week 2 assignment. It manages tasks entirely in memory and exposes interactive Swagger UI at `/docs`.

## Setup

1. Create and activate a virtual environment on Windows:
   - `python -m venv .venv`
   - `.venv\\Scripts\\activate`
2. Install dependencies:
   - `pip install -r requirements.txt`

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## Endpoints

| Method | Path | Description | Success Code |
| --- | --- | --- | --- |
| GET | `/` | API metadata | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/tasks` | List all tasks | 200 |
| GET | `/tasks/{task_id}` | Get one task | 200 |
| POST | `/tasks` | Create a task | 201 |
| PUT | `/tasks/{task_id}` | Update a task | 200 |
| DELETE | `/tasks/{task_id}` | Delete a task | 204 |

## Sample `curl -i`

```bash
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d "{\"title\":\"Buy milk\"}"
```

Expected response:

```text
HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

## Swagger UI

Open `http://localhost:8000/docs` to try the full CRUD flow.

![Swagger UI screenshot](docs-screenshot.png)

## Notes

- Data is stored only in memory, so it resets when the server restarts.
- POST and PUT validate input and return JSON errors for bad requests.
- Unknown task IDs return 404 with a JSON error message.

## AI vs Me

To be completed in Stage 7 after running a separate AI-generated version in quarantine.
