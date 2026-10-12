# Concept research and design rationale

Verified against the primary publication/specification pages on **2026-10-12**. The project target was at least three relevant sources, including scholarly research and a primary record/provenance source; that target is not represented as an instructor rule. These sources inform design choices. None validates this prototype clinically.

## 1. Scholarly research — peer-reviewed review, not a preprint

**Authors:** Lorainne Tudor Car, Dhakshenya Ardhithy Dhinagaran, Bhone Myint Kyaw, Tobias Kowatsch, Shafiq Joty, Yin-Leng Theng, and Rifat Atun. **Title:** *Conversational Agents in Health Care: Scoping Review and Conceptual Analysis*. **Published:** August 7, 2020. *Journal of Medical Internet Research*, 22(8), e17158. **DOI:** [10.2196/17158](https://doi.org/10.2196/17158). [Publisher full text](https://www.jmir.org/2020/8/e17158/).

The review maps healthcare conversational-agent applications and calls for stronger evaluation of acceptability, safety, and effectiveness. Its evidence is about other systems; it does not establish benefits of our application. The publisher identifies the final article's peer-review history and separately links an earlier preprint. This document relies on the final peer-reviewed publication.

**Design proposal informed by it:** keep a narrow educational history-recording purpose; show limitations prominently; separately test workflow, source handling, and provider errors. Our offline software results are not clinical effectiveness evidence. Diagnosis, treatment and triage remain outside this application.

## 2. Primary specification — structured question/answer records

**Organization:** HL7 International, FHIR Infrastructure Work Group. **Title:** *FHIR R4 Resource QuestionnaireResponse — Content*, v4.0.1, Technical Correction #1. **Version-page generation date:** November 1, 2019. [Permanent R4 specification page](https://hl7.org/fhir/R4/questionnaireresponse.html).

QuestionnaireResponse represents ordered questions and their answers, including question wording and who answered. It separates the form definition from a response instance and distinguishes responses at different times/for different subjects. Its author/source/authored fields provide a useful record-design reference.

**Design proposal informed by it:** retain each exact eliciting question alongside the original answer, respondent, session and recording time; keep the editable question library separate from submitted responses. The SQLite schema is inspired by these concepts; it is **not** a FHIR server, export, implementation guide, or claim of conformance. The cited historical R4 page is deliberately versioned, not described as the latest release.

## 3. Primary specification — provenance and recording time

**Organization:** HL7 International, Security Work Group. **Title:** *FHIR R4 Resource Provenance — Content*, v4.0.1, Technical Correction #1. **Version-page generation date:** November 1, 2019. [Permanent R4 specification page](https://hl7.org/fhir/R4/provenance.html).

The resource describes the provenance of creation/change activities, their targets, participants and source entities. Its distinction between activity occurrence and recording time informs the separation between when a patient reports an event happened and when this app captured the statement.

**Design proposal informed by it:** attach stable original-source IDs to derived outputs; preserve recording timestamps; retain separately reported imprecise event wording; append linked corrections instead of destroying originals. Basic activity rows and immutability triggers do not implement signatures, non-repudiation, audited tamper resistance, or comprehensive FHIR provenance.

## Research versus prototype results

The sources support conceptual distinctions and evaluation caution. The feedback loop, manual approval controls, conservative extractive claim policy, and injected-clock tests are this project's proposals/implementation. Automated synthetic tests establish behavior for their examples. Mocked Ollama tests establish adapter request/validation paths. No study participant evaluation, real patient data, real-model test, medical-truth verification, or clinical-safety validation was undertaken.

## Technical implementation references (separate from healthcare research)

Official documentation inspected for this implementation on 2026-10-12:

- [Streamlit project config](https://docs.streamlit.io/develop/api-reference/configuration/config.toml): loopback binding, telemetry setting, static serving and CORS/XSRF configuration. Local installed configuration was also checked.
- [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest): script/widget testing used with installed Streamlit 1.65.0.
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [chat API](https://docs.ollama.com/api/chat), and [show-model details](https://docs.ollama.com/api-reference/show-model-details): JSON-schema requests, model metadata and application-side validation. No inference was performed.
- [Ollama cloud documentation](https://docs.ollama.com/cloud) and [FAQ](https://docs.ollama.com/faq): a local endpoint alone is not proof of local inference; cloud aliases are refused and installed artifact metadata is checked. The FAQ documents `OLLAMA_NO_CLOUD=1`; no global settings were changed.
- [pytest temporary directories](https://docs.pytest.org/en/stable/how-to/tmp_path.html): isolated test databases.
- [Git initialization](https://git-scm.com/docs/git-init) and [GitHub CLI repository creation](https://cli.github.com/manual/gh_repo_create): local main branch and prepared publication handoff. GitHub CLI was not installed and no publication occurred.
