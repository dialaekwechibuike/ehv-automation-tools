"""
EHV Automation Project Evaluator (AI-Judge edition)
===================================================
A reusable evaluator for ANY automation project or workflow.

You only fill in two CONFIG lines (project name + description).
You do NOT add test cases manually. When you run the script, Claude will:

  1. Read your project description.
  2. Invent a full set of realistic test situations for that project.
  3. Simulate how the automation SHOULD respond to each situation.
  4. Independently judge each outcome (PASS / CONCERN / FAIL).
  5. Give an overall verdict: score, strengths, weaknesses, risks,
     and recommendations.
  6. Save a clean markdown report you can send to Florian.

IMPORTANT — what this tool does and does NOT do:
  - DOES: scenario planning, edge-case discovery, structured QA writeups.
  - DOES NOT: call your live n8n workflow, webhook, or production APIs.
  Responses are AI-simulated from your project description, not from
  the real automation. The report states this clearly.

HOW TO USE:
  1. Fill in PROJECT_NAME and PROJECT_DESCRIPTION in the CONFIG section.
  2. Run:  python evaluate_project.py

REQUIREMENTS:
    pip install anthropic
    export ANTHROPIC_API_KEY=your_key_here
"""

import anthropic
import json
import os
import re
import sys
import time
from datetime import datetime

# ============================================================
# CONFIG — fill this in for each new project
# ============================================================

# --- Change ONLY these two lines for each new project ---------
PROJECT_NAME = "PUT YOUR PROJECT NAME HERE"
PROJECT_DESCRIPTION = (
    "Describe in 1-3 sentences what this project does, what it decides, "
    "and which tools it uses (e.g. n8n, Gmail, Google Sheets, Claude)."
)
# --------------------------------------------------------------

GITHUB_REPO = "https://github.com/dialaekwechibuike/ehv-automation-tools"
YOUR_NAME = "Chibuike Dialaekwe"
MANAGER_NAME = "Florian"
COMPANY = "Erste Hausverwaltung GmbH"
MODEL = "claude-sonnet-4-6"

# How many test situations Claude should invent from the description alone.
NUM_TEST_CASES = 6

# Retry JSON parsing this many times when the model returns bad JSON.
JSON_PARSE_RETRIES = 2

# ============================================================
# PRICING (claude-sonnet-4-6) — for the cost estimate in the report
# ============================================================
INPUT_COST_PER_M = 3.00
OUTPUT_COST_PER_M = 15.00

# ============================================================
# ENGINE — no need to edit anything below this line
# ============================================================

PLACEHOLDER_MARKERS = (
    "PUT YOUR PROJECT NAME HERE",
    "Describe in 1-3 sentences",
)


def _extract_json(text):
    """Pull the first JSON object or array out of a model reply."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def _call_model(client, prompt, max_tokens, usage):
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    usage["in"] += resp.usage.input_tokens
    usage["out"] += resp.usage.output_tokens
    return resp.content[0].text.strip()


def _call_model_json(client, prompt, max_tokens, usage, expect, label, warnings):
    """Call the model and parse JSON, retrying on failure."""
    current_prompt = prompt

    for attempt in range(JSON_PARSE_RETRIES + 1):
        text = _call_model(client, current_prompt, max_tokens, usage)
        parsed = _extract_json(text)
        if expect == "list" and isinstance(parsed, list):
            return parsed
        if expect == "dict" and isinstance(parsed, dict):
            return parsed
        if attempt < JSON_PARSE_RETRIES:
            current_prompt = (
                prompt
                + "\n\nYour previous reply was not valid "
                + expect
                + ". Return ONLY valid "
                + expect
                + " JSON with no commentary."
            )

    warnings.append(
        label
        + " failed after "
        + str(JSON_PARSE_RETRIES + 1)
        + " attempt(s); continuing with partial results."
    )
    return None


def validate_config():
    errors = []
    if not PROJECT_NAME.strip() or any(m in PROJECT_NAME for m in PLACEHOLDER_MARKERS):
        errors.append("Set PROJECT_NAME to your real project name.")
    if not PROJECT_DESCRIPTION.strip() or any(
        m in PROJECT_DESCRIPTION for m in PLACEHOLDER_MARKERS
    ):
        errors.append("Set PROJECT_DESCRIPTION to a concrete project summary.")
    if NUM_TEST_CASES <= 0:
        errors.append("NUM_TEST_CASES must be greater than zero.")
    return errors


def generate_test_cases(client, usage, warnings):
    """Invent a balanced set of test situations from the project description."""
    prompt = (
        "You are a senior QA test designer reviewing an automation project.\n\n"
        "Project name: "
        + PROJECT_NAME
        + "\n"
        "What the project does: "
        + PROJECT_DESCRIPTION
        + "\n\n"
        "Design exactly "
        + str(NUM_TEST_CASES)
        + " test situations tailored to THIS project. Cover a mix of:\n"
        "- normal expected inputs\n"
        "- edge cases and ambiguous inputs\n"
        "- missing, invalid, or duplicate data\n"
        "- timing, retries, or integration failures\n"
        "- cases that should escalate to a human or stop safely\n\n"
        "Write each situation as one short plain-language sentence. "
        "Do not assume a specific industry unless the project description "
        "already implies one.\n"
        "Return ONLY a JSON array of "
        + str(NUM_TEST_CASES)
        + " strings. No commentary."
    )
    parsed = _call_model_json(
        client,
        prompt,
        900,
        usage,
        "list",
        "Test case generation",
        warnings,
    )
    if isinstance(parsed, list):
        cases = [str(x).strip() for x in parsed if str(x).strip()]
        return cases[:NUM_TEST_CASES]
    return []


def run_case(client, scenario, usage):
    """Simulate how the automation SHOULD respond to this situation."""
    prompt = (
        "You are simulating the decision logic of this automation project.\n"
        "Project: "
        + PROJECT_NAME
        + "\n"
        "What it does: "
        + PROJECT_DESCRIPTION
        + "\n\n"
        "Based only on the project description, respond exactly as the automation "
        "SHOULD for the following situation. Be concise, realistic, and specific "
        "about the actions the workflow would take.\n\n"
        "Situation: "
        + scenario
    )
    t0 = time.time()
    response = _call_model(client, prompt, 400, usage)
    elapsed = time.time() - t0
    return response, elapsed


def evaluate_all(client, items, usage, warnings):
    """Send every (scenario, response) pair to Claude for an independent verdict."""
    blocks = []
    for it in items:
        blocks.append(
            "Case "
            + str(it["index"])
            + ":\n"
            "Situation: "
            + it["scenario"]
            + "\n"
            "Simulated automation response: "
            + it["response"]
        )
    joined = "\n\n".join(blocks)

    prompt = (
        "You are an independent QA reviewer for an automation project.\n\n"
        "Project: "
        + PROJECT_NAME
        + "\n"
        "What it does: "
        + PROJECT_DESCRIPTION
        + "\n\n"
        "IMPORTANT: The responses below were AI-SIMULATED from the project "
        "description. They were NOT produced by the live workflow. "
        "Judge each response against what the project SHOULD do in production. "
        "Be strict and skeptical — do not assume the simulated response is "
        "correct just because it sounds plausible.\n\n"
        + joined
        + "\n\n"
        "Return ONLY valid JSON in exactly this shape:\n"
        "{\n"
        '  "overall": {\n'
        '    "score": <integer 0-10>,\n'
        '    "summary": "<2-3 sentence verdict>",\n'
        '    "strengths": ["..."],\n'
        '    "weaknesses": ["..."],\n'
        '    "risks": ["..."],\n'
        '    "recommendations": ["..."]\n'
        "  },\n"
        '  "cases": [\n'
        '    {"index": <int>, "verdict": "PASS|CONCERN|FAIL", "reason": "<one sentence>"}\n'
        "  ]\n"
        "}\n"
        "Include one verdict entry for every case index shown above.\n"
        "No text before or after the JSON."
    )
    return _call_model_json(
        client,
        prompt,
        1500,
        usage,
        "dict",
        "Overall evaluation",
        warnings,
    )


def build_report(items, verdicts, overall, usage, total_time, warnings):
    now = datetime.now()
    date_str = now.strftime("%d %B %Y")
    fname = "evaluation_report_" + now.strftime("%Y%m%d_%H%M") + ".md"

    by_index = {}
    if verdicts:
        for v in verdicts:
            by_index[v.get("index")] = v

    cost = (
        usage["in"] / 1_000_000 * INPUT_COST_PER_M
        + usage["out"] / 1_000_000 * OUTPUT_COST_PER_M
    )

    lines = []
    lines.append("# Project Evaluation Report")
    lines.append("")
    lines.append("**Project:** " + PROJECT_NAME + "  ")
    lines.append("**Prepared by:** " + YOUR_NAME + "  ")
    lines.append("**Submitted to:** " + MANAGER_NAME + ", " + COMPANY + "  ")
    lines.append("**Date:** " + date_str + "  ")
    lines.append("**GitHub:** " + GITHUB_REPO + "  ")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Evaluation Methodology")
    lines.append("")
    lines.append(
        "This report was generated by `evaluate_project.py` using AI-assisted "
        "scenario review. Claude invented test situations from the project "
        "description, simulated expected automation behaviour, and "
        "independently judged those simulated outcomes."
    )
    lines.append("")
    lines.append(
        "**What this report proves:** design-level QA, edge-case coverage, "
        "and a structured summary of likely behaviour."
    )
    lines.append("")
    lines.append(
        "**What this report does NOT prove:** that the live workflow, "
        "webhooks, or integrations were executed. Validate critical paths "
        "against the real automation before production use."
    )
    lines.append("")
    if warnings:
        lines.append("**Run warnings:**")
        lines.append("")
        for w in warnings:
            lines.append("- " + w)
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Project Overview")
    lines.append("")
    lines.append(PROJECT_DESCRIPTION)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Overall Verdict")
    lines.append("")
    if overall:
        lines.append("**Score:** " + str(overall.get("score", "n/a")) + " / 10")
        lines.append("")
        lines.append(overall.get("summary", ""))
        lines.append("")
        for title, key in [
            ("Strengths", "strengths"),
            ("Weaknesses", "weaknesses"),
            ("Risks", "risks"),
            ("Recommendations", "recommendations"),
        ]:
            vals = overall.get(key) or []
            if vals:
                lines.append("**" + title + ":**")
                lines.append("")
                for val in vals:
                    lines.append("- " + str(val))
                lines.append("")
    else:
        lines.append(
            "_The evaluator did not return a structured overall verdict; "
            "see case results below and re-run if needed._"
        )
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Case-by-Case Results")
    lines.append("")
    for it in items:
        v = by_index.get(it["index"], {})
        verdict = v.get("verdict", "—")
        reason = v.get("reason", "")
        lines.append("### [" + verdict + "] Case " + str(it["index"]))
        lines.append("")
        lines.append("**Situation:**")
        lines.append("> " + it["scenario"])
        lines.append("")
        lines.append("**Simulated automation response:**")
        lines.append("> " + it["response"].replace("\n", "\n> "))
        lines.append("")
        if reason:
            lines.append("**Reviewer note:** " + reason)
            lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("## Run Stats")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append("| Model used | `" + MODEL + "` |")
    lines.append("| Auto-generated test cases | " + str(len(items)) + " |")
    lines.append("| Input tokens | " + format(usage["in"], ",") + " |")
    lines.append("| Output tokens | " + format(usage["out"], ",") + " |")
    lines.append("| Estimated API cost | $" + format(cost, ".6f") + " USD |")
    lines.append("| Total run time | " + format(total_time, ".2f") + "s |")
    lines.append("")
    lines.append("---")
    lines.append("*Report auto-generated by evaluate_project.py (AI-Judge edition)*")

    with open(fname, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return fname


def main():
    config_errors = validate_config()
    if config_errors:
        print("\nConfiguration error(s):")
        for err in config_errors:
            print("  - " + err)
        print("\nEdit PROJECT_NAME and PROJECT_DESCRIPTION at the top of the file.")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nMissing ANTHROPIC_API_KEY.")
        print("Run: export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    client = anthropic.Anthropic()
    usage = {"in": 0, "out": 0}
    warnings = []
    t_start = time.time()

    print("\nEvaluating project: " + PROJECT_NAME)
    print("Mode: AI-simulated scenario review (not live workflow execution)")
    print("=" * 55)

    print("Generating test cases from project description...")
    cases = generate_test_cases(client, usage, warnings)
    if not cases:
        print("No test cases were generated. Check PROJECT_DESCRIPTION and try again.")
        sys.exit(1)

    items = []
    for idx, scenario in enumerate(cases, start=1):
        items.append({"index": idx, "scenario": scenario})
        print("  [case " + str(idx) + "] " + scenario)

    for it in items:
        resp_text, _ = run_case(client, it["scenario"], usage)
        it["response"] = resp_text
        print("  [simulated] Case " + str(it["index"]))

    print("Asking Claude for the independent overall verdict...")
    result = evaluate_all(client, items, usage, warnings)
    overall = result.get("overall") if isinstance(result, dict) else None
    verdicts = result.get("cases") if isinstance(result, dict) else None

    if verdicts is None:
        warnings.append("Case verdicts were missing from the evaluation response.")

    total_time = time.time() - t_start
    report_file = build_report(items, verdicts, overall, usage, total_time, warnings)

    print("\n" + "=" * 55)
    if overall:
        print("  Overall score : " + str(overall.get("score", "n/a")) + " / 10")
    print("  Cases         : " + str(len(items)))
    cost = (
        usage["in"] / 1_000_000 * INPUT_COST_PER_M
        + usage["out"] / 1_000_000 * OUTPUT_COST_PER_M
    )
    print("  Est. cost     : $" + format(cost, ".6f") + " USD")
    if warnings:
        print("  Warnings      : " + str(len(warnings)))
    print("=" * 55)
    print("\nReport saved: " + report_file)
    print("Send this file to Florian.")


if __name__ == "__main__":
    main()
