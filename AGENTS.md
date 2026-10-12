# Project invariants

- Educational synthetic-data prototype only; preserve the persistent notice.
- Original exchanges are immutable. Append linked corrections/changes/conflicts.
- Patient scope is trusted application context; never obtain it from model text.
- Only original exchanges support claims. Never use AI outputs or clinician questions as patient facts.
- Validate every claim's IDs, patient, retrieved set, relevance, and exact full answer.
- Render patient/model content as safe plain text. Preserve negation, uncertainty, and full question context.
- Recording timestamps come from an injected aware clock in UTC; event dates remain reported wording. No invented exact day.
- Follow-ups require explicit approval before asking. Skipping/declining/unknown responses do not resolve information gaps.
- Save exact patient submissions transactionally before optional model interpretation. Keep idempotency tokens.
- Do not share conversation/cache state across patients. Snapshots stay historical; new history requires a fresh query.
- Bind to loopback; retain CORS/XSRF protections. No external notifications, hosted fallback, tools for models, or real records.
- Local mode never downloads or starts models. Live inference requires explicit user authorization; this build was requested without running a local model.
- Keep local data/config, databases/sidecars, exports/logs, secrets, weights, and .venv ignored. Reset requires the typed phrase in seed.py and containment checks.
- GitHub publication needs approved owner/name/visibility; do not grant a license or change global Git settings.

## Commands (project root)

PowerShell: `.\.venv\Scripts\python.exe -m streamlit run app.py`; `.\.venv\Scripts\python.exe -m pytest -q`; `.\.venv\Scripts\python.exe -m history_assistant.cli seed`.

macOS/Linux: use `.venv/bin/python` instead. Install with `python -m pip install -r requirements.txt` inside the project venv.

Optional live-model tests are skipped unless `--run-live-model` is explicitly passed. Do not pass it without authorization. See README.md and docs/test_report.md for proof boundaries.
