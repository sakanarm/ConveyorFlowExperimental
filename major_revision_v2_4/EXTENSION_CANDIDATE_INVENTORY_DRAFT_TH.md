# Candidate inventory for a larger ecological Real-LLM study (draft, no paid calls)

This is a pre-qualification inventory, **not** a frozen extension cohort, power calculation, or claim that the cases already pass the container gates. The running v2.4 resume is untouched. The 11 potentially complete paired blocks remain a bounded pilot after the block-03 interruption.

## New public ML corpora

The current mixed-job study repeats Adult and Beijing. Two plausible additional source datasets, each above the original 20,000-row threshold, are:

| Candidate | Official source | Rows | Intended task | Qualification still required |
|---|---|---:|---|---|
| Bank Marketing (`bank-full.csv`, not its 10% sample) | [UCI dataset 222](https://archive.ics.uci.edu/dataset/222/bank+marketing) | 45,211 | Binary classification | Freeze file hash and train/test split; decide whether `duration` is excluded to avoid post-call information leakage; build four-stage DAG and independent verifier. |
| Covertype | [UCI dataset 31](https://archive.ics.uci.edu/dataset/31/covertype) | 581,012 | Seven-class classification | Freeze file hash and split; bound runtime/memory in the same container; build four-stage DAG and independent verifier. |

Both UCI records identify CC BY 4.0 licenses. Dataset size alone does not establish task independence: several DAG cases from one corpus remain clustered by corpus. Online Retail has 541,909 transactions but is **not** an automatic drop-in because a defensible label/target and leakage-safe split would need separate design.

## New repository clusters

The local public BugsInPy metadata snapshot contains 17 projects. The current main study uses 4: FastAPI, Luigi, Matplotlib, and pandas. Thirteen other project names are present: ansible, black, cookiecutter, httpie, keras, PySnooper, sanic, scrapy, spacy, thefuck, tornado, tqdm, and youtube-dl. The inventory is source metadata only; it says nothing yet about container reproducibility, patch scope, test reliability, or rights to redistribute repository snapshots. [BugsInPy's research description](https://arxiv.org/abs/2401.15481) reports real Python bugs across 17 projects.

The frozen local metadata manifest (BugsInPy source commit `11c5f1eea954a42132cfd06bf257766a7963e0fd`) contains the following *candidate counts*, not qualified independent observations: ansible 18, black 23, cookiecutter 4, httpie 5, keras 45, PySnooper 3, sanic 5, scrapy 40, spacy 10, thefuck 32, tornado 16, tqdm 9, and youtube-dl 43. This is 253 metadata entries across the 13 as-yet-unused projects. The counts are useful for estimating qualification effort, but no row enters the study until the same container and verifier gates pass. Existing v2.3 preflight/smoke exposure (including tornado) must be checked by exact case ID before declaring any case new.

Before paid extension calls: freeze a hash-sorted pre-outcome-blind project/case queue that excludes all prior-exposed case IDs; verify buggy-fail/fixed-pass, public regression baseline, allowed production paths, prompt context, container replay, and source-import identity for each case. Keep every exclusion with a reason. At least four **new qualified projects** beyond the current four are a diversity target, not a power guarantee; the final number of projects and cases must come from the prespecified precision/power simulation, with conservative variance assumptions, before extension execution. Do not enlarge `n` by treating stages, retries, or repeated prompts on the same bug as independent projects.

## Decision gate

No extension paid calls until the current audited pilot is complete or transparently halted, outcome definitions and smallest effects of interest are signed off, source/verifier hashes are frozen, and the sample-size/precision simulation is stored with the new execution lock. If qualification cannot reach the needed independent projects/datasets, narrow the paper claim rather than silently substituting cases after seeing LLM outcomes.
