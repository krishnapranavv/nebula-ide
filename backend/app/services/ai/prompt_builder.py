"""
Prompt builder for AI code review.

Engineering goal: maximise review quality while minimising token count.
Token cost is the primary operational cost of this service.

Techniques used:
  - Code truncation at AI_MAX_CODE_LINES (default 300)
  - Finding cap at AI_MAX_FINDINGS_PER_REVIEW (default 15)
  - Compact JSON schema with short field names
  - Structured output mandate (JSON-only) to skip preamble tokens
"""
import json
from typing import List
from app.core.config import settings
from app.services.ai.static_analysis import RawFinding


SYSTEM_PROMPT = """You are a senior software engineer performing a code review.

Respond ONLY with valid JSON matching this exact schema — no preamble, no markdown fences:
{
  "overall_score": <integer 1-10>,
  "summary": "<one concise sentence>",
  "findings": [
    {
      "line": <integer>,
      "severity": "<error|warning|info>",
      "category": "<security|performance|style|correctness|other>",
      "rule_id": "<rule identifier>",
      "message": "<short description>",
      "explanation": "<WHY this is a problem — 1-3 sentences>",
      "fix": "<corrected code snippet or null>"
    }
  ]
}

Rules:
- overall_score: 1=terrible, 10=production-ready
- explanation must explain WHY the issue matters, not just restate the rule
- fix should be a short corrected code snippet when practical
- Only include findings for real issues — do not invent issues
- Focus on security, correctness, and performance over minor style issues"""


def build_review_prompt(code: str, language: str, findings: List[RawFinding]) -> str:
    # Truncate code to stay within token budget
    lines = code.splitlines()
    truncated = False
    if len(lines) > settings.AI_MAX_CODE_LINES:
        lines = lines[:settings.AI_MAX_CODE_LINES]
        truncated = True
    truncated_code = "\n".join(lines)
    if truncated:
        truncated_code += f"\n# ... [truncated at {settings.AI_MAX_CODE_LINES} lines]"

    # Cap findings sent to AI
    top_findings = findings[:settings.AI_MAX_FINDINGS_PER_REVIEW]
    findings_json = json.dumps(
        [{"line": f.line, "tool": f.tool, "rule": f.rule_id, "msg": f.message, "sev": f.severity}
         for f in top_findings],
        indent=None,
    )

    return (
        f"Language: {language}\n\n"
        f"Code:\n```{language}\n{truncated_code}\n```\n\n"
        f"Static analysis found {len(top_findings)} issue(s):\n{findings_json}\n\n"
        f"Provide a JSON review. Explain the most impactful issues. "
        f"Include corrected code snippets where helpful."
    )
