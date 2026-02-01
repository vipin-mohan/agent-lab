import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Task API")

TASKS_FILE = Path(__file__).parent / "tasks.json"

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tasks</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: system-ui, sans-serif;
      background: #1e293b;
      color: #e2e8f0;
      margin: 2rem;
      max-width: 32rem;
    }
    h1 { color: #f8fafc; margin-bottom: 1rem; }
    input[type="text"] {
      padding: 0.5rem 0.75rem;
      border: 1px solid #475569;
      border-radius: 6px;
      background: #334155;
      color: #f1f5f9;
      width: 100%;
      margin-bottom: 0.75rem;
    }
    input[type="text"]::placeholder { color: #94a3b8; }
    button {
      padding: 0.5rem 1rem;
      border: none;
      border-radius: 6px;
      background: #0f766e;
      color: #f0fdfa;
      cursor: pointer;
      margin-right: 0.5rem;
      margin-bottom: 0.5rem;
    }
    button:hover { background: #115e59; }
    #deleteBtn { background: #b91c1c; color: #fef2f2; }
    #deleteBtn:hover { background: #991b1b; }
    #taskList {
      list-style: none;
      padding-left: 0;
      margin-top: 1.5rem;
    }
    #taskList li {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 0;
      border-bottom: 1px solid #334155;
    }
    #taskList input[type="checkbox"] {
      width: 1.1rem;
      height: 1.1rem;
      accent-color: #0f766e;
    }
  </style>
</head>
<body>
  <h1>Tasks</h1>
  <div>
    <input type="text" id="taskInput" placeholder="Enter a task" />
    <button id="addBtn">Add task</button>
    <button id="listBtn">List tasks</button>
    <button id="deleteBtn">Delete selected</button>
  </div>
  <ul id="taskList"></ul>

  <script>
    const input = document.getElementById("taskInput");
    const addBtn = document.getElementById("addBtn");
    const listBtn = document.getElementById("listBtn");
    const deleteBtn = document.getElementById("deleteBtn");
    const list = document.getElementById("taskList");

    function loadTasks() {
      fetch("/tasks")
        .then(r => r.json())
        .then(tasks => {
          list.innerHTML = "";
          tasks.forEach(t => {
            const li = document.createElement("li");
            const cb = document.createElement("input");
            cb.type = "checkbox";
            cb.dataset.id = t.id;
            li.appendChild(cb);
            li.appendChild(document.createTextNode(" " + t.text));
            list.appendChild(li);
          });
        });
    }

    function addTask() {
      const text = input.value.trim();
      if (!text) return;
      fetch("/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text })
      })
        .then(r => r.json())
        .then(() => {
          input.value = "";
          loadTasks();
        });
    }

    function deleteSelected() {
      const ids = Array.from(list.querySelectorAll('input[type="checkbox"]:checked'))
        .map(cb => parseInt(cb.dataset.id, 10));
      if (ids.length === 0) return;
      fetch("/tasks", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: ids })
      })
        .then(() => loadTasks());
    }

    addBtn.addEventListener("click", addTask);
    listBtn.addEventListener("click", loadTasks);
    deleteBtn.addEventListener("click", deleteSelected);
    input.addEventListener("keydown", e => { if (e.key === "Enter") addTask(); });
    loadTasks();
  </script>
</body>
</html>
"""

# In-memory task storage (loaded from / saved to tasks.json)
tasks: list[dict] = []


def load_tasks_from_file() -> list[dict]:
    """Load tasks from tasks.json. Returns empty list if file missing or invalid."""
    if not TASKS_FILE.exists():
        return []
    try:
        data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_tasks_to_file() -> None:
    """Write current tasks to tasks.json."""
    TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")


def _ensure_tasks_loaded() -> None:
    """Load tasks from file once if in-memory list is empty."""
    global tasks
    if not tasks and TASKS_FILE.exists():
        tasks = load_tasks_from_file()


class TaskCreate(BaseModel):
    text: str


class Task(BaseModel):
    id: int
    text: str


class TaskDelete(BaseModel):
    ids: list[int]


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the task list UI."""
    return HTML_PAGE


@app.post("/tasks", response_model=Task)
def add_task(task: TaskCreate):
    """Add a new task."""
    _ensure_tasks_loaded()
    task_id = max((t["id"] for t in tasks), default=0) + 1
    new_task = {"id": task_id, "text": task.text}
    tasks.append(new_task)
    save_tasks_to_file()
    return new_task


@app.get("/tasks", response_model=list[Task])
def list_tasks():
    """List all tasks."""
    _ensure_tasks_loaded()
    return tasks


@app.delete("/tasks")
def delete_tasks(body: TaskDelete):
    """Delete tasks by ID."""
    _ensure_tasks_loaded()
    ids = set(body.ids)
    tasks[:] = [t for t in tasks if t["id"] not in ids]
    save_tasks_to_file()
    return {"deleted": len(ids)}


if __name__ == "__main__":
    tasks[:] = load_tasks_from_file()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
