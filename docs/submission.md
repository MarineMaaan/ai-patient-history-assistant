# Assignment and GitHub handoff

Submit this **actual public GitHub repository URL containing the commented source code**:

[https://github.com/MarineMaaan/ai-patient-history-assistant](https://github.com/MarineMaaan/ai-patient-history-assistant)

Publication under **MarineMaaan**, repository name **ai-patient-history-assistant**, and **public** visibility was explicitly approved on 2026-10-12. The repository was created through GitHub's REST API using the existing Git Credential Manager authentication, then pushed with Git. GitHub CLI was not installed. The authenticated account was checked before creation; credential values were kept in memory and never printed or tracked. No global configuration was changed.

Local branch `main` tracks `origin/main` at `https://github.com/MarineMaaan/ai-patient-history-assistant.git`. GitHub metadata confirmed public visibility and main as the default branch; remote main was checked against local HEAD after the push. An unauthenticated metadata request also confirmed public accessibility. The running local demonstration server was stopped at the user's request.

The assignment submission is the repository URL above. Additional architecture, research, demonstration and test documents support review; they are not represented as explicitly required by the instructor. Source, synthetic fixtures, version-pinned dependencies and documentation are tracked. Runtime data/configuration, the virtual environment, SQLite sidecars, logs/exports, caches, the task-local publication helper, and weights remain ignored. No license was added or granted.

## Reviewer access

The repository is public; reviewers can open the URL and inspect the commented source without a private-repository invitation. Individual instructor access has not been separately exercised. This publishes source only: the Streamlit application has not been deployed, exposed remotely, or given external notifications.

## Inspect and update

From this project directory:

```powershell
git status --short
git remote -v
git log --oneline -3
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

For future authorized source updates, run relevant tests, inspect intended diffs, stage explicit paths, and run `.\.venv\Scripts\python.exe scripts/audit_repository.py` before committing/pushing. Push with `git push origin main`, then compare remote main's hash with local HEAD. `.gitignore` does not remove previously tracked files. Preserve remotes; never force-push or rewrite user history. Changing repository visibility, inviting reviewers, granting a license, or deploying a live application requires separate authorization.
