# MFEC LiteLLM Model Selection for the Real-LLM Pilot

## Decision

The MFEC endpoint is sufficient for an infrastructure pilot and a three-agent
Real-LLM study. The catalog retrieved on 2026-09-23 contained 21 model IDs.
However, the endpoint exposes deployment aliases rather than immutable public
model snapshots. Therefore, the paper must describe these as MFEC deployment
IDs and record the retrieval date, returned model ID, provider route (if
available), generation settings, token usage, latency, and price actually
charged.

## Recommended primary team

Use three models from the same visible family to reduce cross-vendor
confounding:

1. `gemini-3-flash`
2. `gemini-3.5-flash`
3. `gemini-3.8-flash`

This set is a candidate team, not a predefined Ability Rank 1-3 ordering.
Assign ranks only after held-out executable probes. Version numbers, price,
latency, and model names are not measures of ability. If two candidates cannot
be separated by the predeclared confidence rule, report a tied/overlapping
ability band or replace one candidate before freezing the main experiment.

## Recommended robustness team

If the primary team has insufficient ability separation, use a deliberately
heterogeneous cross-family team as a secondary robustness condition:

1. `gpt-5-mini`
2. `gemini-3.8-flash`
3. `claude-sonnet-5`

This design improves the chance of meaningful capability heterogeneity but
introduces vendor/family confounding. It should not replace the within-family
primary comparison.

## Models not recommended for the primary team

- `text-embedding-3-large`: not a generative task-solving agent.
- `perplexity`: likely a search-oriented route; its external retrieval changes
  the information condition.
- `mfec-coding`: underlying model/version is not identifiable from the alias.
- Mixed `flash`/`pro` pairs alone: useful for robustness but confound model
  capability with service tier.

## Required gates before research execution

1. Confirm all three IDs accept the same chat-completions interface.
2. Obtain or record alias-to-underlying-model mapping and effective dates if
   MFEC can provide them.
3. Freeze generation parameters and disable any silent model fallback.
4. Record actual token usage, wall-clock latency, retry count, returned model
   ID, and charged price per request.
5. Rank ability using held-out executable ML Build and Fix Bug probes.
6. Keep the 60 analysis cases separate from the ability-ranking probes.
7. Treat a backend alias change during collection as a protocol deviation.

The sanitized catalog is stored in `mfec_model_catalog.json`; no API key is
stored in that file.

## Infrastructure smoke result

On 2026-09-23, all three primary-team candidates completed a minimal request
through `/v1/chat/completions`. The returned model IDs matched the requested
IDs. Each request reported 14 total tokens; the one-shot latencies were 1,428
ms (`gemini-3-flash`), 1,009 ms (`gemini-3.5-flash`), and 1,396 ms
(`gemini-3.8-flash`). These values establish API feasibility only. They must
not be interpreted as comparative performance, model ability, or stable
latency estimates. The sanitized record is stored in
`mfec_smoke_results.json`.
