# Execution and validation report

Executed on **2026-10-12** in the local project directory. Evidence below is software behavior on synthetic data, not clinical validation. Per the user's explicit instruction, no local model was installed or run.

## Environment actually tested

| Component | Observed version/value |
|---|---|
| OS | `Windows-10-10.0.26300-SP0` (Python platform report); Windows NT build 26300 |
| Python | 3.11.9, project-local `.venv` |
| SQLite | 3.45.1 |
| Streamlit | 1.65.0 |
| Pydantic | 2.14.1 |
| pytest | 9.1.1 |
| httpx | 0.28.1 |
| Git | 2.45.2.windows.1 |
| Ollama client | 0.20.3 detected by read-only version check; no live server/inference tested |
| GitHub CLI | Not present during tooling inspection |

The installed Python 3.14 was detected but not used. `requirements-lock.txt` records the actual installed direct/transitive packages. macOS/Linux setup instructions are provided but were not executed.

## Commands and results

Commands were run from the project root in Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install streamlit pydantic pytest httpx
.\.venv\Scripts\python.exe -m pip freeze
.\.venv\Scripts\python.exe -m history_assistant.cli seed
.\.venv\Scripts\python.exe -m compileall -q app.py history_assistant tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q --tb=short
.\.venv\Scripts\python.exe -m streamlit run app.py
```

- Final pytest result: **55 passed, 1 skipped in 37.30 seconds**. The skipped test is the optional real-model test. No final test failures remained.
- Compilation: exit 0, no reported syntax errors.
- Dependency integrity: `No broken requirements found.`
- Seeding: successful. Repeated seeding in tests preserved existing statements and did not reset runtime data.
- Actual Streamlit process: started successfully, printed loopback URL. HTTP `/` returned **200**; `/_stcore/health` returned **200**, body `ok`. The listener was observed at **127.0.0.1:8501**.
- The task-owned Streamlit child was identified through its project-venv parent, stopped, and relaunched after final code changes. The loopback application was checked again from this fresh process.
- Real browser: loaded title **AI Patient History Assistant** and rendered the patient selector, simulated role controls, offline provider label, persistent educational notice, scheduling controls, and interview controls. This supplements AppTest; it is not a real-model or clinical test.
- Installed Streamlit config inspection confirmed address `127.0.0.1`, CORS enabled, XSRF enabled, static serving disabled, and usage telemetry disabled.
- Git ignore inspection confirmed the runtime SQLite database and venv interpreter are ignored. Explicit staged/tracked review preceded local commits.
- `scripts/audit_repository.py` was executed against staged/index and tracked HEAD blobs, with no findings for its defined token/private-key patterns or prohibited runtime paths. This narrow heuristic supplements manual inspection and is not a comprehensive secrets/security audit.

An early test run exposed an output-table INSERT placeholder-count mismatch; it was corrected. Subsequent passing runs were 47/1, then 54/1, then final 55/1 after additional evidence-boundary and missing-dose checks. The final result is the relevant acceptance evidence; no failed attempt is presented as a pass.

## What the automated tests establish

Temporary SQLite database tests exercise the required no-evidence query → proposal → approval → simulated due → exact submitted response → fresh supported query → restart → Patient B isolation sequence. They check original question/answer wording, real injected UTC recording time, separate July 2025 month precision, null normalized day, follow-up/clinician/source links, and preservation of the old missing-answer snapshot.

Additional tests check explicit denial versus missing/declined/skipped/unknown/uncertain states; original/derived separation; deduplication; edits/approval/dismissal/skipping/requeue/manual resolution; immutable originals; linked corrections/changes/conflicts; patient-scoped reads/writes and foreign keys; idempotent tokens and altered-content rejection; clock/schedule/restart behavior; confirmed reset and containment; clarification failures, repeated/out-of-scope questions; and stale summary review.

Adversarial citation tests reject nonexistent, wrong-patient, out-of-context and irrelevant sources, plus exact-wording/negation changes and omitted correction context. The same-patient asthma source cited for a consciousness question is explicitly rejected. A green-color answer to a consciousness question is not accepted as substantive consciousness evidence. Asthma and migraine are tested as distinct synthetic entities. A medication mention without dosage remains insufficient for a dose query. These are defined semantic examples, not a general clinical relevance classifier.

Mocked HTTP/provider tests check structured `/api/chat` requests, schema/output validation, lack of tools, local-tag/artifact/metadata checks, cloud/remote rejection, malformed responses, bounded retries, timeout visibility, and absence of hidden offline substitution. Prompt-injection examples remain inert stored text and cannot change patient context or obtain tools.

Streamlit `st.testing.v1.AppTest` drives the full feedback loop through actual widget submissions, confirms the source/event-date fields, completes a check-in, repeats the query, switches patients, and creates a new app test instance against the same database to verify persistence. A second UI test checks retrieval-only mode for an unavailable patient and the visible unconfigured-Ollama error. AppTest is a framework-driven UI test, not human usability or accessibility acceptance.

## Live-model check deliberately not performed

Before the user's prohibition, read-only tooling inspection found an installed Ollama client but no running loopback runtime. No model inventory was available. No weights were downloaded, runtime started, model selected, paid/hosted endpoint used, or real inference run. The adapter is implemented and tested with mocks only. The real-model test defaults to skip and requires `--run-live-model` as an explicit opt-in in a future authorized session. No installation approval is requested for this build because the user specifically declined local-model operation.

## Significant limits

Software tests do not establish medical truth, clinical safety, HIPAA compliance, production readiness, authentication, encryption-at-rest, model quality, or hardware compatibility. Neutral-question and topic/detail checks are small rules with limited coverage. Unknown/complex language may require original-record review. Full verbatim output intentionally rejects many plausible LLM paraphrases. Ambiguous gaps remain unresolved until explicit review, and older snapshots do not silently change. No notification is delivered while the app is closed.

GitHub publication and reviewer access remain untested/pending user approval. See `submission.md` for exact remaining commands and unresolved placeholders.
