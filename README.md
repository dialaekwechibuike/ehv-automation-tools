# EHV Automation Tools

Reusable automation scripts for Erste Hausverwaltung GmbH internship projects.
Built by Chibuike Dialaekwe (AI Automation Intern).

---

## What is inside

```
ehv-automation-tools/
├── README.md                        ← you are here
├── evaluator/
│   └── evaluate_project.py          ← main evaluation script
└── COWORK_INSTRUCTIONS.md           ← paste this into Cowork to deploy
```

---

## evaluate_project.py

A reusable n8n project evaluator. When you finish any EHV automation project:

1. Open `evaluate_project.py` in Cursor
2. Fill in the CONFIG section at the top (project name, description, GitHub link)
3. Add your test cases
4. Run it — a markdown report is auto-generated
5. Send the report to Florian

### Requirements
```
pip install anthropic
export ANTHROPIC_API_KEY=your_key_here
python evaluator/evaluate_project.py
```
