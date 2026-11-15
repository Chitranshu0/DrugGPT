# Safety and scope

DrugGPT answers medical science and drug-study questions only. It is designed for students and researchers.

## What DrugGPT does

- Searches locally indexed medical PDFs and answers only when relevant evidence is found.
- Displays the supporting source and page for every grounded answer.
- Declines unrelated questions, patient-specific diagnosis/dosing/treatment requests, and urgent-care situations.
- Routes medication-related requests through a clinician review step before returning guidance.
- Applies deterministic guardrails (`triage_query`) to classify each question as emergency, out-of-scope, general, symptom, or medication review.

## What DrugGPT does NOT do

- It is **not** a diagnostic, prescribing, or emergency-care service.
- It does not give individual doses or personal medical advice.
- It does not replace qualified healthcare professionals.

## Emergency handling

If a message matches emergency patterns (for example chest pain, difficulty breathing, overdose, or self-harm), DrugGPT returns emergency guidance and directs the user to contact local emergency services or the nearest emergency department immediately.

## Clinician review

Medication-related requests are drafted internally and paused with an `interrupt`. They are only returned to the user after a clinician approves them through the `/reviews/{review_id}/decision` endpoint or the Streamlit Clinician Review page. Rejected reviews result in a safety refusal.

## Verification

Verify research conclusions against the original materials and qualified professionals. If no indexed source sufficiently supports a question, DrugGPT provides general educational information rather than inventing an answer.
