# AI Patient History Assistant

A working local classroom application for **fictional patient history capture and evidence retrieval**. A clinician's unanswered question produces a proposed follow-up; approval adds it to a patient check-in; the exact submitted response enriches the record; a fresh query can cite it. This does not retrain a model.

> Educational prototype. Synthetic data only. Not for diagnosis, treatment, emergencies, or real patient records. This application is not monitored.

## Quick start — Windows PowerShell

Python 3.11 and Git are prerequisites. Python **3.11.9** was actually tested. No model, GPU, credentials, or hosted service is needed for offline mode. From this project's directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m history_assistant.cli seed
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open [the loopback application](http://127.0.0.1:8501). Stop with Ctrl+C. A project venv has already been installed for this handoff; skip its creation if using this checkout as delivered. No PowerShell activation or execution-policy change is needed.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/audit_repository.py
```

## Equivalent macOS/Linux commands

These instructions have not been executed on macOS/Linux. Use Python 3.11:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m history_assistant.cli seed
.venv/bin/python -m streamlit run app.py
.venv/bin/python -m pytest -q
```

`requirements-lock.txt` pins the actual installed direct and transitive versions; `requirements.txt` includes that lock. It is a version-pinned manifest, not a cryptographic hash lock. The tested environment was Windows NT build 26300, SQLite 3.45.1, Streamlit 1.65.0, Pydantic 2.14.1, pytest 9.1.1, and httpx 0.28.1. See [test report](docs/test_report.md) for measured results.

## Modes

**Offline rules-based demo — no LLM running.** This is the default, visibly labeled mode. It searches stored original exchanges using topic synonyms and text, and returns exact source answers. It works on newly submitted inputs, not only the fixtures. Rules-based date clarification is available for uncertain responses without event wording.

**Local Ollama adapter.** The code implements `/api/tags`, `/api/show`, and structured `/api/chat` requests. It requires an explicitly configured exact local model tag. It refuses non-loopback endpoints, cloud tags/remote metadata, missing local artifacts, unconfirmed completion capability, invalid output, and invalid evidence. It uses no tools, redirects, proxy environment, cloud fallback, model installation, or runtime startup. There is a 30-second default per-request timeout, at most one retry per HTTP call, bounded input/output, and temperature zero.

Per the user's instruction, **no local model was installed or run** during this build. Ollama client 0.20.3 was detected; a read-only runtime probe before that instruction found no running loopback server. All adapter tests used mocked HTTP. No claim of real-model compatibility or quality has been established.

To configure an already installed local runtime in a future authorized session, copy `config.example.toml` to ignored `local/config.toml`, set `ollama_model` to its exact installed tag, and explicitly select **Local Ollama** in the sidebar. The default remains offline. Starting a runtime or downloading weights is the user's separate decision. Do not use a cloud-backed model. Ollama's documented local-only environment setting is `OLLAMA_NO_CLOUD=1`; this application does not modify global runtime configuration. The optional test command, **only after explicit authorization**, is:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m live_model --run-live-model
```

Failures appear visibly and preserve original records. Choosing offline mode is an explicit user action, never a hidden fallback.

## Classroom demo

1. Select fictional Patient A and **Simulated clinician**. Ask the default consciousness-history question. Observe missing evidence and a proposed follow-up.
2. Expand the proposal; approve its neutral question.
3. Click **Simulate check-in due**, switch to **Patient interview**, and **Start check-in**.
4. Submit `I passed out once in July 2025. I don't remember the exact day.` Set event wording to `July 2025` and precision to `month`.
5. Complete the session, switch to clinician, and ask again. Expand the linked source to see the exact question, response, UTC recording time, and separate month-precision event wording.
6. Restart the app, inspect the timeline, then select Patient B and ask again. B's own explicit historical denial is shown; A's response is not available in B's context.

Full steps and expected results are in [demo walkthrough](docs/demo_walkthrough.md).

## Storage and safe reset

Runtime database: `local/history.sqlite3`, created automatically on first app open or seed command. Configuration, data, SQLite sidecars, exports/logs, secrets, caches, venvs, and model weights are ignored. The local directory is not served as static content. `seed` is idempotent and preserves existing demo work.

For a destructive **full synthetic-data reset**, stop Streamlit and deliberately confirm with the exact phrase:

```powershell
.\.venv\Scripts\python.exe -m history_assistant.cli reset --confirm "RESET SYNTHETIC DATA"
```

macOS/Linux: `.venv/bin/python -m history_assistant.cli reset --confirm "RESET SYNTHETIC DATA"`. Reset is restricted to the resolved project-local `.sqlite3` target and exact sidecars. It reseeds two fictional patients and removes added statements, outputs, and workflow history. There is no automatic reset on startup.

## Inspect and extend

- `app.py`: Streamlit rendering, forms, role/view selection, and per-context widget clearing.
- `history_assistant/schema.sql`, `db.py`: constraints, immutable originals, patient-scoped access and transactions.
- `service.py`: interviewing, scheduling, querying, snapshots, gap lifecycle and idempotency.
- `interview.py`, `fixtures/questions.json`: editable demonstration question library and neutral question rules.
- `retrieval.py`, `evidence.py`: original-record search and claim validation.
- `providers.py`, `prompts.py`, `models.py`: offline/Ollama boundary, versioned prompts and Pydantic contracts.
- `fixtures/synthetic_patients.json`: explicit synthetic import data with historical seed timestamps.
- `tests/`: temporary DB workflows, adversarial citations, mocked providers, AppTest UI coverage, and optional live test.

Change the library JSON intentionally; generated questions never modify it. Extend topic synonyms and detail checks with synthetic relevance tests. Keep future providers behind the existing interface and preserve patient scoping, full source visibility, and append-only corrections. [Architecture](docs/architecture.md) traces the runtime sequence.

## Limitations and troubleshooting

This is not production authentication/access control, encryption-at-rest, audited tamper resistance, HIPAA compliance, clinical validation, diagnosis, triage, treatment guidance, or a monitored service. Do not enter real records. An unavailable patient enables existing-record retrieval only; no current wishes or consent are inferred. No notification is delivered while the application is closed.

Retrieval and question screening are deliberately small heuristic rules. They can miss synonyms or nuanced unsafe/leading language; source matching does not establish medical truth. This version rejects free-form model paraphrases and uses full verbatim answers. Dosage, frequency, and exact-date questions have conservative missing-detail checks; other complex multi-part questions need source review and may require a manually edited follow-up. Automatic gap resolution is limited to narrow consciousness-history examples; ambiguous/substantive other answers require a reviewer explanation. Declined/unknown/skipped are never denials.

Related corrections, changes, and conflicts remain visible together; the newest statement is not automatically declared correct. Event dates are never normalized automatically. Relevant context over 50 records or 40,000 estimated characters blocks generation instead of silently removing records; all original exchanges remain inspectable. Prompt-injection tests establish application boundaries for synthetic examples, not immunity of arbitrary models.

If the port is busy, use `--server.port 8502` while retaining loopback binding. If a form action fails, check nonempty answers, approved question state, precision/wording consistency, and patient selection. A saved statement stays saved even when interpretation fails. If Ollama is unconfigured/unavailable, explicitly choose Offline demo. If a summary is stale, generate a new one before review. SQLite reset errors on Windows usually mean an app process still has the database open.

Published with the user's approval as the public repository [MarineMaaan/ai-patient-history-assistant](https://github.com/MarineMaaan/ai-patient-history-assistant). [Submission handoff](docs/submission.md) gives the assignment URL, reviewer access, and update commands. The local demonstration server was stopped after the handoff; use the launch command above to run it again. No software license has been granted.
