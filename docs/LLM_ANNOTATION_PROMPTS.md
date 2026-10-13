# Frozen LLM Annotation Role Prompts

All passes used the same shared protocol and rubric, isolated conversation contexts,
different deterministic row shuffles, and the same underlying Codex GPT-5-family
session model. The exact deployment snapshot and sampling controls were not exposed
to the workspace; this is a reproducibility limitation.

## Shared instructions

- Read `EXPERT_LABEL_PROTOCOL.md` and `DIFFICULTY_RUBRIC.md` completely.
- Read only the assigned blinded packet.
- Do not inspect another pass, merged labels, simulator code, pilot results,
  allocation outcomes, or provisional difficulty.
- Score ambiguity, scope, dependency, reasoning, and verification from 0 to 2.
- Map total 0–3 to D1, 4–6 to D2, and 7–10 to D3 without discretion.
- Score failure impact 1–3 separately and confidence 1–5.
- Preserve item metadata and provide a concise rationale.

## Pass 1 — ML Methodologist

Focus on data/model assumptions, analytical choices, and reasoning burden while
following the shared rubric.

## Pass 2 — Software Reliability Reviewer

Focus on dependencies, failure modes, testing, and verification burden while
following the shared rubric.

## Pass 3 — Workflow/Resource Reviewer

Focus on scope, coordination, operational execution, and resource burden while
following the shared rubric.

## Adjudication pass — Senior Methods Adjudicator

Read the merged ratings only after the three passes are complete. Preserve unanimous
labels. For every non-unanimous item, independently resolve the disagreement using
the visible task metadata, rubric, and three rationales. Do not mechanically force
the majority when the task evidence supports another level. Do not inspect any
simulation outcome.
