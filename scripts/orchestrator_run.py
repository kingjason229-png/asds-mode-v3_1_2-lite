#!/usr/bin/env python3
"""
ASDS Lite orchestrator runtime for OpenClaw.
Single-task, serial, tasks.json-as-source-of-truth workflow.
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_PATH = Path(os.environ.get("ASDS_PROJECT_PATH", Path.home() / ".openclaw/workspace")).expanduser()
TASKS_FILE = PROJECT_PATH / "tasks.json"
DEMAND_FILE = PROJECT_PATH / "DEMAND.md"
PROGRESS_FILE = PROJECT_PATH / "PROGRESS.md"
PROJECT_AGENTS_FILE = PROJECT_PATH / "AGENTS.md"
DESIGN_FILE = PROJECT_PATH / "design.md"
CLARIFIED_DEMAND_FILE = PROJECT_PATH / "clarified-demand.md"
DELIVERY_NOTE_FILE = PROJECT_PATH / "delivery-note.md"

VALID_STATUSES = {"PENDING", "IN_PROGRESS", "DONE", "RETRY", "BLOCKED"}
STATUS_ALIASES = {
    "COMPLETED": "DONE",
    "RESOLVED": "DONE",
    "PASS": "DONE",
    "FAILED": "RETRY",
    "FAIL_RETRY": "RETRY",
    "ARCHIVED": "BLOCKED",
}
OPENCLAW_BIN = shutil.which("openclaw") or "/Users/kingjason/.npm-global/bin/openclaw"
DEFAULT_AGENT_TIMEOUT = int(os.environ.get("ASDS_AGENT_TIMEOUT", "900"))
MAX_RETRY_COUNT = int(os.environ.get("ASDS_MAX_RETRY_COUNT", "3"))
DEFAULT_VERIFICATION_COMMANDS = ["lint", "typecheck", "test", "build"]
DEFAULT_QA_TEMPLATE = {
    "result": None,
    "issue_level": None,
    "findings": [],
    "mapped_acceptance_criteria": {},
    "evidence": [],
    "next_action": None,
}
REQUIRED_QA_KEYS = set(DEFAULT_QA_TEMPLATE.keys())


def _deep_copy_json(value):
    import json as _json
    return _json.loads(_json.dumps(value, ensure_ascii=False))


def default_task_fields() -> dict:
    return {
        "task_type": "feature",
        "target_files": [],
        "verification_commands": list(DEFAULT_VERIFICATION_COMMANDS),
        "depends_on": [],
        "risk_level": "medium",
        "affected_files": [],
        "verification_summary": "",
        "verification_artifacts": [],
        "blocker_type": None,
        "notes": "",
        "design_doc": None,
        "reproduce": "",
        "root_cause": "",
        "minimal_fix": "",
        "regression_verify": "",
        "qa_result": _deep_copy_json(DEFAULT_QA_TEMPLATE),
        "closeout": {
            "done": False,
            "version_updated": False,
            "version_value": None,
            "change_summary": "",
            "delivery_note": None,
            "evidence_collected": False,
        },
    }


def merge_defaults(target: dict, defaults: dict) -> None:
    for key, value in defaults.items():
        if key not in target or target[key] is None:
            target[key] = _deep_copy_json(value)
        elif isinstance(value, dict) and isinstance(target[key], dict):
            merge_defaults(target[key], value)


def choose_design_doc() -> Optional[str]:
    for candidate in (DESIGN_FILE, CLARIFIED_DEMAND_FILE):
        if candidate.exists():
            return candidate.name
    return None


def normalize_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def ensure_closeout_defaults(task: dict) -> dict:
    closeout = task.get("closeout")
    if not isinstance(closeout, dict):
        closeout = {}
        task["closeout"] = closeout
    merge_defaults(task, default_task_fields())
    return closeout


def qa_result_is_structured(task: dict) -> bool:
    qa_result = task.get("qa_result")
    if not isinstance(qa_result, dict):
        return False
    if not REQUIRED_QA_KEYS.issubset(set(qa_result.keys())):
        return False
    result = qa_result.get("result")
    issue_level = qa_result.get("issue_level")
    findings = qa_result.get("findings")
    evidence = qa_result.get("evidence")
    mapped = qa_result.get("mapped_acceptance_criteria")
    if result not in {"PASS", "FAIL", "BLOCKED"}:
        return False
    if issue_level in (None, ""):
        return False
    if not isinstance(findings, list) or not isinstance(evidence, list) or not isinstance(mapped, dict):
        return False
    return True


def bugfix_has_root_cause(task: dict) -> bool:
    if task.get("task_type") != "bugfix":
        return True
    return bool(str(task.get("root_cause") or "").strip())


def build_change_summary(task: dict) -> str:
    closeout = ensure_closeout_defaults(task)
    summary = str(closeout.get("change_summary") or "").strip()
    if summary:
        return summary
    affected_files = normalize_list(task.get("affected_files"))
    verification_summary = str(task.get("verification_summary") or "").strip()
    parts = []
    if affected_files:
        parts.append(f"affected_files={', '.join(affected_files)}")
    if verification_summary:
        parts.append(f"verification={verification_summary}")
    if task.get("task_type") == "bugfix" and str(task.get("root_cause") or "").strip():
        parts.append(f"root_cause={str(task.get('root_cause')).strip()}")
    return '; '.join(parts) if parts else 'N/A'


def infer_version_value() -> Optional[str]:
    candidates = [
        PROJECT_PATH / 'package.json',
        PROJECT_PATH / 'app.json',
        PROJECT_PATH / 'pyproject.toml',
        PROJECT_PATH / 'Cargo.toml',
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            raw = candidate.read_text(encoding='utf-8')
        except Exception:
            continue
        if candidate.name in {'package.json', 'app.json'}:
            try:
                data = json.loads(raw)
                version = data.get('version')
                if isinstance(version, str) and version.strip():
                    return version.strip()
            except Exception:
                pass
        else:
            for line in raw.splitlines():
                stripped = line.strip()
                if stripped.startswith('version') and '=' in stripped:
                    value = stripped.split('=', 1)[1].strip().strip('"').strip("'")
                    if value:
                        return value
    return None


def ensure_delivery_note(task: dict) -> None:
    DELIVERY_NOTE_FILE.parent.mkdir(parents=True, exist_ok=True)
    closeout = ensure_closeout_defaults(task)
    lines = [
        f"## {task.get('id', 'TASK')} - {task.get('title', '')}",
        f"- closed_at: {now_iso()}",
        f"- task_type: {task.get('task_type', 'feature')}",
        f"- version_updated: {closeout.get('version_updated')}",
        f"- version_value: {closeout.get('version_value') or 'N/A'}",
        f"- change_summary: {build_change_summary(task)}",
        f"- affected_files: {', '.join(normalize_list(task.get('affected_files'))) or 'N/A'}",
        f"- verification_summary: {task.get('verification_summary') or 'N/A'}",
        f"- verification_artifacts: {', '.join(normalize_list(task.get('verification_artifacts'))) or 'N/A'}",
        "",
    ]
    with open(DELIVERY_NOTE_FILE, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))



def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_parent() -> None:
    PROJECT_PATH.mkdir(parents=True, exist_ok=True)


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def atomic_write_tasks(data) -> None:
    tmp = TASKS_FILE.with_suffix(TASKS_FILE.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(tmp, "r", encoding="utf-8") as f:
        json.load(f)
    os.replace(tmp, TASKS_FILE)


def append_progress(summary: str, validation: str = "N/A", artifacts: str = "N/A", next_step: str = "wait") -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    block = (
        f"## [orchestrator] - {now_iso()}\n"
        f"- status: INFO\n"
        f"- summary: {summary}\n"
        f"- validation: {validation}\n"
        f"- artifacts: {artifacts}\n"
        f"- next: {next_step}\n\n"
    )
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(block)


def ensure_project_agents() -> None:
    if PROJECT_AGENTS_FILE.exists():
        return
    template = """# AGENTS.md - Project validation rules for ASDS Lite

## Validation chain
- If available, run: lint
- If available, run: typecheck
- If available, run: test
- If available, run: build

## Write-back evidence
- coder should write `affected_files` for the current task.
- coder should write `verification_summary` with commands/results/N-A markers.
- coder should write `verification_artifacts` with log paths, build outputs, screenshots, or other concrete evidence when available.
- bugfix tasks should additionally write `reproduce`, `root_cause`, `minimal_fix`, and `regression_verify`.
- qa should write a structured `qa_result` object with `result`, `issue_level`, `findings`, `mapped_acceptance_criteria`, `evidence`, and `next_action`.
- orchestrator should complete lightweight `closeout` before final DONE, including delivery-note and evidence collection.

## Retry / blocked protocol
- If a task is `BLOCKED`, set `blocker_type` such as `user`, `env`, `spec`, or `retry_limit`.
- If a task reaches the retry limit, convert it to `BLOCKED` instead of retrying forever.
- When the blocker is resolved, resume the current ASDS Lite project from the main dialogue; orchestrator may reopen the blocked task back to `PENDING` / `IN_PROGRESS`.

## Notes
- Missing steps should be reported as N/A, not invented.
- At least one meaningful validation step should run before coder claims implementation complete.
- QA performs static business review only and does not re-run the full pipeline by default.
"""
    PROJECT_AGENTS_FILE.write_text(template, encoding="utf-8")


def demand_lines():
    if not DEMAND_FILE.exists():
        return []
    return [line.rstrip() for line in DEMAND_FILE.read_text(encoding="utf-8").splitlines()]


def extract_acceptance(lines):
    items = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("- ", "* ")):
            items.append(line[2:].strip())
        elif len(items) < 5 and not line.startswith("#"):
            items.append(line)
    return items[:5] or ["满足 DEMAND.md 中描述的核心需求", "交付结果可通过项目 AGENTS.md 定义的最小验证链"]


def init_from_demand() -> dict:
    if not DEMAND_FILE.exists():
        raise SystemExit(f"DEMAND.md not found: {DEMAND_FILE}")
    lines = demand_lines()
    title = next((line.lstrip('#').strip() for line in lines if line.strip()), "Implement DEMAND.md")
    task = {
        "id": "TASK-001",
        "title": title[:120],
        "description": f"实现 {DEMAND_FILE.name} 中定义的需求",
        "status": "PENDING",
        "priority": "high",
        "acceptance_criteria": extract_acceptance(lines),
        "retry_count": 0,
        "notes": "initialized from DEMAND.md",
        "createdAt": now_iso(),
    }
    merge_defaults(task, default_task_fields())
    task["design_doc"] = choose_design_doc()
    data = {"active_task_id": None, "tasks": [task]}
    atomic_write_tasks(data)
    append_progress("initialized tasks.json from DEMAND.md", artifacts=str(TASKS_FILE), next_step="activate first task")
    return data


def normalize_task(task: dict) -> dict:
    original_status = task.get("status")
    status = STATUS_ALIASES.get(original_status, original_status)
    if status not in VALID_STATUSES:
        status = "PENDING" if not original_status else "RETRY"
        note = f"normalized unsupported status from {original_status!r}"
        task["notes"] = (task.get("notes", "") + ("\n" if task.get("notes") else "") + note).strip()
    elif original_status in STATUS_ALIASES:
        note = f"normalized legacy status {original_status!r} -> {status!r}"
        task["notes"] = (task.get("notes", "") + ("\n" if task.get("notes") else "") + note).strip()
    task["status"] = status
    task.setdefault("title", task.get("description", task.get("id", "Untitled task"))[:120])
    task.setdefault("description", task.get("title", task.get("id", "")))
    task.setdefault("priority", "medium")
    task.setdefault("acceptance_criteria", [])
    task.setdefault("retry_count", 0)
    merge_defaults(task, default_task_fields())
    if not task.get("design_doc"):
        task["design_doc"] = choose_design_doc()
    return task


def normalize_tasks(data: dict) -> dict:
    data.setdefault("active_task_id", None)
    tasks = [normalize_task(task) for task in data.get("tasks", [])]
    data["tasks"] = tasks
    active_id = data.get("active_task_id")
    ids = {task.get("id") for task in tasks}
    if active_id not in ids:
        data["active_task_id"] = None
    active_tasks = [task for task in tasks if task.get("status") == "IN_PROGRESS"]
    if len(active_tasks) > 1:
        keeper = active_tasks[0]
        for extra in active_tasks[1:]:
            extra["status"] = "RETRY"
            extra["notes"] = (extra.get("notes", "") + "\nnormalized: multiple IN_PROGRESS tasks detected").strip()
        data["active_task_id"] = keeper.get("id")
    elif len(active_tasks) == 1:
        data["active_task_id"] = active_tasks[0].get("id")
    elif data.get("active_task_id"):
        task = next((t for t in tasks if t.get("id") == data["active_task_id"]), None)
        if not task or task.get("status") != "IN_PROGRESS":
            data["active_task_id"] = None
    return data


def read_or_init_tasks() -> dict:
    ensure_parent()
    ensure_project_agents()
    if not PROGRESS_FILE.exists():
        PROGRESS_FILE.write_text("# PROGRESS\n\n", encoding="utf-8")
    if TASKS_FILE.exists():
        data = normalize_tasks(read_json(TASKS_FILE))
        atomic_write_tasks(data)
        return data
    return init_from_demand()


def task_by_id(data: dict, task_id: str):
    return next((task for task in data.get("tasks", []) if task.get("id") == task_id), None)


def choose_next_task(data: dict):
    if data.get("active_task_id"):
        return task_by_id(data, data["active_task_id"])
    for task in data.get("tasks", []):
        if task.get("status") == "PENDING":
            return task
    return None


def activate_task(data: dict, task: dict) -> None:
    task["status"] = "IN_PROGRESS"
    task["updatedAt"] = now_iso()
    data["active_task_id"] = task["id"]
    atomic_write_tasks(data)
    append_progress(f"activated {task['id']}: {task.get('title','')}", artifacts=str(TASKS_FILE), next_step="dispatch coder")


def run_agent(agent_id: str, message: str):
    if not OPENCLAW_BIN or not Path(OPENCLAW_BIN).exists():
        raise RuntimeError(f"openclaw CLI not found: {OPENCLAW_BIN}")
    cmd = [OPENCLAW_BIN, "agent", "--agent", agent_id, "--message", message, "--timeout", str(DEFAULT_AGENT_TIMEOUT), "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=DEFAULT_AGENT_TIMEOUT + 60)
    if result.returncode != 0:
        raise RuntimeError(f"agent {agent_id} failed: {result.stderr or result.stdout}")
    stdout = result.stdout.strip()
    try:
        return json.loads(stdout) if stdout else {"raw": ""}
    except json.JSONDecodeError:
        return {"raw": stdout}


def dispatch_coder(task: dict) -> None:
    message = f"""You are the ASDS Lite coder for a single task.
Project path: {PROJECT_PATH}
Current task id: {task['id']}
Current task title: {task.get('title','')}
Rules:
- Read {TASKS_FILE} and {PROJECT_AGENTS_FILE}. Read {DEMAND_FILE} if it exists.
- Work ONLY on task {task['id']}.
- Implement the requirement.
- Run the project validation chain defined in AGENTS.md.
- Write results back to tasks.json atomically.
- Do NOT use FAILED. Allowed outcomes for your own write-back are keeping IN_PROGRESS with QA-ready notes, RETRY, or BLOCKED.
- Write your changed files into `affected_files`.
- Respect `target_files`, `verification_commands`, and `risk_level` when present; do not expand scope casually.
- Write your validation result summary into `verification_summary`.
- Write concrete evidence paths or artifacts into `verification_artifacts`.
- If `task_type` is `bugfix`, you MUST write non-empty strings for `reproduce`, `root_cause`, `minimal_fix`, and `regression_verify` before handing off to QA.
- If `task_type` is `bugfix` and any one of those four fields is empty, do NOT leave the task QA-ready and do NOT claim completion; set RETRY or BLOCKED with a precise explanation in `notes`.
- If you must block the task, set `blocker_type` and explain the blocker in notes.
- Put your implementation summary into task notes.
- Do NOT write PROGRESS.md.
Return a concise machine-readable summary in your final reply."""
    result = run_agent("coder", message)
    append_progress(f"coder finished for {task['id']}", validation="see tasks.json task notes", artifacts=json.dumps(result, ensure_ascii=False)[:1000], next_step="dispatch qa")


def dispatch_qa(task: dict) -> None:
    message = f"""You are the ASDS Lite QA for a single task.
Project path: {PROJECT_PATH}
Current task id: {task['id']}
Rules:
- Read {TASKS_FILE} and {PROJECT_AGENTS_FILE}. Read {DEMAND_FILE} if it exists.
- Review ONLY task {task['id']}.
- Perform static business review against acceptance_criteria, `affected_files`, `verification_summary`, and `verification_artifacts`.
- Write `qa_result` as a complete JSON object with EXACTLY this shape:
  {{
    "result": "PASS|FAIL|BLOCKED",
    "issue_level": "low|medium|high|critical",
    "findings": [],
    "mapped_acceptance_criteria": {{}},
    "evidence": [],
    "next_action": "..."
  }}
- Do NOT omit any qa_result key even when the value is empty.
- Do NOT edit code.
- Update tasks.json atomically and set the task to DONE, RETRY, or BLOCKED.
- If setting BLOCKED, write `blocker_type` and a concrete unblock condition.
- Do NOT use FAILED.
- Do NOT write PROGRESS.md.
Return a concise machine-readable summary in your final reply."""
    result = run_agent("qa", message)
    append_progress(f"qa finished for {task['id']}", validation="see tasks.json task notes", artifacts=json.dumps(result, ensure_ascii=False)[:1000], next_step="finalize task state")


def finalize_after_agents(task: dict) -> str:
    reloaded = normalize_tasks(read_json(TASKS_FILE))
    task = task_by_id(reloaded, task["id"])
    if not task:
        raise RuntimeError(f"active task disappeared: {task['id']}")
    status = task.get("status")
    if status == "RETRY":
        task["retry_count"] = int(task.get("retry_count", 0)) + 1
        task["updatedAt"] = now_iso()
        reloaded["active_task_id"] = None
        if task["retry_count"] >= MAX_RETRY_COUNT:
            task["status"] = "BLOCKED"
            task["blocker_type"] = task.get("blocker_type") or "retry_limit"
            note = f"retry limit reached ({task['retry_count']}/{MAX_RETRY_COUNT}); escalated to BLOCKED"
            task["notes"] = (task.get("notes", "") + ("\n" if task.get("notes") else "") + note).strip()
            atomic_write_tasks(reloaded)
            append_progress(f"task {task['id']} escalated to BLOCKED after retry limit", validation="qa requested retry repeatedly", artifacts=str(TASKS_FILE), next_step="wait for unblock")
            return f"BLOCKED {task['id']}"
        task["status"] = "PENDING"
        atomic_write_tasks(reloaded)
        append_progress(f"task {task['id']} returned for retry", validation="qa requested retry", artifacts=str(TASKS_FILE), next_step="fix task write-back issues, then rerun coder and qa")
        return f"RETRY {task['id']}"
    if status in {"DONE", "BLOCKED"}:
        reloaded["active_task_id"] = None
        task["updatedAt"] = now_iso()
        if status == "DONE":
            if not bugfix_has_root_cause(task):
                task["status"] = "RETRY"
                task["retry_count"] = int(task.get("retry_count", 0)) + 1
                note = "orchestrator gate: bugfix missing root_cause; refusing DONE"
                task["notes"] = (task.get("notes", "") + ("\n" if task.get("notes") else "") + note).strip()
                task["qa_result"]["result"] = task["qa_result"].get("result") or "FAIL"
                task["qa_result"]["issue_level"] = task["qa_result"].get("issue_level") or "high"
                task["qa_result"]["next_action"] = "fill root_cause and rerun coder/qa"
                atomic_write_tasks(reloaded)
                append_progress(f"task {task['id']} rejected from DONE", validation="bugfix missing root_cause", artifacts=str(TASKS_FILE), next_step="fill root_cause, rerun coder, then rerun qa")
                return f"RETRY {task['id']}"
            if not qa_result_is_structured(task):
                task["status"] = "RETRY"
                task["retry_count"] = int(task.get("retry_count", 0)) + 1
                note = "orchestrator gate: qa_result missing required structured fields; refusing DONE"
                task["notes"] = (task.get("notes", "") + ("\n" if task.get("notes") else "") + note).strip()
                atomic_write_tasks(reloaded)
                append_progress(f"task {task['id']} rejected from DONE", validation="qa_result incomplete", artifacts=str(TASKS_FILE), next_step="rewrite complete qa_result JSON, then rerun qa")
                return f"RETRY {task['id']}"
            task["blocker_type"] = None
            closeout = ensure_closeout_defaults(task)
            closeout["change_summary"] = build_change_summary(task)
            if not closeout.get("version_value"):
                closeout["version_value"] = infer_version_value()
            closeout["version_updated"] = bool(closeout.get("version_updated") or closeout.get("version_value"))
            closeout["evidence_collected"] = bool(task.get("verification_summary") or task.get("verification_artifacts"))
            ensure_delivery_note(task)
            closeout["done"] = True
            closeout["delivery_note"] = DELIVERY_NOTE_FILE.name
        elif not task.get("blocker_type"):
            task["blocker_type"] = "unspecified"
        atomic_write_tasks(reloaded)
        append_progress(f"task {task['id']} closed as {task['status']}", validation="qa final decision", artifacts=str(TASKS_FILE), next_step="stop")
        return f"{task['status']} {task['id']}"
    if status == "IN_PROGRESS":
        append_progress(f"task {task['id']} still IN_PROGRESS after agent run", validation="manual follow-up may be needed", artifacts=str(TASKS_FILE), next_step="stop")
        return f"IN_PROGRESS {task['id']}"
    atomic_write_tasks(reloaded)
    append_progress(f"task {task['id']} ended with unexpected status {status}", validation="normalized write-back completed", artifacts=str(TASKS_FILE), next_step="stop")
    return f"{status} {task['id']}"


def main() -> None:
    data = read_or_init_tasks()
    task = choose_next_task(data)
    if not task:
        append_progress("no pending task and no active task", artifacts=str(TASKS_FILE), next_step="exit")
        print("IDLE")
        return
    if task.get("status") == "PENDING":
        activate_task(data, task)
    else:
        append_progress(f"resuming active task {task['id']}", artifacts=str(TASKS_FILE), next_step="dispatch coder")
    task = task_by_id(normalize_tasks(read_json(TASKS_FILE)), task["id"])
    dispatch_coder(task)
    task = task_by_id(normalize_tasks(read_json(TASKS_FILE)), task["id"])
    if task and task.get("status") == "BLOCKED":
        print(finalize_after_agents(task))
        return
    dispatch_qa(task)
    print(finalize_after_agents(task))


if __name__ == "__main__":
    try:
        main()
    except subprocess.TimeoutExpired as exc:
        append_progress("agent timeout", validation="timeout", artifacts=str(exc), next_step="stop")
        raise SystemExit(f"TIMEOUT: {exc}")
    except Exception as exc:
        append_progress("orchestrator error", validation="exception", artifacts=repr(exc), next_step="stop")
        raise
