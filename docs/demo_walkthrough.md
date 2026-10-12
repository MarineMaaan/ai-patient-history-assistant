# Required end-to-end demonstration

Use entirely synthetic data. The persistent notice applies to all views. Run commands from the project root; see README for setup and operating-system equivalents. Default mode must read **Offline rules-based demo — no LLM running.** No local model is installed or run for this demonstration.

## Prepare

Launch `.\.venv\Scripts\python.exe -m streamlit run app.py`, then open `http://127.0.0.1:8501`. The first run imports two explicitly fictional patients and four dated seed sessions. Seed fixtures' historical timestamps are synthetic import timestamps; newly submitted statements use actual application recording time.

If this scenario was already performed, retain it and inspect the timeline or deliberately stop the app and run the confirmed reset command in README. Reseeding without reset does not erase existing answers.

## 1. Ask the unanswered question

Select **Patient A — Avery Example (fictional)**. Set **Simulated role/view** to **Simulated clinician**. Keep identity `Classroom reviewer`. Ask:

> Has this fictional patient ever lost consciousness?

Click **Ask recorded history**. Expected: a persisted clinician question and timestamp; “I found no statement addressing this in the records searched”; no patient claim about consciousness; and a proposed information gap. The output has its own snapshot ID/time/provider/prompt version, separate from source exchanges.

## 2. Approve the neutral follow-up

Expand the consciousness proposal under **Information gaps and follow-up review**. Observe its link to the original clinician question. The neutral default is:

> What, if anything, do you remember about ever fainting, passing out, or losing consciousness?

Click **Approve follow-up**. Only now is it eligible for the patient queue. Repeating the unanswered clinician question before a response links to the same unresolved proposal instead of duplicating it. Editing is allowed before approval; unsafe/leading diagnostic language is rejected by the demonstration guard.

## 3. Simulate due and submit the exact patient response

Click sidebar **Simulate check-in due**. Expected: a due notice; no source timestamps change. Switch to **Patient interview** and click **Start check-in**. The approved question is displayed first; its workflow state becomes asked. Submit:

> I passed out once in July 2025. I don't remember the exact day.

Choose **Answered**, set **Patient-reported event date wording** to `July 2025`, and **Reported event-date precision** to `month`. Click **Save exact response**.

Expected: an immutable original exchange containing exactly that question and answer, a real timezone-aware UTC submission timestamp, `July 2025` separately with month precision, and a null normalized event date. The reported event does not get an invented day. The gap links to this source and becomes answered/resolved by the narrow consciousness-history rule. This recognizes a substantive report, not medical truth.

The check-in next offers the changes question. Answer or explicitly skip it, then click **Complete session**. Expected: last-completed and next-due times persist. Ending a session does not resolve skipped/unknown/ambiguous follow-ups.

## 4. Ask again

Return to **Simulated clinician** and ask the same consciousness question again. Expected: a new derived snapshot backed by the exact response. Click the **Original exchange** source link and expand its question/answer/timestamp. See separate recording time and patient-reported month wording. The old missing-answer snapshot remains unchanged in the timeline.

## 5. Restart and inspect

Stop the Streamlit process with Ctrl+C, then run the launch command again. Choose Patient A and **History & activity**. Expected: the original exchange, clinician questions, both answer snapshots, follow-up links/state, session and schedule remain available. Database location is `local/history.sqlite3`.

## 6. Check Patient B isolation

Select **Patient B — Blake Sample (fictional)** and **Simulated clinician**. Ask the same question. Expected: B's own original denial, “I have never fainted or lost consciousness, as far as I remember.” A's July 2025 response is absent. Patient switching clears prior widget text, output/session IDs and drafts, and all source access remains scoped.

## Additional demonstrations

- **Patient cannot currently answer**: the patient view only offers existing history retrieval. No submission, current-wishes inference or consent is provided.
- **Correction/change/conflict**: expand the append-linked-statement form; inspect the original source; append a new statement with the appropriate relationship. Original text is unchanged, and summaries show linked context together.
- **Skip/unknown/decline**: these persist different answer states. Skipped follow-ups return in a later session; answered-but-unknown/uncertain follow-ups need clinician review/requeue. Declined proposals remain unresolved in history and are not silently re-asked.
- **Missing detail**: ask “What dose of medication was reported?” for A. Existing medication statements are visible, but absent dosage evidence creates a dose follow-up rather than establishing a dose.
- **Provider unavailable**: select Local Ollama without a configured tag. A visible error asks for an explicit mode choice. Do not start a local runtime for this build.

Automation of the central workflow is in `tests/test_ui.py` and `tests/test_workflows.py`; provider tests are mocks. These results do not establish clinical or real-model acceptance.
