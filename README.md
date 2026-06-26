# EHV Automation Tools

Reusable automation scripts for Erste Hausverwaltung GmbH internship projects.
Built by Chibuike Dialaekwe (AI Automation Intern).

**Live repo:** https://github.com/dialaekwechibuike/ehv-automation-tools

---

## What is inside

```
ehv-automation-tools/
├── README.md                        ← you are here
├── evaluator/
│   └── evaluate_project.py          ← main evaluation script
└── COWORK_INSTRUCTIONS.md           ← deployment checklist for Cowork
```

---

## evaluate_project.py

A reusable **AI-assisted project evaluator** for any n8n workflow or automation.

When you finish any project:

1. Open `evaluator/evaluate_project.py`
2. Fill in **only** `PROJECT_NAME` and `PROJECT_DESCRIPTION`
3. Run the script — test cases are invented automatically
4. Send the generated markdown report to Florian

You do **not** write test cases manually.

### What it does

- Invents a full set of test situations from your project description
- Simulates expected automation behaviour for each situation
- Independently judges each case (PASS / CONCERN / FAIL)
- Produces a manager-ready report with score, risks, and recommendations

### What it does NOT do

This tool does **not** call your live n8n workflow or production APIs. It is a
**design-level QA and documentation tool**, not a substitute for testing the
real automation. The generated report states this clearly.

### Requirements

```bash
pip install anthropic
export ANTHROPIC_API_KEY=your_key_here
python evaluator/evaluate_project.py
```

### Optional tuning

Change `NUM_TEST_CASES` in the script if you want more or fewer auto-generated
test situations. The default is `6`.
