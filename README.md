# ConveyorFlow Experimental Package

Reproducibility package for **ConveyorFlow: Decentralized Capability-Aware Self-Selection for Heterogeneous LLM Agent Teams**.

ConveyorFlow keeps tasks on a shared READY belt. Idle agents inspect visible tasks, estimate feasibility and difficulty, volunteer for one task, and contend through an atomic compare-and-swap claim. CF-Fit prioritizes capability-task fit; an overqualified agent may stand down temporarily, while aging and bounded relaxation prevent indefinite waiting. Static and centralized controls use the same workloads, task dependencies, belt semantics, and one-task-per-agent limit; only the allocation decision changes.

## Evidence in this repository

- Frozen simulation design: 22,500 runs, 50 paired seeds, common random numbers.
- Public-workload-derived ML Build and Fix Bug tasks: UCI Adult, Beijing Multi-Site Air Quality, and CodeXGLUE Bugs2Fix.
- Real-LLM validation: 60 frozen cases, deterministic validators, three allocation policies, and ten paired seeds.
- Role-conditioned LLM difficulty labels, prompts, agreement analysis, adjudication log, and frozen labels. These are **not independent human-expert labels**.
- Aggregate results, statistical summaries, figures, source diagrams, manuscript, and advisor presentation.

The large per-run event ledgers and raw upstream datasets are intentionally not stored in Git. They can be regenerated from the frozen configuration and download scripts. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

## Quick start

Tested with Python 3.12 on Windows. The simulation code itself is cross-platform; the convenience script below is PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest tests -q
```

Validate the frozen design without executing all 22,500 runs:

```powershell
python scripts/run_main.py --check-design
```

Download and prepare public data:

```powershell
python scripts/download_data.py
python scripts/prepare_data.py
```

Run the full simulation and analysis:

```powershell
python scripts/run_main.py --workers 8
python scripts/analyze_main.py
python scripts/analyze_secondary_extensions.py --workers 8
python scripts/verify_artifacts.py --output results/main
```

The full run creates several gigabytes of append-only event ledgers under `results/main/events/`. Runtime depends on CPU, disk, and worker count.

## Real-LLM execution

The vendor-neutral harness, 60 case bundles, validators, frozen allocation logic, and aggregate results are included under `real_llm_pilot/`. A dry run does not call any provider:

```powershell
python real_llm_pilot/run_pilot.py `
  --config real_llm_pilot/config.mfec_main_frozen.json `
  --cases real_llm_pilot/case_manifest.csv `
  --dry-run
```

Live re-execution requires a reviewer-supplied OpenAI-compatible endpoint configuration and API key. Never commit credentials. Provider aliases, latency, prices, and backend model snapshots may drift, so live Real-LLM runs are re-executions under a documented provider state, not bit-for-bit reproductions of historical wall-clock behavior.

## Repository map

- `Code/conveyorflow_v2/` — simulation engine, state transitions, metrics, and workload generation.
- `config/` — frozen simulation configurations.
- `scripts/` — data preparation, runners, analyses, figures, manifests, and artifact verification.
- `tests/` — unit and integrity tests for simulation and Real-LLM paths.
- `docs/` — research protocol, RQ-to-metric map, algorithms, rubrics, preregistration, and reviewer audit.
- `expert_labels/` — AI-label protocol, blinded packets, agreement results, adjudication, and frozen labels.
- `data/` — source manifest and derived metadata; `data/raw/` is excluded.
- `results/main/` — aggregate simulation tables, figures, hashes, and source snapshot; event ledgers are excluded.
- `real_llm_pilot/` — provider-neutral harness, case bundles, validators, frozen metadata, aggregate results, and figures; raw call directories are excluded.
- `ConveyorFlow_diagrams_en_working.drawio` — editable architecture and belt diagrams.
- `ConveyorFlow_IEEE_Manuscript.docx` — current manuscript draft.
- `presentation/` — advisor deck, talk script, and Q&A material.

## Reproducibility boundary

Simulation outputs are designed for exact seeded reproduction, subject to the recorded Python environment and source snapshot. Real-LLM outputs are reproducible at the protocol, case, validator, allocation, and analysis levels; exact generations and timing depend on the external provider state.

## Security and disclosure

- No API key or bearer token is stored in this repository.
- AI-assisted difficulty annotation is disclosed and is not represented as human ground truth.
- Human-expert validation remains a pre-submission item.
- Authors remain responsible for all claims, code, analyses, and final prose. See [AI_USE_DISCLOSURE.md](docs/AI_USE_DISCLOSURE.md).

## Citation and license

Citation metadata is provided in `CITATION.cff`. A software license has not yet been selected; reuse rights remain reserved until the author adds a license. Dataset use remains subject to each upstream source license.
