"""
Secure code execution sandbox using Docker.

Security constraints enforced on every container:
  - network_mode=none          No internet access whatsoever
  - read_only=True             Immutable root filesystem
  - user=nobody                Non-root execution
  - no-new-privileges          No privilege escalation
  - pids_limit=50              Fork bomb prevention
  - mem_limit / memswap_limit  Memory cap, swap disabled
  - cpu_quota                  CPU throttle (50% of 1 core)
  - tmpfs /tmp                 Small writable area, noexec
  - Code mounted read-only     Source never writeable inside container

Cost note: containers are destroyed immediately after execution —
no idle resource cost, no persistent container overhead.
"""
import docker
import docker.errors
import tempfile
import os
import shutil
import asyncio
import time
import uuid
import logging
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

_docker_client = None


def _get_client() -> docker.DockerClient:
    global _docker_client
    if _docker_client is None:
        _docker_client = docker.from_env()
    return _docker_client


# ── Language runtime configuration ───────────────────────────────────────────

RUNTIMES = {
    "python": {
        "image":    "nebula-sandbox-python:latest",
        "fallback": "python:3.11-slim",
        "filename": "main.py",
        "cmd":      ["python", "-u", "/code/main.py"],
        "cmd_stdin": "python -u /code/main.py < /code/stdin.txt",
    },
    "javascript": {
        "image":    "nebula-sandbox-node:latest",
        "fallback": "node:18-alpine",
        "filename": "main.js",
        "cmd":      ["node", "/code/main.js"],
        "cmd_stdin": "node /code/main.js < /code/stdin.txt",
    },
    "cpp": {
        "image":    "nebula-sandbox-cpp:latest",
        "fallback": "gcc:12",
        "filename": "main.cpp",
        "cmd":      ["bash", "-c", "g++ -O2 -std=c++17 -o /tmp/prog /code/main.cpp && /tmp/prog"],
        "cmd_stdin": "g++ -O2 -std=c++17 -o /tmp/prog /code/main.cpp && /tmp/prog < /code/stdin.txt",
    },
}


class SandboxResult:
    __slots__ = ("exec_id", "stdout", "stderr", "exit_code", "runtime_ms", "timed_out")

    def __init__(self, exec_id, stdout, stderr, exit_code, runtime_ms, timed_out):
        self.exec_id    = exec_id
        self.stdout     = stdout[:settings.SANDBOX_MAX_STDOUT_BYTES]
        self.stderr     = stderr[:settings.SANDBOX_MAX_STDERR_BYTES]
        self.exit_code  = exit_code
        self.runtime_ms = runtime_ms
        self.timed_out  = timed_out


async def run_code(code: str, language: str, stdin: str = "") -> SandboxResult:
    """
    Execute code safely and return captured output.
    Raises ValueError for unsupported languages.
    All cleanup is guaranteed via finally block.
    """
    runtime = RUNTIMES.get(language)
    if not runtime:
        raise ValueError(f"Unsupported language: {language}")

    exec_id  = str(uuid.uuid4())
    code_dir = None
    container = None

    try:
        # ── Write code to a host-side temp directory ──────────────────────────
        code_dir = tempfile.mkdtemp(prefix=f"nebula_{exec_id[:8]}_")
        code_path = os.path.join(code_dir, runtime["filename"])

        with open(code_path, "w", encoding="utf-8") as f:
            f.write(code)
        os.chmod(code_path, 0o444)   # read-only for nobody user
        os.chmod(code_dir, 0o755)

        # Build command — use stdin redirect shell wrapper if stdin is provided
        if stdin:
            stdin_path = os.path.join(code_dir, "stdin.txt")
            with open(stdin_path, "w", encoding="utf-8") as f:
                f.write(stdin)
            os.chmod(stdin_path, 0o444)
            command = ["bash", "-c", runtime["cmd_stdin"]]
        else:
            command = runtime["cmd"]

        # ── Resolve image ─────────────────────────────────────────────────────
        client = _get_client()
        image = runtime["image"]
        try:
            client.images.get(image)
        except docker.errors.ImageNotFound:
            logger.warning(f"Custom image {image} not found — using fallback {runtime['fallback']}")
            image = runtime["fallback"]

        # ── Spawn container with ALL security constraints ─────────────────────
        start = time.monotonic()

        def _run():
            return client.containers.run(
                image=image,
                command=command,
                volumes={code_dir: {"bind": "/code", "mode": "ro"}},
                tmpfs={"/tmp": "size=16m,noexec,nosuid,nodev"},
                network_mode="none",
                read_only=True,
                mem_limit=settings.SANDBOX_MEMORY_LIMIT,
                memswap_limit=settings.SANDBOX_MEMORY_LIMIT,
                cpu_quota=settings.SANDBOX_CPU_QUOTA,
                cpu_period=100000,
                pids_limit=settings.SANDBOX_PIDS_LIMIT,
                security_opt=["no-new-privileges:true"],
                user="nobody",
                remove=False,
                detach=True,
                stdout=True,
                stderr=True,
            )

        container = await asyncio.get_event_loop().run_in_executor(None, _run)

        # ── Wait with hard timeout ────────────────────────────────────────────
        timed_out = False
        exit_code = -1
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: container.wait(timeout=settings.SANDBOX_TIMEOUT_SECONDS + 2)
                ),
                timeout=float(settings.SANDBOX_TIMEOUT_SECONDS),
            )
            exit_code = result.get("StatusCode", -1)
        except (asyncio.TimeoutError, Exception):
            timed_out = True
            try:
                container.kill()
            except Exception:
                pass

        runtime_ms = int((time.monotonic() - start) * 1000)

        # ── Capture output ────────────────────────────────────────────────────
        try:
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
        except Exception:
            stdout, stderr = "", ""

        if timed_out:
            stderr = f"[Timed out after {settings.SANDBOX_TIMEOUT_SECONDS}s]\n" + stderr

        return SandboxResult(
            exec_id=exec_id,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            runtime_ms=runtime_ms,
            timed_out=timed_out,
        )

    finally:
        # Guaranteed cleanup — no orphaned containers, no temp files leaking
        if container:
            try:
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Container removal failed for {exec_id}: {e}")
        if code_dir and os.path.exists(code_dir):
            shutil.rmtree(code_dir, ignore_errors=True)
