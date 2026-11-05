# herdr-qa-plan

Two Claude Code skills for mobile + web QA run by parallel Claude workers in Herdr panes:

- `writing-qa-test-plans/`: writes the QA plan (`SKILL.md`, `plan-template.md`, `strategy-catalog.md`, `baseline-audit.md`, `orchestration-section-template.md`).
- `executing-qa-test-plans/`: runs the plan (`SKILL.md`, `evaluation-standard.md`, `driver-protocol.md`, `devices-and-tools.md`, templates, `scripts/`).

`README.md` explains both for users. When a change alters what a skill asks, does or produces, update the README in the same change.

## Language

Everything is in English: skills, templates, scripts, README, this file, commit messages. Spanish appears only where it is data, never prose:

- example app texts in scenarios ("Iniciar sesión");
- the bilingual conversation-language question;
- the `es` strings of `render-results.py`.

## Contracts between files

- `make-package.sh` and `check-report.py` find plan sections and suite header fields by exact text. The headings in `plan-template.md` and the header-line field names (`Strategy`, `Lane`, `Tool`, `Spend`, …) stay as they are, in English; renaming one means changing the scripts in the same commit.
- Scenario IDs are read from `| S-0NN-NN |` table rows.
- Sections marked `(orchestrator-only section)` are never copied into worker packages.
- Both skills are manual only (`disable-model-invocation: true`). Keep it.

## Scripts

- Bash scripts run on macOS bash 3.2: no associative arrays, no `mapfile`, no `${var,,}`.
- Python scripts use the standard library only and run with `/usr/bin/python3` (3.9+). `check-report.py` imports the parser of `render-results.py`.
- Pinned versions: Maestro 2.11.0 and `@playwright/mcp@0.0.83`. Never `@latest`.

## Verifying a change

Build a worker package from the template; it must print the package path and the standard sections:

```bash
d=$(mktemp -d) && mkdir -p "$d/run"
awk '/^````markdown$/{f=1;next} /^````$/{f=0} f' writing-qa-test-plans/plan-template.md > "$d/plan.md"
bash executing-qa-test-plans/scripts/make-package.sh --plan "$d/plan.md" --suite S-001 --model sonnet \
  --why test --run-id r1 --run-dir "$d/run" --device emulator-5554 --evidence ev --root "$d"
```

For a change to the money guard, also set a suite's `**Spend:**` and check that the test and verify packages are refused without a `Money movement (D<n>)` block in `--notes`.

## Git

- Branch from `main`: `feature/`, `fix/`, `chore/`.
- Conventional commits (`feat:`, `fix:`, `chore:`, `refactor:`).
- Merge into `main` with `git merge --no-ff -m "merge: <branch>"`.
- Push only when asked.
- Never commit `__pycache__/`.
