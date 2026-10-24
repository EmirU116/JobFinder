# Contributing to JobFinder

Read `CLAUDE.md` first. It defines the project and agent rules that every change must respect.

## Branches
- `main` is always runnable. It is protected: no direct pushes and no force-pushes.
- Create one short-lived branch per change from an up-to-date `main`:
  ```
  git switch main; git pull
  git switch -c feat/indeed-source-hints
  ```
- Prefixes:

  | Prefix | Use for |
  |---|---|
  | `feat/` | new capability (new tool, new CLI option) |
  | `fix/` | bug fix |
  | `prompt/` | changes to agent prompts or the profile schema only |
  | `refactor/` | code restructuring with no behavior change |
  | `docs/` | README, CLAUDE.md, CONTRIBUTING.md |
  | `chore/` | dependencies, config, tooling |

- Use lowercase kebab-case names that describe the change, e.g. `fix/csv-dedupe-trailing-slash`.
- Rebase on `main` before opening the PR (`git pull --rebase origin main`). Delete the branch after merging.

## Commits
Use [Conventional Commits](https://www.conventionalcommits.org/):
```
<type>(optional scope): <imperative summary, max ~72 chars>

<why the change was needed, if not obvious>
```
Types: `feat`, `fix`, `prompt`, `refactor`, `docs`, `chore`, `test`.
Examples: `feat(review): add --list option`, `prompt(job-hunter): require deadline extraction`.

- Each commit is one logical change and leaves the project runnable.
- Never commit `data/`, `output/`, `.env`, API keys, or real CVs or letters. Check `git status` before every commit.

## Pull requests
1. Keep PRs small and focused, ideally under about 300 changed lines. Split unrelated changes into separate PRs.
2. Title in Conventional Commit format, e.g. `feat: add Platsbanken API tool`.
3. Fill in every section of `.github/pull_request_template.md`:
   - what changed and why
   - how you tested it (commands plus results; for prompt changes, a short summary of a `--jobs-per-agent 1` run)
   - the agent-rules checklist
4. Get at least one approving review before merging. The author merges once CI or checks are green.
5. Use **squash merge** so `main` has one commit per PR with the PR title as its message.

### Changes that need extra care in review
- **Agent rules** (CLAUDE.md § Agent rules): anything that could let an agent submit applications, write files directly, or use new tools. These need the project owner's explicit approval.
- **CSV schema / statuses:** must stay backward-compatible with existing `applications.csv` files.
- **Prompts:** state the expected behavior change and include evidence from a test run.
- **Cost:** changes to the model, agent count, budget, or turn limits must state the expected cost per run.

## Code review checklist (for reviewers)
- [ ] Follows the layering (prompts / config / store / tools)
- [ ] No personal data or secrets in the diff
- [ ] The agent rules still hold (human in the loop, no fabrication, least privilege, dedupe)
- [ ] Tested as described, with results in the PR
- [ ] README/CLAUDE.md updated if behavior or usage changed
