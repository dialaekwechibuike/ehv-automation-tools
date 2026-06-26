"""
EHV Automation Project Evaluator (AI-Judge edition)
===================================================
A reusable evaluator that works for ANY project.

You do NOT write the "correct answer" for each case anymore.
Instead you just describe your project and list a few example
situations (cases). When you run it, Claude will:

  1. Read your project description and your listed cases.
  2. Invent extra creative / edge cases you may have forgotten.
  3. Decide how the project SHOULD respond to each case.
  4. Judge each outcome (PASS / CONCERN / FAIL) with reasons.
  5. Give an overall verdict on the project: score, strengths,
     weaknesses, risks and recommendations.
  6. Save a clean markdown report you can send to Florian.

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
import time
import os
import json
import re
from datetime import datetime

# ============================================================
# CONFIG — fill this in for each new project
# ============================================================

# --- Change ONLY these two lines for each new project ---------
PROJECT_NAME        = "PUT YOUR PROJECT NAME HERE"
PROJECT_DESCRIPTION = "Describe in 1-3 sentences what this project does, what it decides, and which tools it uses."
# --------------------------------------------------------------

GITHUB_REPO         = "https://github.com/dialaekwechibuike/ehv-automation-tools"
YOUR_NAME           = "Chibuike Dialaekwe"
MANAGER_NAME        = "Florian"
COMPANY             = "Erste Hausverwaltung GmbH"
MODEL               = "claude-sonnet-4-6"

# How many extra creative / edge cases should Claude invent on its own?
NUM_EXTRA_CASES     = 4

# ============================================================
# CASES — open-ended situations for THIS project. NO answers needed.
# Just describe situations in plain language (any language).
#
# You can also leave this list completely empty:  CASES = []
# and Claude will invent all the test cases for you from the
# PROJECT_DESCRIPTION above.
#
# Example of the format (delete these and write your own):
#   "Describe a normal, expected situation for your project.",
#   "Describe an unusual or tricky situation.",
# ============================================================

CASES = []

# ============================================================
# PRICING (claude-sonnet-4-6) — for the cost estimate in the report
# ============================================================
INPUT_COST_PER_M  = 3.00
OUTPUT_COST_PER_M = 15.00

# ============================================================
# ENGINE — no need to edit anything below this line
# ============================================================

def _extract_json(text):
    """Pull the first JSON object or array out of a model reply."""
    text = text.strip()
    # strip ``` fences if present
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    # otherwise grab the first {...} or [...] block
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return None
    return None


def generate_extra_cases(client, usage):
    """Ask Claude to invent additional realistic / edge cases."""
    if NUM_EXTRA_CASES <= 0:
        return []

    listed = "\n".join("- " + c for c in CASES) if CASES else "(none provided yet)"
    prompt = (
        "You are a QA test designer reviewing an automation project.\n\n"
        "Project name: " + PROJECT_NAME + "\n"
        "What the project does: " + PROJECT_DESCRIPTION + "\n\n"
        "The team already plans to test these situations:\n" + listed + "\n\n"
        "Propose " + str(NUM_EXTRA_CASES) + " ADDITIONAL realistic test "
        "situations that are NOT already covered above. Focus on edge cases, "
        "tricky inputs, and things that could make the system behave wrongly.\n"
        "Return ONLY a JSON array of short plain-language strings. No commentary."
    )
    resp = client.messages.create(
        model=MODEL, max_tokens=700,
        messages=[{"role": "user", "content": prompt}],
    )
    usage["in"]  += resp.usage.input_tokens
    usage["out"] += resp.usage.output_tokens

    parsed = _extract_json(resp.content[0].text)
    if isinstance(parsed, list):
        return [str(x) for x in parsed][:NUM_EXTRA_CASES]
    return []


def run_case(client, scenario, usage):
    """Ask Claude how the project SHOULD respond to this situation."""
    prompt = (
        "You are the AI decision step inside this automation project.\n"
        "Project: " + PROJECT_NAME + "\n"
        "What it does: " + PROJECT_DESCRIPTION + "\n\n"
        "Respond exactly as the automation should for the following situation. "
        "Be concise and realistic.\n\n"
        "Situation: " + scenario
    )
    t0 = time.time()
    resp = client.messages.create(
        model=MODEL, max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed = time.time() - t0
    usage["in"]  += resp.usage.input_tokens
    usage["out"] += resp.usage.output_tokens
    return resp.content[0].text.strip(), elapsed


def evaluate_all(client, items, usage):
    """Send every (scenario, response) pair to Claude for a verdict."""
    blocks = []
    for it in items:
        blocks.append(
            "Case " + str(it["index"]) + " (" + it["source"] + "):\n"
            "Situation: " + it["scenario"] + "\n"
            "Automation response: " + it["response"]
        )
    joined = "\n\n".join(blocks)

    prompt = (
        "You are a strict but fair QA reviewer for an automation project.\n\n"
        "Project: " + PROJECT_NAME + "\n"
        "What it does: " + PROJECT_DESCRIPTION + "\n\n"
        "Below are test situations and how the automation responded to each. "
        "Judge whether each response is correct and appropriate for this project, "
        "then give an overall assessment of the whole project outcome.\n\n"
        + joined + "\n\n"
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
        "No text before or after the JSON."
    )
    resp = client.messages.create(
        model=MODEL, max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    usage["in"]  += resp.usage.input_tokens
    usage["out"] += resp.usage.output_tokens
    return _extract_json(resp.content[0].text)


def build_report(items, verdicts, overall, usage, total_time):
    now      = datetime.now()
    date_str = now.strftime("%d %B %Y")
    fname    = "evaluation_report_" + now.strftime("%Y%m%d_%H%M") + ".md"

    by_index = {}
    if verdicts:
        for v in verdicts:
            by_index[v.get("index")] = v

    cost = usage["in"] / 1_000_000 * INPUT_COST_PER_M + \
           usage["out"] / 1_000_000 * OUTPUT_COST_PER_M

    L = []
    L.append("# Project Evaluation Report")
    L.append("")
    L.append("**Project:** " + PROJECT_NAME + "  ")
    L.append("**Prepared by:** " + YOUR_NAME + "  ")
    L.append("**Submitted to:** " + MANAGER_NAME + ", " + COMPANY + "  ")
    L.append("**Date:** " + date_str + "  ")
    L.append("**GitHub:** " + GITHUB_REPO + "  ")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Project Overview")
    L.append("")
    L.append(PROJECT_DESCRIPTION)
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Overall Verdict")
    L.append("")
    if overall:
        L.append("**Score:** " + str(overall.get("score", "n/a")) + " / 10")
        L.append("")
        L.append(overall.get("summary", ""))
        L.append("")
        for title, key in [("Strengths", "strengths"),
                           ("Weaknesses", "weaknesses"),
                           ("Risks", "risks"),
                           ("Recommendations", "recommendations")]:
            vals = overall.get(key) or []
            if vals:
                L.append("**" + title + ":**")
                L.append("")
                for v in vals:
                    L.append("- " + str(v))
                L.append("")
    else:
        L.append("_Claude did not return a structured overall verdict; "
                 "see raw case results below._")
        L.append("")
    L.append("---")
    L.append("")
    L.append("## Case-by-Case Results")
    L.append("")
    for it in items:
        v = by_index.get(it["index"], {})
        verdict = v.get("verdict", "—")
        reason  = v.get("reason", "")
        L.append("### [" + verdict + "] Case " + str(it["index"]) +
                 " (" + it["source"] + ")")
        L.append("")
        L.append("**Situation:**")
        L.append("> " + it["scenario"])
        L.append("")
        L.append("**Automation response:**")
        L.append("> " + it["response"].replace("\n", "\n> "))
        L.append("")
        if reason:
            L.append("**Reviewer note:** " + reason)
            L.append("")
        L.append("---")
        L.append("")
    L.append("## Run Stats")
    L.append("")
    L.append("| Metric | Value |")
    L.append("|--------|-------|")
    L.append("| Model used | `" + MODEL + "` |")
    L.append("| Cases evaluated | " + str(len(items)) + " |")
    L.append("| Input tokens | " + format(usage["in"], ",") + " |")
    L.append("| Output tokens | " + format(usage["out"], ",") + " |")
    L.append("| Estimated API cost | $" + format(cost, ".6f") + " USD |")
    L.append("| Total run time | " + format(total_time, ".2f") + "s |")
    L.append("")
    L.append("---")
    L.append("*Report auto-generated by evaluate_project.py (AI-Judge edition)*")

    with open(fname, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return fname


def main():
    client = anthropic.Anthropic()
    usage  = {"in": 0, "out": 0}
    t_start = time.time()

    print("\nEvaluating project: " + PROJECT_NAME)
    print("=" * 55)

    # 1. Gather cases: the ones you listed + ones Claude invents
    items = []
    idx = 0
    for c in CASES:
        idx += 1
        items.append({"index": idx, "scenario": c, "source": "listed"})

    print("Asking Claude to invent extra cases...")
    extra = generate_extra_cases(client, usage)
    for c in extra:
        idx += 1
        items.append({"index": idx, "scenario": c, "source": "AI-generated"})

    if not items:
        print("No cases to evaluate. Add some to CASES or set NUM_EXTRA_CASES > 0.")
        return

    # 2. Get the automation's response for each case
    for it in items:
        resp_text, _ = run_case(client, it["scenario"], usage)
        it["response"] = resp_text
        print("  [done] Case " + str(it["index"]) + " (" + it["source"] + ")")

    # 3. Have Claude judge everything
    print("Asking Claude for the overall verdict...")
    result   = evaluate_all(client, items, usage)
    overall  = result.get("overall") if isinstance(result, dict) else None
    verdicts = result.get("cases")   if isinstance(result, dict) else None

    total_time = time.time() - t_start

    # 4. Write the report
    report_file = build_report(items, verdicts, overall, usage, total_time)

    print("\n" + "=" * 55)
    if overall:
        print("  Overall score : " + str(overall.get("score", "n/a")) + " / 10")
    print("  Cases         : " + str(len(items)))
    cost = usage["in"] / 1_000_000 * INPUT_COST_PER_M + \
           usage["out"] / 1_000_000 * OUTPUT_COST_PER_M
    print("  Est. cost     : $" + format(cost, ".6f") + " USD")
    print("=" * 55)
    print("\nReport saved: " + report_file)
    print("Send this file to Florian.")


if __name__ == "__main__":
    main()
