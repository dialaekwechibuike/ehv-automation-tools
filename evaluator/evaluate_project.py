"""
EHV Automation Project Evaluator
==================================
HOW TO USE:
1. Open this file in Cursor inside your project folder
2. Fill in the CONFIG section below with your project details
3. Add your test cases to the TEST_CASES list
4. Run: python evaluate_project.py
5. A markdown report is generated and saved — send it to Florian

REQUIREMENTS:
    pip install anthropic
    export ANTHROPIC_API_KEY=your_key_here
"""

import anthropic
import time
import os
from datetime import datetime

# ============================================================
# CONFIG — fill this in for each new project
# ============================================================

PROJECT_NAME        = "Zahlungserinnerung Workflow"          # Name of your project
PROJECT_DESCRIPTION = "Automated late-payment reminder system for EHV tenants using n8n, Claude AI, Google Sheets, Amazon SQS, monday.com and Twilio."
GITHUB_REPO         = "https://github.com/chybyke1992/YOUR_REPO"  # Your GitHub link
YOUR_NAME           = "Chibuike Dialaekwe"
MANAGER_NAME        = "Florian"
COMPANY             = "Erste Hausverwaltung GmbH"
MODEL               = "claude-sonnet-4-6"

# ============================================================
# TEST CASES — define what Claude should classify/generate
# Format:
#   "input"    : the text you send to Claude
#   "expected" : the exact response you expect (used for pass/fail)
#   "label"    : short description shown in the report
# ============================================================

TEST_CASES = [
    {
        "label": "Test 1 — Identify overdue tenant",
        "input": "Mieter Hans Mueller hat seine Miete fuer Juni 2026 nicht bezahlt. Soll er eine Zahlungserinnerung erhalten? Antworte nur mit Ja oder Nein.",
        "expected": "Ja"
    },
    {
        "label": "Test 2 — Skip paid tenant",
        "input": "Mieter Anna Schmidt hat ihre Miete fuer Juni 2026 vollstaendig bezahlt. Soll sie eine Zahlungserinnerung erhalten? Antworte nur mit Ja oder Nein.",
        "expected": "Nein"
    },
    {
        "label": "Test 3 — Generate reminder message",
        "input": "Schreibe eine kurze, hoefliche Zahlungserinnerung auf Deutsch fuer Mieter Klaus Weber, Wohnung 3B, ausstehender Betrag 850 Euro fuer Juni 2026. Maximal 3 Saetze.",
        "expected": None   # None = no exact match, just checks Claude responds
    },
    {
        "label": "Test 4 — Classify payment status",
        "input": "Zahlungsstatus: 5 Tage ueberfaellig. Klassifiziere als: Erste Erinnerung, Zweite Mahnung, oder Letzte Mahnung. Antworte nur mit dem Klassifizierungsnamen.",
        "expected": "Erste Erinnerung"
    },
    {
        "label": "Test 5 — Classify urgent case",
        "input": "Zahlungsstatus: 32 Tage ueberfaellig. Klassifiziere als: Erste Erinnerung, Zweite Mahnung, oder Letzte Mahnung. Antworte nur mit dem Klassifizierungsnamen.",
        "expected": "Letzte Mahnung"
    },
]

# ============================================================
# PRICING (claude-sonnet-4-6)
# ============================================================
INPUT_COST_PER_M  = 3.00
OUTPUT_COST_PER_M = 15.00

# ============================================================
# EVALUATION ENGINE — no need to edit below this line
# ============================================================

def run_evaluation():
    client = anthropic.Anthropic()

    results = []
    total_input_tokens  = 0
    total_output_tokens = 0
    total_time          = 0.0
    correct             = 0
    skipped             = 0

    print(f"\nRunning evaluation for: {PROJECT_NAME}")
    print("=" * 55)

    for i, tc in enumerate(TEST_CASES, 1):
        t0 = time.time()
        response = client.messages.create(
            model=MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": tc["input"]}],
        )
        elapsed = time.time() - t0

        raw_text  = response.content[0].text.strip()
        predicted = raw_text.split("\n")[0].strip()
        in_tok    = response.usage.input_tokens
        out_tok   = response.usage.output_tokens

        if tc["expected"] is None:
            passed  = len(predicted) > 0
            skipped += 1
            status  = "OPEN"
        else:
            passed = predicted.lower() == tc["expected"].lower()
            if passed:
                correct += 1
            status = "PASS" if passed else "FAIL"

        total_input_tokens  += in_tok
        total_output_tokens += out_tok
        total_time          += elapsed

        results.append({
            "index":     i,
            "label":     tc["label"],
            "input":     tc["input"],
            "expected":  tc["expected"] if tc["expected"] else "(open-ended)",
            "predicted": predicted,
            "full_response": raw_text,
            "passed":    passed,
            "status":    status,
            "in_tok":    in_tok,
            "out_tok":   out_tok,
            "time_s":    elapsed,
        })

        print(f"[{status}] {tc['label']}")

    # Summary metrics
    exact_cases    = len(TEST_CASES) - skipped
    accuracy       = (correct / exact_cases * 100) if exact_cases > 0 else 0
    estimated_cost = (
        total_input_tokens  / 1_000_000 * INPUT_COST_PER_M
        + total_output_tokens / 1_000_000 * OUTPUT_COST_PER_M
    )
    avg_time = total_time / len(TEST_CASES)

    return results, {
        "accuracy":         accuracy,
        "correct":          correct,
        "exact_cases":      exact_cases,
        "skipped":          skipped,
        "total_input_tok":  total_input_tokens,
        "total_output_tok": total_output_tokens,
        "estimated_cost":   estimated_cost,
        "avg_time":         avg_time,
        "total_time":       total_time,
    }


def generate_report(results, metrics):
    now       = datetime.now()
    date_str  = now.strftime("%d %B %Y")
    file_name = f"evaluation_report_{now.strftime('%Y%m%d_%H%M')}.md"

    lines = []
    lines.append(f"# Project Evaluation Report")
    lines.append(f"")
    lines.append(f"**Project:** {PROJECT_NAME}  ")
    lines.append(f"**Prepared by:** {YOUR_NAME}  ")
    lines.append(f"**Submitted to:** {MANAGER_NAME}, {COMPANY}  ")
    lines.append(f"**Date:** {date_str}  ")
    lines.append(f"**GitHub:** {GITHUB_REPO}  ")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Project Overview")
    lines.append(f"")
    lines.append(f"{PROJECT_DESCRIPTION}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Evaluation Summary")
    lines.append(f"")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Model used | `{MODEL}` |")
    lines.append(f"| Total test cases | {len(TEST_CASES)} |")
    lines.append(f"| Exact match tests | {metrics['exact_cases']} |")
    lines.append(f"| Open-ended tests | {metrics['skipped']} |")
    lines.append(f"| Correct (exact) | {metrics['correct']} / {metrics['exact_cases']} |")
    lines.append(f"| **Accuracy** | **{metrics['accuracy']:.1f}%** |")
    lines.append(f"| Total input tokens | {metrics['total_input_tok']:,} |")
    lines.append(f"| Total output tokens | {metrics['total_output_tok']:,} |")
    lines.append(f"| Estimated API cost | ${metrics['estimated_cost']:.6f} USD |")
    lines.append(f"| Avg response time | {metrics['avg_time']:.2f}s |")
    lines.append(f"| Total run time | {metrics['total_time']:.2f}s |")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Test Case Results")
    lines.append(f"")

    for r in results:
        badge = {"PASS": "PASS", "FAIL": "FAIL", "OPEN": "OPEN"}[r["status"]]
        lines.append(f"### [{badge}] {r['label']}")
        lines.append(f"")
        lines.append(f"**Input prompt:**")
        lines.append(f"> {r['input']}")
        lines.append(f"")
        lines.append(f"**Expected:** `{r['expected']}`  ")
        lines.append(f"**Claude responded:** `{r['predicted']}`  ")
        if r["status"] == "OPEN":
            lines.append(f"")
            lines.append(f"**Full response:**")
            lines.append(f"> {r['full_response']}")
        lines.append(f"")
        lines.append(f"*Tokens: {r['in_tok']} in / {r['out_tok']} out | Response time: {r['time_s']:.2f}s*")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

    lines.append(f"## Notes")
    lines.append(f"")
    lines.append(f"- All tests were run against live Claude API (`{MODEL}`).")
    lines.append(f"- Open-ended tests (marked OPEN) were checked only for a non-empty response.")
    lines.append(f"- Cost estimate based on Anthropic pricing: $3.00 / 1M input tokens, $15.00 / 1M output tokens.")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"*Report auto-generated by evaluate_project.py*")

    report_text = "\n".join(lines)

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(report_text)

    return file_name


if __name__ == "__main__":
    results, metrics = run_evaluation()
    report_file      = generate_report(results, metrics)

    print("\n" + "=" * 55)
    print(f"  Accuracy      : {metrics['accuracy']:.1f}%")
    print(f"  Correct       : {metrics['correct']} / {metrics['exact_cases']}")
    print(f"  Est. cost     : ${metrics['estimated_cost']:.6f} USD")
    print(f"  Avg time      : {metrics['avg_time']:.2f}s")
    print("=" * 55)
    print(f"\nReport saved: {report_file}")
    print("Send this file to Florian.")
