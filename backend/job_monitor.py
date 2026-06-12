from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .db import ROOT_DIR


@dataclass(frozen=True)
class ScriptProcess:
    pid: int
    age_seconds: int
    command: str


def running_script_processes(script_names: list[str]) -> list[ScriptProcess]:
    names = [name for name in script_names if name]
    if not names:
        return []
    try:
        completed = subprocess.run(
            ["ps", "-axo", "pid=,etimes=,command="],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    current_pid = os.getpid()
    processes: list[ScriptProcess] = []
    for line in completed.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            age_seconds = int(parts[1])
        except ValueError:
            continue
        command = parts[2]
        if pid == current_pid:
            continue
        if any(name in command for name in names):
            processes.append(ScriptProcess(pid=pid, age_seconds=age_seconds, command=command))
    return processes


def terminate_script_processes(
    script_names: list[str],
    *,
    min_age_seconds: int = 0,
    grace_seconds: float = 3.0,
) -> list[dict[str, Any]]:
    killed: list[dict[str, Any]] = []
    candidates = [
        process
        for process in running_script_processes(script_names)
        if process.age_seconds >= max(0, min_age_seconds)
    ]
    for process in candidates:
        item = {"pid": process.pid, "age_seconds": process.age_seconds, "command": process.command, "signal": "TERM"}
        try:
            os.kill(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            item["status"] = "already_exited"
        except PermissionError as exc:
            item["status"] = "permission_denied"
            item["error"] = str(exc)
        else:
            item["status"] = "terminated"
        killed.append(item)

    if grace_seconds > 0 and any(item.get("status") == "terminated" for item in killed):
        time.sleep(grace_seconds)

    still_running = {process.pid: process for process in running_script_processes(script_names)}
    for item in killed:
        if item.get("status") != "terminated" or item["pid"] not in still_running:
            continue
        item["signal"] = "KILL"
        try:
            os.kill(int(item["pid"]), signal.SIGKILL)
        except ProcessLookupError:
            item["status"] = "exited_after_term"
        except PermissionError as exc:
            item["status"] = "kill_permission_denied"
            item["error"] = str(exc)
        else:
            item["status"] = "killed"
    return killed


def start_detached_python_script(
    script_path: str,
    args: list[str],
    *,
    stdout_path: str,
    stderr_path: str,
    python_executable: str | None = None,
) -> dict[str, Any]:
    script = ROOT_DIR / script_path
    if not script.exists():
        raise FileNotFoundError(script)
    Path(stdout_path).parent.mkdir(parents=True, exist_ok=True)
    Path(stderr_path).parent.mkdir(parents=True, exist_ok=True)
    executable = python_executable or sys.executable
    stdout = open(stdout_path, "a", encoding="utf-8")
    stderr = open(stderr_path, "a", encoding="utf-8")
    try:
        process = subprocess.Popen(
            [executable, str(script), *args],
            cwd=str(ROOT_DIR),
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
    except Exception:
        stdout.close()
        stderr.close()
        raise
    stdout.close()
    stderr.close()
    return {
        "pid": process.pid,
        "script": script_path,
        "args": args,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
    }
