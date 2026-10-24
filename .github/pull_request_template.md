## What & why
<!-- What does this PR change, and why is it needed? Link the issue if there is one. -->

## Type
- [ ] feat
- [ ] fix
- [ ] prompt
- [ ] refactor
- [ ] docs
- [ ] chore

## How I tested it
<!-- Commands you ran and what happened. For prompt/orchestration changes, summarize a `python main.py --jobs-per-agent 1` run (jobs found, letter language correct, cost). Never paste real CV content or letters. -->

## Agent rules checklist (CLAUDE.md)
- [ ] Agents still cannot submit applications or contact employers (status stays `ready_for_review`)
- [ ] No new tools given to agents, or new tools are listed and justified here
- [ ] Letters still use only CV facts, in the ad's language
- [ ] CSV schema/status changes are backward-compatible (or N/A)
- [ ] Budget/turn guardrails still set
- [ ] No personal data, `data/`, `output/`, or secrets in the diff

## Notes for reviewers
<!-- Risks, follow-ups, or expected cost impact. -->
