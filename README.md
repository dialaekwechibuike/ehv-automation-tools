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

A reusable **AI-assisted project evaluator** for n8n and similar automations.

When you finish any EHV automation project:

1. Open `evaluator/evaluate_project.py` in Cursor
2. Fill in the CONFIG section (project name + description)
3. Add a few test situations to `CASES` (or leave empty for AI-generated cases)
4. Run the script — a markdown report is auto-generated
5. Send the report to Florian

### What it does

- Invents edge cases you may not have thought of
- Simulates expected automation behaviour from your description
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

### Example cases (format)

```python
CASES = [
    "A tenant emails about a burst pipe at 11pm and marks it urgent.",
    "A marketing newsletter arrives in the shared inbox with no tenant ID.",
    "Two emails about the same heating issue arrive 5 minutes apart.",
]
```

Replace these with situations that match **your** project before running.
