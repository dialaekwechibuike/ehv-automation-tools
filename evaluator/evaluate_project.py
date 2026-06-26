"""
EHV Automation Project Evaluator (AI-Judge edition)
===================================================
A reusable evaluator that works for ANY automation project.

You do NOT write the "correct answer" for each case anymore.
Instead you describe your project and list a few example situations
(cases). When you run it, Claude will:

  1. Read your project description and your listed cases.
  2. Invent extra creative / edge cases you may have forgotten.
  3. Simulate how the automation SHOULD respond to each case.
  4. Independently judge each outcome (PASS / CONCERN / FAIL).
  5. Give an overall verdict: score, strengths, weaknesses, risks,
     and recommendations.
  6. Save a clean markdown report you can send to Florian.

IMPORTANT — what this tool does and does NOT do:
  - DOES: scenario planning, edge-case discovery, structured QA writeups.
  - DOES NOT: call your live n8n workflow, webhook, or production APIs.
  Responses are AI-simulated from your project description, not from
  the real automation. Say so clearly when you submit the report.

HOW TO USE:
  1. Fill in the CONFIG section below (project name + description).
  2. Add a few example situations to the CASES list
     (or leave it empty and let Claude invent them all).
  3. Run:  python evaluate_project.py

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

# --- Change these lines for each new project ------------------
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

# How many extra creative / edge cases should Claude invent on its own?
NUM_EXTRA_CASES = 4

# Retry JSON parsing this many times when the model returns bad JSON.
JSON_PARSE_RETRIES = 2

# ============================================================
# CASES — open-ended situations for THIS project. NO answers needed.
# Just describe situations in plain language (German or English is fine).
#
# Leave CASES = [] to let Claude invent all test cases from the
# PROJECT_DESCRIPTION above.
#
# Example format for a tenant-email routing workflow (replace with yours):
# CASES = [
#     "A tenant emails about a burst pipe at 11pm and marks it urgent.",
#     "A marketing newsletter arrives in the shared inbox with no tenant ID.",
#     "Two emails about the same heating issue arrive 5 minutes apart.",
#     "An email is in German and mentions 'Wasserschaden' but no apartment number.",
#     "A tenant forwards a long thread; only the oldest message has the unit number.",
# ]
# ============================================================

CASES = []

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
    last_text = ""

    for attempt in range(JSON_PARSE_RETRIES + 1):
        last_text = _call_model(client, current_prompt, max_tokens, usage)
        parsed = _extract_json(last_text)
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
        label + " failed after "
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
    if NUM_EXTRA_CASES < 0:
        errors.append("NUM_EXTRA_CASES must be zero or greater.")
    return errors


def generate_extra_cases(client, usage, warnings):
    """Ask Claude to invent additional realistic / edge cases."""
    if NUM_EXTRA_CASES <= 0:
        return []

    listed = "\n".join("- " + c for c in CASES) if CASES else "(none provided yet)"
    prompt = (
        "You are a QA test designer reviewing a property-management automation "
        "project for Erste Hausverwaltung GmbH.\n\n"
        "Project name: "
        + PROJECT_NAME
        + "\n"
        "What the project does: "
        + PROJECT_DESCRIPTION
        + "\n\n"
        "The team already plans to test these situations:\n"
        + listed
        + "\n\n"
        "Propose "
        + str(NUM_EXTRA_CASES)
        + " ADDITIONAL realistic test situations that are NOT already covered. "
        "Focus on edge cases, ambiguous inputs, duplicate messages, missing data, "
        "after-hours urgency, multilingual content, and failure modes.\n"
        "Each case should be one short plain-language sentence.\n"
        "Return ONLY a JSON array of strings. No commentary."
    )
    parsed = _call_model_json(
        client,
        prompt,
        700,
        usage,
        "list",
        "Extra case generation",
        warnings,
    )
    if isinstance(parsed, list):
        return [str(x) for x in parsed][:NUM_EXTRA_CASES]
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
        "about actions (route, tag, notify, escalate, ignore, request info, etc.).\n\n"
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
            + " ("
            + it["source"]
            + "):\n"
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
        "description. They were NOT produced by the live n8n workflow. "
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
        "scenario review. Claude invented and/or reviewed test situations, "
        "simulated expected automation behaviour from the project description, "
        "and independently judged those simulated outcomes."
    )
    lines.append("")
    lines.append(
        "**What this report proves:** design-level QA, edge-case coverage, "
        "and a structured summary of likely behaviour."
    )
    lines.append("")
    lines.append(
        "**What this report does NOT prove:** that the live n8n workflow, "
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
        lines.append(
            "### ["
            + verdict
            + "] Case "
            + str(it["index"])
            + " ("
            + it["source"]
            + ")"
        )
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
    lines.append("| Listed cases | " + str(len(CASES)) + " |")
    lines.append("| Total cases evaluated | " + str(len(items)) + " |")
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
        print("\nEdit the CONFIG section at the top of evaluate_project.py and run again.")
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
    print("Mode: AI-simulated scenario review (not live n8n execution)")
    print("=" * 55)

    items = []
    idx = 0
    for case in CASES:
        idx += 1
        items.append({"index": idx, "scenario": case, "source": "listed"})

    print("Asking Claude to invent extra cases...")
    extra = generate_extra_cases(client, usage, warnings)
    for case in extra:
        idx += 1
        items.append({"index": idx, "scenario": case, "source": "AI-generated"})

    if not items:
        print("No cases to evaluate. Add some to CASES or set NUM_EXTRA_CASES > 0.")
        sys.exit(1)

    for it in items:
        resp_text, _ = run_case(client, it["scenario"], usage)
        it["response"] = resp_text
        print("  [done] Case " + str(it["index"]) + " (" + it["source"] + ")")

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
