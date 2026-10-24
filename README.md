# JobFinder

A multi-agent job search assistant built on the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/python). See `Project Idea.png`.

1. **Context:** an agent reads your CV (`data/cv.pdf`) and builds `data/profile.json` with your skills, target roles, locations and preferred work modes. You confirm the profile or edit it.
2. **Team:** the same agent acts as the **lead** and launches 3 **job-hunter** subagents in parallel, each with its own search slice. Each subagent:
   search for jobs → read the job ad → write a cover letter in the ad's language → "send"
3. **"Send"** saves the letter to `output/letters/<job_id>.md` and adds a row to `output/applications.csv` with status `ready_for_review`. **Nothing is submitted automatically.** You review each application and apply yourself.

## Setup (Windows PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # or be logged in to Claude Code
```
Copy your CV to `data\cv.pdf`.

## Web UI (recommended)
```powershell
streamlit run app.py
```
Opens at http://localhost:8501 with these pages:

| Page | What it does |
|---|---|
| **Dashboard** | Key numbers, status and work-mode charts, upcoming deadlines, recently found jobs, results per agent |
| **Review queue** | Reviews applications one at a time, with an editable cover letter: approve, skip, or open the ad |
| **All applications** | The CSV as a filterable table (search, status, work mode, agent). Select a row to edit its status, notes, deadline and letter. Export to CSV |
| **CV & profile** | Upload a CV, rebuild the profile with the agent, and edit the profile fields |
| **Run search** | Choose the number of agents and jobs per agent, start or stop a run, and follow the live log |

## Command line
```powershell
python main.py                       # read CV (first time) + run the 3 agents
python main.py --jobs-per-agent 1    # small test run
python main.py --refresh-profile     # re-read the CV
python main.py --profile-only        # only build the profile

python review.py                     # read each letter, approve / skip / open the ad
python review.py --list              # overview of all jobs
python review.py --mark <job_id> applied   # applied | interview | rejected | offer | skipped
```

## CSV columns
`job_id, date_found, company, role, location, work_mode, status, url, source, language, deadline, apply_method, letter_path, agent_id, notes`

Status flow: `ready_for_review` → `approved` → `applied` → `interview` / `rejected` / `offer` (or `skipped`).

## Configuration
`jobfinder/config.py` sets the model, the number of agents, jobs per agent, and the budget and turn limits (`MAX_BUDGET_USD` stops a run that gets too expensive).
