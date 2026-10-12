# Assignment and GitHub handoff

The assignment submission is the **actual GitHub repository URL containing the commented source code**. Submit that URL once publication is authorized and verified. Additional architecture, research, demonstration and test documents support review; they are not represented as explicitly required by the instructor.

The local repository is on `main`, with no remote configured at creation. Source, synthetic fixtures, version-pinned dependencies and documentation are tracked. Runtime data/configuration, virtual environment, SQLite sidecars, logs/exports, caches and weights remain ignored. No license was added or granted. Use `git log --oneline -2` and `git status --short` to inspect the delivered commits/state.

## Remaining approval and tooling

Publication requires the user's approved **GitHub owner/account**, **repository name**, and **public/private visibility**. These choices remain unresolved; no repository has been published and there is no GitHub URL yet. GitHub CLI (`gh`) was not available on this machine during inspection. Installing system-wide tooling requires separate approval. Existing authenticated tooling can be used when authorized; do not print credentials or invent a remote URL.

## Prepared commands — only after approval

Run from the project root. Replace `<OWNER>` and `<REPOSITORY>` with approved values and choose exactly one visibility flag. The placeholders are unresolved. These commands assume GitHub CLI is available and authenticated in the correct account:

```powershell
gh auth status
git remote -v
git status --short
git ls-files
git diff --cached --stat
# Choose --private OR --public according to explicit approval.
gh repo create <OWNER>/<REPOSITORY> --private --source . --remote origin --push
gh repo view <OWNER>/<REPOSITORY> --json url,visibility
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Compare remote main's hash to local HEAD before reporting success. Obtain the actual repository URL from `gh repo view`; do not construct it from a guessed username. If a remote now exists, preserve it and inspect it before using `--remote origin`; do not replace or delete it. Never force-push or rewrite user history. Recheck tracked and staged content for credentials and runtime data before any push; `.gitignore` does not remove already-tracked files.

If CLI installation is unavailable, the user may create an **empty** repository in the approved account through GitHub's UI, then provide its actual clone URL. With that authorized URL, preserving existing remotes:

```powershell
git remote -v
git remote add origin <ACTUAL_APPROVED_CLONE_URL>
git push -u origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Create it without adding a README, license, or `.gitignore` to avoid unrelated history conflicts. The second path assumes origin is absent; use a separate approved remote name if it already exists.

## Reviewer access

A public repository can be opened by the reviewer using the verified URL. A private repository needs a user-approved reviewer-access arrangement. Do not invite people or change visibility without approval. Confirm that the intended reviewer can access the submitted URL and see commented source; an inaccessible private URL is not a complete handoff.
