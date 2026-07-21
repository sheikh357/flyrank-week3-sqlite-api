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
    description="A small in-memory CRUD API for FlyRank Week 2.",
    docs_url=None,
    redoc_url=None,
)
app.openapi_version = "3.0.3"

swagger_assets_path = Path(swagger_ui_bundle_file).resolve().parent / "vendor" / "swagger-ui-4.15.5"
app.mount("/swagger-assets", StaticFiles(directory=str(swagger_assets_path)), name="swagger-assets")


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


tasks: list[Task] = [
    Task(id=1, title="Learn FastAPI basics", done=False),
    Task(id=2, title="Build CRUD endpoints", done=False),
    Task(id=3, title="Test in Swagger UI", done=True),
]


def find_task_index(task_id: int) -> Optional[int]:
    for index, task in enumerate(tasks):
        if task.id == task_id:
            return index
    return None


def not_found_response(task_id: int) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": f"Task {task_id} not found"})


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


@app.get("/tasks", summary="List tasks", description="Return every task currently stored in memory.", response_model=list[Task])
def list_tasks() -> list[Task]:
    return tasks


@app.get("/tasks/{task_id}", summary="Get one task", description="Return one task by id.", response_model=Task)
def get_task(task_id: int):
    index = find_task_index(task_id)
    if index is None:
        return not_found_response(task_id)
    return tasks[index]


@app.post("/tasks", summary="Create a task", description="Create a new task with a title.", status_code=201, response_model=Task)
def create_task(payload: TaskCreate) -> Task:
    next_id = max((task.id for task in tasks), default=0) + 1
    task = Task(id=next_id, title=payload.title, done=False)
    tasks.append(task)
    return task


@app.put("/tasks/{task_id}", summary="Update a task", description="Update a task's title and/or done status.", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    index = find_task_index(task_id)
    if index is None:
        return not_found_response(task_id)

    if payload.title is None and payload.done is None:
        return JSONResponse(status_code=400, content={"error": "Task update must include title and/or done"})

    updated_task = tasks[index].model_copy(update=payload.model_dump(exclude_unset=True))
    tasks[index] = updated_task
    return updated_task


@app.delete("/tasks/{task_id}", summary="Delete a task", description="Remove a task from memory.", status_code=204)
def delete_task(task_id: int) -> Response:
    index = find_task_index(task_id)
    if index is None:
        return not_found_response(task_id)

    tasks.pop(index)
    return Response(status_code=204)
