# Cowork Task Instructions
> Upload this entire folder to Cowork and say: "Carry out all tasks in COWORK_INSTRUCTIONS.md"

---

## Your Details
- GitHub username: chybyke1992
- Name: Chibuike Dialaekwe
- Company: Erste Hausverwaltung GmbH
- Manager: Florian

---

## Task 1 — Create GitHub Repository

Create a new PUBLIC repository on GitHub under the account `chybyke1992` with:
- Repo name: `ehv-automation-tools`
- Description: `EHV internship automation toolkit — n8n workflow evaluator, project reports, and reusable scripts by Chibuike Dialaekwe`

Then push these files into the repo maintaining this exact folder structure:
```
ehv-automation-tools/
├── README.md
├── evaluator/
│   └── evaluate_project.py
└── COWORK_INSTRUCTIONS.md
```

Use the exact file contents from this uploaded folder. Do not change anything inside the files.

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

If the environment variable ANTHROPIC_API_KEY is available, run:
```
cd ~/Desktop
python evaluate_project.py
```

This will generate a markdown report file on the Desktop named something like:
`evaluation_report_20260626_HHMM.md`

Share the output in chat so we can review the results.

---

## Checklist before finishing — double check all of this:
- [ ] GitHub repo `ehv-automation-tools` is live and public under `chybyke1992`
- [ ] All 3 files are in the repo with correct folder structure
- [ ] `evaluate_project.py` is saved at `~/Desktop/evaluate_project.py`
- [ ] File content was not truncated or modified
- [ ] GitHub repo URL is shared in chat
- [ ] Local file path is confirmed in chat

Do not mark this task complete until every item on the checklist above is confirmed.
