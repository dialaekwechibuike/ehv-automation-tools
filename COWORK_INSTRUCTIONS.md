# Cowork Task Instructions
> Upload this entire folder to Cowork and say: "Carry out all tasks in COWORK_INSTRUCTIONS.md"

---

## Your Details
- GitHub username: dialaekwechibuike
- Name: Chibuike Dialaekwe
- Company: Erste Hausverwaltung GmbH
- Manager: Florian

---

## Task 1 — GitHub Repository

Ensure the PUBLIC repository exists under `dialaekwechibuike`:
- Repo name: `ehv-automation-tools`
- Description: `EHV internship automation toolkit — n8n workflow evaluator, project reports, and reusable scripts by Chibuike Dialaekwe`
- URL: https://github.com/dialaekwechibuike/ehv-automation-tools

Push these files maintaining this exact folder structure:
```
ehv-automation-tools/
├── README.md
├── evaluator/
│   └── evaluate_project.py
└── COWORK_INSTRUCTIONS.md
```

Confirm when done by sharing the live GitHub repo URL.

---

## Task 2 — Save Locally on Mac

Save the file `evaluator/evaluate_project.py` to this exact path on the Mac:
```
~/Desktop/evaluate_project.py
```

Confirm the file is saved and the path is correct.

---

## Task 3 — Run the Evaluation Script (optional, only if ANTHROPIC_API_KEY is set)

Before running, edit the CONFIG section in the script:
- Set `PROJECT_NAME`
- Set `PROJECT_DESCRIPTION`

Do not add manual test cases. The script generates them automatically.

Then run:
```bash
cd ~/Desktop
export ANTHROPIC_API_KEY=your_key_here
python evaluate_project.py
```

This will generate a markdown report on the Desktop named something like:
`evaluation_report_20260626_HHMM.md`

Share the output in chat so we can review the results.

---

## Checklist before finishing
- [ ] GitHub repo `ehv-automation-tools` is live and public under `dialaekwechibuike`
- [ ] All 3 files are in the repo with correct folder structure
- [ ] `evaluate_project.py` is saved at `~/Desktop/evaluate_project.py`
- [ ] CONFIG placeholders were replaced before any test run
- [ ] GitHub repo URL is shared in chat
- [ ] Local file path is confirmed in chat

Do not mark this task complete until every item on the checklist above is confirmed.
