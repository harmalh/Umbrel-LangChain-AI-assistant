from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse

app = FastAPI()

DATA_DIR = Path(os.getenv("EAIA_DATA_DIR", "/data"))
CONFIG_PATH = DATA_DIR / "config" / "config.yaml"
SECRETS_PATH = DATA_DIR / "secrets" / "secrets.json"
ENV_PATH = DATA_DIR / "app.env"
LOG_DIR = DATA_DIR / "logs"
LANGGRAPH_PORT = int(os.getenv("EAIA_LANGGRAPH_PORT", "2024"))


def langgraph_up() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{LANGGRAPH_PORT}/openapi.json", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def read_text(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return fallback


def tail_log(name: str, lines: int = 40) -> str:
    path = LOG_DIR / name
    if not path.exists():
        return "(log file not found)"
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:]) if content else "(empty)"


def render_page(message: str = "") -> str:
    config_text = read_text(CONFIG_PATH, "")
    secrets_text = read_text(SECRETS_PATH, "")
    env_text = read_text(ENV_PATH, "")
    status = "running" if langgraph_up() else "starting or unavailable"

    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
  <title>Executive AI Assistant</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; margin: 2rem; line-height: 1.4; }}
    h1, h2 {{ margin-bottom: 0.4rem; }}
    textarea {{ width: 100%; min-height: 14rem; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    pre {{ background: #f5f5f5; padding: 1rem; overflow: auto; white-space: pre-wrap; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 1.5rem; }}
    .card {{ border: 1px solid #ddd; border-radius: 12px; padding: 1rem; }}
    .muted {{ color: #555; }}
    .msg {{ padding: 0.75rem 1rem; background: #f3f7ff; border-radius: 10px; margin-bottom: 1rem; }}
    button {{ padding: 0.6rem 1rem; border-radius: 8px; border: 1px solid #aaa; background: white; cursor: pointer; }}
    code {{ background: #f5f5f5; padding: 0.1rem 0.3rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Executive AI Assistant</h1>
  <p class=\"muted\">Umbrel wrapper for LangChain's archived executive-ai-assistant project.</p>
  {f'<div class="msg">{message}</div>' if message else ''}

  <div class=\"card\">
    <h2>Status</h2>
    <p><strong>LangGraph API:</strong> {status}</p>
    <p><strong>Config file:</strong> <code>{CONFIG_PATH}</code></p>
    <p><strong>OAuth client JSON:</strong> <code>{SECRETS_PATH}</code></p>
    <p><strong>Environment file:</strong> <code>{ENV_PATH}</code></p>
    <p class=\"muted\">After saving <code>app.env</code>, restart the app from Umbrel so the updated environment is loaded.</p>
  </div>

  <div class=\"grid\">
    <div class=\"card\">
      <h2>1) Save config.yaml</h2>
      <form method=\"post\" action=\"/save-config\">
        <textarea name=\"content\">{config_text}</textarea>
        <p><button type=\"submit\">Save config.yaml</button></p>
      </form>
    </div>

    <div class=\"card\">
      <h2>2) Save Google OAuth client JSON</h2>
      <form method=\"post\" action=\"/save-secrets\">
        <textarea name=\"content\">{secrets_text}</textarea>
        <p><button type=\"submit\">Save secrets.json</button></p>
      </form>
    </div>

    <div class=\"card\">
      <h2>3) Save app.env</h2>
      <p class=\"muted\">Set <code>LANGSMITH_API_KEY</code>, <code>OPENAI_API_KEY</code> and/or <code>ANTHROPIC_API_KEY</code>. You can also set <code>EAIA_APPROVAL_MODE=auto_accept</code> and enable the poller.</p>
      <form method=\"post\" action=\"/save-env\">
        <textarea name=\"content\">{env_text}</textarea>
        <p><button type=\"submit\">Save app.env</button></p>
      </form>
    </div>

    <div class=\"card\">
      <h2>4) Manual ingest</h2>
      <form method=\"post\" action=\"/run-ingest\">
        <label>Minutes since: <input type=\"number\" name=\"minutes_since\" value=\"120\" min=\"1\"></label>
        <button type=\"submit\">Run ingest now</button>
      </form>
      <p class=\"muted\">This calls <code>python scripts/run_ingest.py</code> inside the container.</p>
    </div>

    <div class=\"card\">
      <h2>Notes</h2>
      <ul>
        <li><strong>agent_inbox</strong> mode stays closest to upstream. Use Agent Inbox for approvals.</li>
        <li><strong>auto_accept</strong> lets drafted emails and calendar invites continue without manual approval.</li>
        <li>The upstream project still depends on LangSmith / LangChain Auth for Google OAuth.</li>
      </ul>
    </div>

    <div class=\"card\">
      <h2>Recent logs: langgraph.log</h2>
      <pre>{tail_log("langgraph.log")}</pre>
    </div>

    <div class=\"card\">
      <h2>Recent logs: poller.log</h2>
      <pre>{tail_log("poller.log")}</pre>
    </div>
  </div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return HTMLResponse(render_page())


@app.post("/save-config")
async def save_config(content: str = Form(...)) -> RedirectResponse:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(content.strip() + "\n", encoding="utf-8")
    return RedirectResponse("/?message=Saved+config.yaml", status_code=303)


@app.post("/save-secrets")
async def save_secrets(content: str = Form(...)) -> RedirectResponse:
    parsed = json.loads(content)
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SECRETS_PATH.write_text(json.dumps(parsed, indent=2) + "\n", encoding="utf-8")
    return RedirectResponse("/?message=Saved+secrets.json", status_code=303)


@app.post("/save-env")
async def save_env(content: str = Form(...)) -> RedirectResponse:
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text(content.strip() + "\n", encoding="utf-8")
    return RedirectResponse("/?message=Saved+app.env.+Restart+the+app+from+Umbrel+to+load+changes", status_code=303)


@app.post("/run-ingest")
async def run_ingest(minutes_since: int = Form(...)) -> RedirectResponse:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "poller.log"
    with log_path.open("a", encoding="utf-8") as handle:
        subprocess.Popen(
            [
                "python",
                "scripts/run_ingest.py",
                "--minutes-since",
                str(minutes_since),
                "--early",
                "1",
                "--rerun",
                "0",
            ],
            cwd="/app/eaia-upstream",
            stdout=handle,
            stderr=handle,
        )
    return RedirectResponse("/?message=Started+manual+ingest.+Refresh+logs+below+in+a+moment", status_code=303)


@app.get("/healthz", response_class=PlainTextResponse)
async def healthz() -> str:
    return "ok"
