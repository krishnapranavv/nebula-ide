"""
Static analysis engine.
Runs deterministic linters (pylint, bandit, flake8, eslint, cppcheck)
and normalises their output into a unified Finding list.

These tools are FREE — we run as many findings as we want here.
The AI layer only sees the top N findings to control token cost.
"""
import subprocess
import json
import tempfile
import os
import re
import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RawFinding:
    line: int
    col: int
    severity: str      # error | warning | info
    category: str      # security | performance | style | correctness | other
    rule_id: str
    message: str
    tool: str


def _run(cmd: list[str], cwd: str, timeout: int = 30) -> tuple[str, str, int]:
    """Run a subprocess and return (stdout, stderr, returncode)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        logger.warning(f"Static analysis tool timed out: {cmd[0]}")
        return "", "", -1
    except FileNotFoundError:
        logger.warning(f"Tool not installed: {cmd[0]}")
        return "", "", -1


# ── Python ────────────────────────────────────────────────────────────────────

def _run_pylint(filepath: str, cwd: str) -> List[RawFinding]:
    stdout, _, _ = _run(
        ["pylint", "--output-format=json", "--score=no", filepath],
        cwd=cwd,
    )
    findings = []
    try:
        items = json.loads(stdout) if stdout.strip() else []
        for item in items:
            sev_map = {"error": "error", "warning": "warning", "convention": "info", "refactor": "info"}
            cat_map = {
                "E": "correctness", "W": "style", "C": "style",
                "R": "performance", "F": "correctness",
            }
            msg_id: str = item.get("message-id", "")
            findings.append(RawFinding(
                line=item.get("line", 1),
                col=item.get("column", 0),
                severity=sev_map.get(item.get("type", "warning"), "warning"),
                category=cat_map.get(msg_id[:1], "other"),
                rule_id=msg_id,
                message=item.get("message", ""),
                tool="pylint",
            ))
    except json.JSONDecodeError:
        pass
    return findings


def _run_bandit(filepath: str, cwd: str) -> List[RawFinding]:
    stdout, _, _ = _run(
        ["bandit", "-f", "json", "-q", filepath],
        cwd=cwd,
    )
    findings = []
    try:
        data = json.loads(stdout) if stdout.strip() else {}
        for item in data.get("results", []):
            sev = item.get("issue_severity", "MEDIUM").upper()
            sev_map = {"HIGH": "error", "MEDIUM": "warning", "LOW": "info"}
            findings.append(RawFinding(
                line=item.get("line_number", 1),
                col=0,
                severity=sev_map.get(sev, "warning"),
                category="security",
                rule_id=item.get("test_id", "B000"),
                message=item.get("issue_text", ""),
                tool="bandit",
            ))
    except json.JSONDecodeError:
        pass
    return findings


def _run_flake8(filepath: str, cwd: str) -> List[RawFinding]:
    stdout, _, _ = _run(
        ["flake8", "--format=%(row)d:%(col)d:%(code)s:%(text)s", filepath],
        cwd=cwd,
    )
    findings = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(":", 3)
        if len(parts) < 4:
            continue
        try:
            row, col, code, msg = int(parts[0]), int(parts[1]), parts[2].strip(), parts[3].strip()
            sev = "error" if code.startswith("E") else "warning"
            findings.append(RawFinding(
                line=row, col=col, severity=sev,
                category="style", rule_id=code, message=msg, tool="flake8",
            ))
        except (ValueError, IndexError):
            continue
    return findings


# ── JavaScript ────────────────────────────────────────────────────────────────

def _run_eslint(filepath: str, cwd: str) -> List[RawFinding]:
    stdout, _, _ = _run(
        ["eslint", "--format=json", "--no-eslintrc",
         "--rule", '{"no-undef": "warn", "no-unused-vars": "warn", "eqeqeq": "error"}',
         filepath],
        cwd=cwd,
    )
    findings = []
    try:
        data = json.loads(stdout) if stdout.strip() else []
        for file_result in data:
            for msg in file_result.get("messages", []):
                sev_map = {1: "warning", 2: "error"}
                findings.append(RawFinding(
                    line=msg.get("line", 1),
                    col=msg.get("column", 0),
                    severity=sev_map.get(msg.get("severity", 1), "warning"),
                    category="correctness",
                    rule_id=msg.get("ruleId", "unknown"),
                    message=msg.get("message", ""),
                    tool="eslint",
                ))
    except json.JSONDecodeError:
        pass
    return findings


# ── C++ ───────────────────────────────────────────────────────────────────────

def _run_cppcheck(filepath: str, cwd: str) -> List[RawFinding]:
    stdout, stderr, _ = _run(
        ["cppcheck", "--enable=all", "--template={line}:{severity}:{id}:{message}", filepath],
        cwd=cwd,
    )
    findings = []
    output = stderr or stdout
    for line in output.strip().split("\n"):
        if not line or "Checking" in line:
            continue
        parts = line.split(":", 3)
        if len(parts) < 4:
            continue
        try:
            row, sev_raw, rule_id, msg = int(parts[0]), parts[1].strip(), parts[2].strip(), parts[3].strip()
            sev_map = {"error": "error", "warning": "warning", "style": "info", "performance": "warning"}
            cat_map = {"style": "style", "performance": "performance", "error": "correctness"}
            findings.append(RawFinding(
                line=row, col=0,
                severity=sev_map.get(sev_raw, "info"),
                category=cat_map.get(sev_raw, "other"),
                rule_id=rule_id, message=msg, tool="cppcheck",
            ))
        except (ValueError, IndexError):
            continue
    return findings


# ── Unified runner ────────────────────────────────────────────────────────────

def analyse(code: str, language: str) -> List[RawFinding]:
    """
    Write code to a temp file, run all applicable linters, return combined findings.
    Deduplicates findings with same (line, rule_id).
    """
    ext_map = {"python": ".py", "javascript": ".js", "cpp": ".cpp"}
    ext = ext_map.get(language, ".txt")

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, f"code{ext}")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        findings: List[RawFinding] = []
        if language == "python":
            findings += _run_pylint(filepath, tmpdir)
            findings += _run_bandit(filepath, tmpdir)
            findings += _run_flake8(filepath, tmpdir)
        elif language == "javascript":
            findings += _run_eslint(filepath, tmpdir)
        elif language == "cpp":
            findings += _run_cppcheck(filepath, tmpdir)

    # Deduplicate by (line, rule_id), keeping highest severity
    seen: dict[tuple, RawFinding] = {}
    sev_order = {"error": 0, "warning": 1, "info": 2}
    for f in findings:
        key = (f.line, f.rule_id)
        if key not in seen or sev_order[f.severity] < sev_order[seen[key].severity]:
            seen[key] = f

    return sorted(seen.values(), key=lambda x: (sev_order.get(x.severity, 9), x.line))
