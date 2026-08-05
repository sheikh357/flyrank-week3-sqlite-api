import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from swagger_ui_bundle import __file__ as swagger_ui_bundle_file


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small SQLite-backed CRUD API for FlyRank Week 3.",
    docs_url=None,
    redoc_url=None,
)
app.openapi_version = "3.0.3"

swagger_assets_path = Path(swagger_ui_bundle_file).resolve().parent / "vendor" / "swagger-ui-4.15.5"
app.mount("/swagger-assets", StaticFiles(directory=str(swagger_assets_path)), name="swagger-assets")

DATABASE_PATH = Path(__file__).resolve().parent.parent / "tasks.db"
SEED_TASKS = [
    ("Learn FastAPI basics", 0),
    ("Build CRUD endpoints", 0),
    ("Test in Swagger UI", 1),
]


class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="Task title")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be empty")
        return cleaned


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, description="Task title")
    done: Optional[bool] = Field(default=None, description="Task completion status")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be empty")
        return cleaned


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def row_to_task(row: sqlite3.Row) -> Task:
    return Task(id=row["id"], title=row["title"], done=bool(row["done"]))


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                done INTEGER NOT NULL CHECK (done IN (0, 1))
            )
            """
        )

        row_count = connection.execute("SELECT COUNT(*) AS count FROM tasks").fetchone()["count"]
        if row_count == 0:
            connection.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                SEED_TASKS,
            )


initialize_database()


def not_found_response() -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": "Task not found"})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    message = exc.errors()[0]["msg"] if exc.errors() else "Invalid request body"
    return JSONResponse(status_code=400, content={"error": f"Invalid request body: {message}"})


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Task API - Swagger UI",
        swagger_js_url="/swagger-assets/swagger-ui-bundle.js",
        swagger_css_url="/swagger-assets/swagger-ui.css",
        swagger_favicon_url="/swagger-assets/favicon-32x32.png",
    )


@app.get("/", summary="Get API metadata", description="Return basic metadata about the API.")
def root() -> dict:
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check", description="Confirm the API is running.")
def health() -> dict:
    return {"status": "ok"}


@app.get("/tasks", summary="List tasks", description="Return every task currently stored in SQLite.", response_model=list[Task])
def list_tasks() -> list[Task]:
    with get_connection() as connection:
        rows = connection.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    return [row_to_task(row) for row in rows]


@app.get("/tasks/{task_id}", summary="Get one task", description="Return one task by id.", response_model=Task)
def get_task(task_id: int):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    if row is None:
        return not_found_response()
    return row_to_task(row)


@app.post("/tasks", summary="Create a task", description="Create a new task with a title.", status_code=201, response_model=Task)
def create_task(payload: TaskCreate) -> Task:
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            (payload.title, 0),
        )
        task_id = cursor.lastrowid
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    return row_to_task(row)


@app.put("/tasks/{task_id}", summary="Update a task", description="Update a task's title and/or done status.", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    if payload.title is None and payload.done is None:
        return JSONResponse(status_code=400, content={"error": "Task update must include title and/or done"})

    with get_connection() as connection:
        current_row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if current_row is None:
            return not_found_response()

        current_task = row_to_task(current_row)
        updated_task = current_task.model_copy(update=payload.model_dump(exclude_unset=True))

        connection.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (updated_task.title, int(updated_task.done), task_id),
        )

    return updated_task


@app.delete("/tasks/{task_id}", summary="Delete a task", description="Remove a task from SQLite.", status_code=204)
def delete_task(task_id: int) -> Response:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    if cursor.rowcount == 0:
        return not_found_response()

    return Response(status_code=204)
