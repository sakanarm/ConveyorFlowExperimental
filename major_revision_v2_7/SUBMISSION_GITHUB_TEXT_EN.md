# GitHub text for manuscript submission (v2.7, Rev5)

Use the **frozen commit**, not a moving `main` link:

https://github.com/sakanarm/ConveyorFlowExperimental/tree/691bc9e1397b45f9948069d4b6b44b0e48d8e826

## IEEE manuscript and AJSTR unblinded manuscript: Data and Code Availability

Experimental code, frozen configurations, public-data manifests, analysis scripts, derived aggregate results, and editable diagrams are available at https://github.com/sakanarm/ConveyorFlowExperimental/tree/691bc9e1397b45f9948069d4b6b44b0e48d8e826 (frozen commit 691bc9e). The v2.7 extension is in `major_revision_v2_7`, with `REPRODUCE_V27.ps1` documenting the checks and optional fresh run. Public datasets and bug benchmarks remain at their upstream sources under their licenses. API credentials, raw provider responses, heavy container artifacts, and working manuscripts are not public. Repository hashes and audit capsules do not by themselves recreate historical provider calls; a fresh run needs independent provider access and records its own model identity, timestamps, and outputs.

## AJSTR blinded manuscript: Data and Code Availability

The replication package contains experimental code, frozen configurations, public-data manifests, analysis scripts, derived results, and editable diagrams. Its author-identifying GitHub URL is omitted from this blinded manuscript and will be supplied to the editorial office separately. Public datasets and bug benchmarks remain at their upstream sources under their licenses. API credentials, raw provider responses, and heavy container artifacts are not public. Repository hashes and audit capsules therefore do not by themselves recreate historical provider calls; a fresh run needs independent provider access and records new dated outputs.

## Separate note to the editor for blinded review

Dear Editor,

For the Data and Code Availability statement, the author-identifying public replication repository is https://github.com/sakanarm/ConveyorFlowExperimental/tree/691bc9e1397b45f9948069d4b6b44b0e48d8e826. Please keep this URL outside the blinded reviewer manuscript. The frozen repository contains the experimental code, configurations, manifests, analysis scripts, derived results, editable diagrams, and reproduction instructions. It does not contain API credentials, raw provider responses, or heavy container artifacts. A reviewer can inspect the published audit trail and run a new experiment with independent provider access, but the public package alone cannot replay the historical provider calls. Please advise if the journal has a preferred anonymous-access procedure for the code during review.

Sincerely,
The authors

## Submission check

- Keep the full GitHub URL in the IEEE and AJSTR unblinded versions only.
- Send the separate editor note through the submission system, not inside the blinded manuscript.
- Do not describe the repository as a complete archive of historical raw LLM responses.
- Cite the exact frozen commit in the submitted text even if `main` advances later.
