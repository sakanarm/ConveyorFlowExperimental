param(
    [ValidateSet('Check', 'MatchedVerify', 'MatchedRun', 'MatchedAnalyze',
                 'PilotDryRun', 'PilotExecute', 'PilotAudit', 'LivePreflight', 'BugsPreflightStatus',
                 'CalibrationSummary', 'OverheadVerify', 'OverheadRun',
                 'OverheadLoadVerify', 'OverheadLoadRun', 'PodmanVerify',
                 'PilotV3Audit', 'PilotV3Execute', 'RepositoryPilotAudit',
                 'RepositoryPilotExecute', 'RepositoryDecoderReplay', 'RepositoryDecoderAudit',
                 'RepositoryContractAudit', 'BugsCalibrationPreflightStatus', 'BugsCalibrationPreflightExecute',
                 'RepositoryFirstAttemptAudit', 'RepositoryFirstAttemptPrepare', 'RepositoryFirstAttemptExecute',
                 'MLIsolatedStageAudit', 'MLIsolatedStageExecute', 'MLIsolatedStageFinalize',
                 'EcologicalAudit', 'EcologicalMainReadiness', 'EcologicalDryRun', 'EcologicalMLPrepare',
                 'EcologicalDecisionCheck', 'EcologicalClaimCheck', 'CodeCheck',
                 'EcologicalMLCalibrationAudit', 'EcologicalMLCalibrationFreeze',
                 'EcologicalMLCalibrationExecute', 'EcologicalMLContinuationFreeze',
                 'EcologicalMLContinuationExecute', 'EcologicalMLContinuation2Freeze',
                 'EcologicalMLContinuation2Execute', 'EcologicalRepositoryCalibrationAudit',
                 'EcologicalMLContinuation3Health', 'EcologicalMLContinuation3Freeze',
                 'EcologicalMLContinuation3Execute', 'EcologicalMLContinuation3Pause',
                 'EcologicalMLContinuation3Finalize',
                 'EcologicalIntegrationEventCheck',
                 'EcologicalRepositoryCalibrationFreeze', 'EcologicalRepositoryCalibrationExecute',
                 'EcologicalRepositoryCalibrationFinalize', 'EcologicalIntegrationCheck',
                 'EcologicalMLCalibrationFinalize')]
    [string]$Stage = 'Check',
    [string]$CaseId = 'ADULT_P1',
    [string]$ModelSlot = 'agent_1',
    [string]$CalibrationManifest,
    [string]$CalibrationLedger,
    [string]$OutputPath,
    [ValidateRange(1, 8)][int]$Workers = 4,
    [switch]$ConfirmPaidRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$v2Root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$major = 'major_revision_v2_3'

function Invoke-Python {
    param([string[]]$Arguments)
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python step failed with exit code $LASTEXITCODE"
    }
}

function Invoke-BugsSelection {
    $taskSerialRecoveryLedger = "$major/results/bugsinpy_serial_build_recovery_v6_protocol/combined_prefix_ledger.jsonl"
    $taskExtensionLedger = "$major/results/bugsinpy_prefix_extension_v4/combined_prefix_ledger.jsonl"
    $taskRecoveryLedger = "$major/results/bugsinpy_environment_recovery_v3/combined_prefix_ledger.jsonl"
    $taskOrderedLedger = "$major/results/bugsinpy_preflight_v2_ledger.jsonl"
    if (Test-Path -LiteralPath $taskSerialRecoveryLedger) {
        Invoke-Python @("$major/select_bugsinpy_pilot.py", '--ledger', $taskSerialRecoveryLedger)
    } elseif (Test-Path -LiteralPath $taskExtensionLedger) {
        Invoke-Python @("$major/select_bugsinpy_pilot.py", '--ledger', $taskExtensionLedger)
    } elseif (Test-Path -LiteralPath $taskRecoveryLedger) {
        Invoke-Python @("$major/select_bugsinpy_pilot.py", '--ledger', $taskRecoveryLedger)
    } elseif (Test-Path -LiteralPath $taskOrderedLedger) {
        Invoke-Python @("$major/select_bugsinpy_pilot.py", '--ledger', $taskOrderedLedger)
    } else {
        Invoke-Python @("$major/select_bugsinpy_pilot.py")
    }
}

Push-Location -LiteralPath $v2Root
try {
    switch ($Stage) {
        'CodeCheck' {
            # Portable code/contracts only: no private ledgers, provider or containers.
            Invoke-Python @('-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py')
            Write-Host 'Code/contract tests complete; this does not reproduce paid model outcomes.'
        }
        'EcologicalMLCalibrationAudit' {
            Invoke-Python @("$major/ecological_v1/audit_ml_calibration.py")
        }
        'EcologicalRepositoryCalibrationAudit' {
            Invoke-Python @("$major/ecological_v1/audit_repository_calibration.py")
        }
        'EcologicalMLCalibrationFinalize' {
            if (-not $OutputPath) { throw 'Provide a NEW -OutputPath inside major_revision_v2_3/results.' }
            Invoke-Python @("$major/ecological_v1/finalize_ml_calibration_v1.py", '--output', $OutputPath)
        }
        'EcologicalMLContinuation3Finalize' {
            if (-not $OutputPath) { throw 'Provide a NEW -OutputPath inside major_revision_v2_3/results.' }
            Invoke-Python @("$major/ecological_v1/finalize_ml_calibration_v3.py", '--output', $OutputPath)
        }
        'EcologicalIntegrationEventCheck' {
            if (-not $OutputPath) { throw 'Provide a NEW -OutputPath inside major_revision_v2_3/ecological_v1.' }
            Invoke-Python @("$major/ecological_v1/check_integration_backend_v2.py", '--out', $OutputPath)
        }
        { $_ -in @('EcologicalMLContinuation3Health','EcologicalMLContinuation3Freeze',
                   'EcologicalMLContinuation3Execute','EcologicalMLContinuation3Pause') } {
            $taskPaid = $Stage -eq 'EcologicalMLContinuation3Execute'
            if ($taskPaid -and (-not $ConfirmPaidRun -or -not $env:MFEC_LITELLM_API_KEY)) {
                throw 'Process credential and -ConfirmPaidRun are required for billable calls.'
            }
            $taskLinuxV2 = (& wsl -d Ubuntu -e wslpath -a $v2Root).Trim()
            if ($LASTEXITCODE -ne 0 -or -not $taskLinuxV2) { throw 'Unable to resolve workspace in WSL.' }
            $taskEco = "$taskLinuxV2/$major/ecological_v1"
            $taskImageLock = "$taskLinuxV2/$major/ml_eval_image_lock_podman_v1.json"
            if ($Stage -eq 'EcologicalMLContinuation3Health') {
                & wsl -d Ubuntu -u root -e env CONVEYORFLOW_CONTAINER_COMMAND=podman `
                    CONVEYORFLOW_EVALUATOR_LOCK=$taskImageLock python3 -c `
                    "import sys; sys.path.insert(0,sys.argv[1]); from ml_backend_health_v2 import probe,ROOT; report=probe(ROOT/'backend_health_continuation_3_prestart'); assert report['status']=='backend_health_passed'" $taskEco
            } elseif ($Stage -eq 'EcologicalMLContinuation3Pause') {
                & wsl -d Ubuntu -u root -e env CONVEYORFLOW_CONTAINER_COMMAND=podman `
                    CONVEYORFLOW_EVALUATOR_LOCK=$taskImageLock python3 `
                    "$taskEco/continue_ml_calibration_v3.py" --request-pause
            } elseif ($Stage -eq 'EcologicalMLContinuation3Freeze') {
                & wsl -d Ubuntu -u root -e env CONVEYORFLOW_CONTAINER_COMMAND=podman `
                    CONVEYORFLOW_EVALUATOR_LOCK=$taskImageLock python3 `
                    "$taskEco/continue_ml_calibration_v3.py" --freeze
            } else {
                $env:MFEC_LITELLM_API_KEY | & wsl -d Ubuntu -u root -e python3 `
                    "$taskEco/wsl_continuation_v3_bridge.py" continue_ml_calibration_v3.py --execute
            }
            if ($LASTEXITCODE -ne 0) {
                throw 'Continuation 3 step failed; audit evidence before any retry.'
            }
        }
        'EcologicalRepositoryCalibrationFinalize' {
            if (-not $OutputPath) { throw 'Specify a new result directory with -OutputPath.' }
            Invoke-Python @("$major/ecological_v1/finalize_repository_calibration.py", '--output', $OutputPath)
        }
        { $_ -in @('EcologicalMLContinuation2Freeze','EcologicalMLContinuation2Execute',
                   'EcologicalRepositoryCalibrationFreeze','EcologicalRepositoryCalibrationExecute') } {
            $taskPaid = $Stage.EndsWith('Execute')
            if ($taskPaid -and (-not $ConfirmPaidRun -or -not $env:MFEC_LITELLM_API_KEY)) {
                throw 'Process credential and -ConfirmPaidRun are required for billable calls.'
            }
            $taskIsML = $Stage.StartsWith('EcologicalMLContinuation2')
            $taskRunner = if ($taskIsML) { 'continue_ml_calibration_v2.py' } else { 'run_repository_calibration.py' }
            $taskBridge = if ($taskIsML) { 'wsl_continuation_v2_bridge.py' } else { 'wsl_repository_calibration_bridge.py' }
            $taskLinuxV2 = (& wsl -d Ubuntu -e wslpath -a $v2Root).Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Unable to resolve workspace in WSL.' }
            $taskEco = "$taskLinuxV2/$major/ecological_v1"
            if ($taskPaid) {
                $env:MFEC_LITELLM_API_KEY | & wsl -d Ubuntu -u root -e python3 "$taskEco/$taskBridge" $taskRunner --execute
            } else {
                & wsl -d Ubuntu -u root -e env CONVEYORFLOW_CONTAINER_COMMAND=podman `
                    CONVEYORFLOW_EVALUATOR_LOCK="$taskLinuxV2/$major/ml_eval_image_lock_podman_v1.json" `
                    python3 "$taskEco/$taskRunner" --freeze
            }
            if ($LASTEXITCODE -ne 0) { throw 'Controller stopped; audit evidence before explicit recovery. Do not duplicate paid requests.' }
        }
        { $_ -in @('EcologicalMLCalibrationFreeze','EcologicalMLCalibrationExecute',
                   'EcologicalMLContinuationFreeze','EcologicalMLContinuationExecute') } {
            $taskPaid = $Stage.EndsWith('Execute')
            if ($taskPaid -and -not $ConfirmPaidRun) {
                throw 'This stage makes billable MFEC calls; add -ConfirmPaidRun explicitly.'
            }
            $taskContinuation = $Stage.StartsWith('EcologicalMLContinuation')
            $taskRunner = if ($taskContinuation) { 'continue_ml_calibration.py' } else { 'run_ml_calibration.py' }
            $taskBridge = if ($taskContinuation) { 'wsl_continuation_bridge.py' } else { 'wsl_calibration_bridge.py' }
            $taskLinuxV2 = (& wsl -d Ubuntu -e wslpath -a $v2Root).Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Unable to resolve the workspace in WSL.' }
            $taskEcologicalRoot = "$taskLinuxV2/$major/ecological_v1"
            if ($taskPaid) {
                if (-not $env:MFEC_LITELLM_API_KEY) { throw 'Required process credential is missing.' }
                # Key goes through stdin, never a command-line argument or file.
                $env:MFEC_LITELLM_API_KEY | & wsl -d Ubuntu -u root -e python3 "$taskEcologicalRoot/$taskBridge" $taskRunner --execute
            } else {
                & wsl -d Ubuntu -u root -e env CONVEYORFLOW_CONTAINER_COMMAND=podman python3 "$taskEcologicalRoot/$taskRunner" --freeze
            }
            if ($LASTEXITCODE -ne 0) { throw 'Ecological controller stopped; audit evidence, never blindly restart.' }
        }
        'Check' {
            Invoke-Python @('-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py')
            if (Test-Path -LiteralPath "$major/results/matched_v1/main/manifest.json") {
                Invoke-Python @("$major/verify_matched_v1.py")
            } else {
                Write-Host 'Frozen matched result artifact is absent; integrity verification skipped.'
            }
            if (Test-Path -LiteralPath "$major/results/overhead_proxy_v1/main/manifest.json") {
                Invoke-Python @("$major/verify_overhead_proxy_v1.py")
            } else {
                Write-Host 'Local IPC overhead proxy artifact is absent; integrity verification skipped.'
            }
            if (Test-Path -LiteralPath "$major/results/overhead_load_v1/main/manifest.json") {
                Invoke-Python @("$major/verify_overhead_load_v1.py")
            } else {
                Write-Host 'Concurrent IPC overhead proxy artifact is absent; integrity verification skipped.'
            }
            Invoke-BugsSelection
            $completed = @(Get-ChildItem -LiteralPath "$major/candidate_workspaces" `
                -Recurse -Filter 'dag_summary.json' -File -ErrorAction SilentlyContinue)
            if ($completed.Count -gt 0) {
                Invoke-Python @("$major/audit_ml_dag_pilots.py")
            } else {
                Write-Host 'No local completed ML DAG pilot ledger; pilot audit skipped.'
            }
            if (Test-Path -LiteralPath "$major/ml_eval_image_lock_podman_v1.json") {
                Invoke-Python @("$major/verify_podman_lock.py")
            }
            if (Test-Path -LiteralPath "$major/ml_dag_pilot_v3_lock.json") {
                Invoke-Python @("$major/audit_ml_dag_pilot_v3.py")
            }
            if (Test-Path -LiteralPath "$major/repository_repair_pilot_v1_lock.json") {
                Invoke-Python @("$major/audit_repository_repair_pilot_v1.py")
            }
            if (Test-Path -LiteralPath "$major/candidate_workspaces/repository_decoder_replay_v2/summary.json") {
                Invoke-Python @("$major/audit_repository_decoder_replay_v2.py")
            }
            if (Test-Path -LiteralPath "$major/results/repository_contract_smoke_v3_audit_20261005.json") {
                Invoke-Python @("$major/audit_repository_contract_smoke_v3.py")
            }
            if (Test-Path -LiteralPath "$major/repository_first_attempt_v1_lock.json") {
                Invoke-Python @("$major/audit_repository_first_attempt_v1.py")
            }
            if (Test-Path -LiteralPath "$major/results/bugsinpy_calibration_preflight_v1/lock.json") {
                Invoke-Python @("$major/audit_bugsinpy_calibration_preflight_v1.py")
            }
            if (Test-Path -LiteralPath "$major/ml_isolated_stage_pilot_v2_lock.json") {
                Invoke-Python @("$major/audit_ml_isolated_stage_pilot_v2.py")
            }
            if (Test-Path -LiteralPath "$major/ecological_v1/prepared_design/lock.json") {
                Invoke-Python @("$major/ecological_v1/audit_preparation.py")
            }
            Write-Host 'v2.3 offline checks complete. This is not a real-LLM main experiment.'
        }
        'EcologicalAudit' {
            Invoke-Python @("$major/ecological_v1/audit_preparation.py")
        }
        'EcologicalMLPrepare' {
            # Trusted numeric reference only: no provider/candidate/container execution.
            Invoke-Python @("$major/ecological_v1/prepare_ml_case.py", '--case-id', $CaseId)
        }
        'EcologicalDryRun' {
            if (-not $OutputPath) {
                throw 'Provide a NEW -OutputPath inside major_revision_v2_3/ecological_v1 (relative to v2 or absolute).'
            }
            Invoke-Python @("$major/ecological_v1/run_dry.py", '--out-dir', $OutputPath)
        }
        'EcologicalDecisionCheck' {
            if (-not $OutputPath) {
                throw 'Provide a NEW .json -OutputPath inside major_revision_v2_3/ecological_v1.'
            }
            Invoke-Python @("$major/ecological_v1/check_decision_processes.py", '--out', $OutputPath)
        }
        'EcologicalClaimCheck' {
            if (-not $OutputPath) {
                throw 'Provide a NEW probe directory -OutputPath inside major_revision_v2_3/ecological_v1.'
            }
            Invoke-Python @("$major/ecological_v1/check_shared_claim.py", '--out', $OutputPath)
        }
        'EcologicalIntegrationCheck' {
            if (-not $OutputPath) {
                throw 'Provide a NEW probe directory -OutputPath inside major_revision_v2_3/ecological_v1.'
            }
            Invoke-Python @("$major/ecological_v1/check_integration_backend_v1.py", '--out', $OutputPath)
        }
        'EcologicalMainReadiness' {
            Invoke-Python @("$major/ecological_v1/check_main_readiness_v1.py")
        }
        'MatchedVerify' {
            Invoke-Python @("$major/verify_matched_v1.py")
        }
        'MatchedRun' {
            if (Test-Path -LiteralPath "$major/results/matched_v1/main") {
                throw 'Frozen matched main results already exist; refusing to overwrite. Verify them with -Stage MatchedVerify.'
            }
            Invoke-Python @("$major/run_matched_v1.py", '--workers', "$Workers")
        }
        'MatchedAnalyze' {
            if (-not (Test-Path -LiteralPath "$major/results/matched_v1/main/manifest.json")) {
                throw 'Matched main run is missing.'
            }
            if (Test-Path -LiteralPath "$major/results/matched_v1/main/analysis_overview.json") {
                throw 'Frozen matched analysis already exists; refusing to overwrite.'
            }
            Invoke-Python @("$major/analyze_matched_v1.py")
        }
        'PilotDryRun' {
            Invoke-Python @("$major/run_ml_dag_llm_feasibility.py", '--case-id', $CaseId,
                            '--model-slot', $ModelSlot)
        }
        'PilotExecute' {
            if (-not $ConfirmPaidRun) {
                throw 'PilotExecute makes billable MFEC calls; add -ConfirmPaidRun explicitly.'
            }
            if (-not $env:MFEC_LITELLM_API_KEY) {
                throw 'MFEC_LITELLM_API_KEY is absent from this process environment.'
            }
            Invoke-Python @("$major/run_ml_dag_llm_feasibility.py", '--case-id', $CaseId,
                            '--model-slot', $ModelSlot, '--execute')
        }
        'PilotAudit' {
            Invoke-Python @("$major/audit_ml_dag_pilots.py")
        }
        'LivePreflight' {
            Invoke-Python @("$major/run_ml_dag_llm_feasibility.py", '--check-container')
        }
        'BugsPreflightStatus' {
            Invoke-BugsSelection
        }
        'PodmanVerify' {
            Invoke-Python @("$major/verify_podman_lock.py")
        }
        'PilotV3Audit' {
            Invoke-Python @("$major/audit_ml_dag_pilot_v3.py")
        }
        'PilotV3Execute' {
            if (-not $ConfirmPaidRun -or -not $env:MFEC_LITELLM_API_KEY) {
                throw 'Provide the key only in the process environment and add -ConfirmPaidRun.'
            }
            $taskLinuxRoot = (& wsl -d Ubuntu -e wslpath -a $v2Root).Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Ubuntu WSL is unavailable' }
            $env:MFEC_LITELLM_API_KEY | & wsl -d Ubuntu -u root -e python3 `
                "$taskLinuxRoot/$major/wsl_provider_bridge.py" run_ml_dag_pilot_v3.py `
                --case-id $CaseId --model-slot $ModelSlot
            if ($LASTEXITCODE -ne 0) { throw 'Pilot v3 stopped; inspect evidence before another run' }
        }
        'RepositoryPilotAudit' {
            Invoke-Python @("$major/audit_repository_repair_pilot_v1.py")
        }
        'RepositoryDecoderAudit' {
            Invoke-Python @("$major/audit_repository_decoder_replay_v2.py")
        }
        'RepositoryContractAudit' {
            Invoke-Python @("$major/audit_repository_contract_smoke_v3.py")
        }
        'RepositoryFirstAttemptAudit' {
            if (-not (Test-Path -LiteralPath "$major/repository_first_attempt_v1_lock.json")) {
                throw 'First-attempt model protocol has not frozen yet; audit new-case preflight/preparation instead.'
            }
            Invoke-Python @("$major/audit_repository_first_attempt_v1.py")
        }
        'RepositoryFirstAttemptPrepare' {
            if (Test-Path -LiteralPath "$major/candidate_workspaces/repository_first_attempt_v1_preparation") {
                throw 'Context/identity preparation has started; inspect preserved artifacts before recovery. Refusing a duplicate worker.'
            }
            $taskLinuxRoot = (& wsl -d Ubuntu -e wslpath -a $v2Root).Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Ubuntu WSL is unavailable' }
            & wsl -d Ubuntu -u root -e env CONVEYORFLOW_CONTAINER_COMMAND=podman python3 `
                "$taskLinuxRoot/$major/prepare_repository_first_attempt_v1.py" --all
            if ($LASTEXITCODE -ne 0) { throw 'Preparation stopped; preserve evidence before recovery.' }
        }
        'MLIsolatedStageAudit' {
            Invoke-Python @("$major/audit_ml_isolated_stage_pilot_v2.py")
        }
        'MLIsolatedStageFinalize' {
            # Offline only. The finalizer refuses partial pairs and existing output.
            Invoke-Python @("$major/finalize_ml_stage_pilot_v2.py", '--out-dir',
                            "$major/results/ml_isolated_stage_pilot_v2_final")
        }
        'MLIsolatedStageExecute' {
            if (-not $ConfirmPaidRun -or -not $env:MFEC_LITELLM_API_KEY) {
                throw 'Process credential and -ConfirmPaidRun are required.'
            }
            if (-not (Test-Path -LiteralPath "$major/ml_isolated_stage_pilot_v2_lock.json")) {
                throw 'Require frozen prompts and all twelve trusted reference probes.'
            }
            $taskFrozenStages = Get-Content -LiteralPath "$major/ml_isolated_stage_pilot_v2_lock.json" -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($ModelSlot -notin @($taskFrozenStages.model_slots)) { throw 'Unknown frozen model slot.' }
            foreach ($taskProbe in $taskFrozenStages.probes) {
                if (Test-Path -LiteralPath "$major/candidate_workspaces/ml_isolated_stage_pilot_v2/$($taskProbe.probe_id)_${ModelSlot}") {
                    throw 'This slot has already started. Audit before any recovery; no blind paid rerun.'
                }
            }
            $taskLinuxRoot = (& wsl -d Ubuntu -e wslpath -a $v2Root).Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Ubuntu WSL unavailable.' }
            $env:MFEC_LITELLM_API_KEY | & wsl -d Ubuntu -u root -e python3 `
                "$taskLinuxRoot/$major/wsl_ml_stage_probe_bridge_v2.py" run_ml_isolated_stage_pilot_v2.py `
                --slot $ModelSlot
            if ($LASTEXITCODE -ne 0) { throw 'Stage worker stopped. Preserve outputs and inspect before explicit recovery.' }
        }
        'RepositoryFirstAttemptExecute' {
            if (-not $ConfirmPaidRun -or -not $env:MFEC_LITELLM_API_KEY) {
                throw 'Provide the key only in the process environment and add -ConfirmPaidRun.'
            }
            if (-not (Test-Path -LiteralPath "$major/repository_first_attempt_v1_lock.json")) {
                throw 'Freeze/review the common first-attempt contract and all six identity checks before paid calls.'
            }
            $taskFrozenRepairs = Get-Content -LiteralPath "$major/repository_first_attempt_v1_lock.json" -Raw | ConvertFrom-Json
            if ($CaseId -notin @($taskFrozenRepairs.cases.case_id) -or $ModelSlot -notin @($taskFrozenRepairs.settings.model_slots)) {
                throw 'Case or model slot is outside the frozen eighteen-pair design.'
            }
            if (Test-Path -LiteralPath "$major/candidate_workspaces/repository_first_attempt_v1/${CaseId}_${ModelSlot}") {
                throw 'This first-attempt pair has started or completed; never retry it silently.'
            }
            $taskLinuxRoot = (& wsl -d Ubuntu -e wslpath -a $v2Root).Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Ubuntu WSL is unavailable' }
            $env:MFEC_LITELLM_API_KEY | & wsl -d Ubuntu -u root -e python3 `
                "$taskLinuxRoot/$major/wsl_repository_first_attempt_bridge_v1.py" run_repository_first_attempt_v1.py `
                --case-id $CaseId --slot $ModelSlot
            if ($LASTEXITCODE -ne 0) { throw 'First-attempt call stopped; inspect all saved evidence without issuing a duplicate request.' }
        }
        'BugsCalibrationPreflightStatus' {
            Invoke-Python @("$major/audit_bugsinpy_calibration_preflight_v1.py")
        }
        'BugsCalibrationPreflightExecute' {
            if (-not (Test-Path -LiteralPath "$major/results/bugsinpy_calibration_preflight_v1/lock.json")) {
                throw 'Freeze and review the new candidate pool before execution.'
            }
            if (Test-Path -LiteralPath "$major/results/bugsinpy_calibration_preflight_v1/summary.json") {
                throw 'New-case preflight is complete; audit instead of rerunning.'
            }
            if (Test-Path -LiteralPath "$major/results/bugsinpy_calibration_preflight_v1/ledger.jsonl") {
                throw 'Preflight has already started; inspect its active worker and preserved artifacts before explicit recovery. Refusing a duplicate batch.'
            }
            $taskLinuxRoot = (& wsl -d Ubuntu -e wslpath -a $v2Root).Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Ubuntu WSL is unavailable' }
            & wsl -d Ubuntu -u root -e env CONVEYORFLOW_CONTAINER_COMMAND=podman python3 `
                "$taskLinuxRoot/$major/run_bugsinpy_calibration_preflight_v1.py" --execute
            if ($LASTEXITCODE -ne 0) { throw 'New-case preflight stopped; preserve artifacts and investigate before recovery.' }
        }
        'RepositoryPilotExecute' {
            if (-not $ConfirmPaidRun -or -not $env:MFEC_LITELLM_API_KEY) {
                throw 'Provide the key only in the process environment and add -ConfirmPaidRun.'
            }
            $taskIdentity = Get-Content -LiteralPath "$major/candidate_workspaces/repository_identity_smoke_v1/audit.json" -Raw | ConvertFrom-Json
            if ($taskIdentity.status -ne 'identity_smoke_passed') {
                throw 'All six identity smoke checks must pass before a repair call.'
            }
            if (Test-Path -LiteralPath "$major/candidate_workspaces/repository_repair_pilot_v1/${CaseId}_${ModelSlot}") {
                throw 'This frozen repository job already exists; audit it instead of rerunning.'
            }
            $taskLinuxRoot = (& wsl -d Ubuntu -e wslpath -a $v2Root).Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Ubuntu WSL is unavailable' }
            $env:MFEC_LITELLM_API_KEY | & wsl -d Ubuntu -u root -e python3 `
                "$taskLinuxRoot/$major/wsl_repair_provider_bridge_v1.py" run_repository_repair_pilot_v1.py `
                --case-id $CaseId --model-slot $ModelSlot
            if ($LASTEXITCODE -ne 0) { throw 'Repository pilot stopped; inspect all evidence before recovery.' }
        }
        'RepositoryDecoderReplay' {
            if (Test-Path -LiteralPath "$major/candidate_workspaces/repository_decoder_replay_v2") {
                throw 'Offline diagnostic replay already started or completed; refusing to overwrite it.'
            }
            $taskLinuxRoot = (& wsl -d Ubuntu -e wslpath -a $v2Root).Trim()
            if ($LASTEXITCODE -ne 0) { throw 'Ubuntu WSL is unavailable' }
            & wsl -d Ubuntu -u root -e python3 "$taskLinuxRoot/$major/run_repository_decoder_replay_v2_linux.py" --freeze
            if ($LASTEXITCODE -ne 0) { throw 'Decoder diagnostic freeze failed' }
            & wsl -d Ubuntu -u root -e python3 "$taskLinuxRoot/$major/run_repository_decoder_replay_v2_linux.py" --execute
            if ($LASTEXITCODE -ne 0) { throw 'Decoder replay stopped; preserve partial artifacts and investigate.' }
        }
        'CalibrationSummary' {
            if (-not $CalibrationManifest -or -not $CalibrationLedger) {
                throw 'Provide -CalibrationManifest and -CalibrationLedger from a frozen held-out ecological calibration.'
            }
            Invoke-Python @("$major/summarize_ecological_calibration.py", '--manifest',
                            $CalibrationManifest, '--ledger', $CalibrationLedger)
        }
        'OverheadVerify' {
            Invoke-Python @("$major/verify_overhead_proxy_v1.py")
        }
        'OverheadRun' {
            if (Test-Path -LiteralPath "$major/results/overhead_proxy_v1/main") {
                throw 'Frozen overhead proxy main results already exist; refusing to overwrite. Verify them with -Stage OverheadVerify.'
            }
            Invoke-Python @("$major/measure_overhead_proxy_v1.py")
        }
        'OverheadLoadVerify' {
            Invoke-Python @("$major/verify_overhead_load_v1.py")
        }
        'OverheadLoadRun' {
            if (Test-Path -LiteralPath "$major/results/overhead_load_v1/main") {
                throw 'Frozen load proxy main results already exist; refusing to overwrite. Verify them with -Stage OverheadLoadVerify.'
            }
            Invoke-Python @("$major/measure_overhead_load_v1.py")
        }
    }
} finally {
    Pop-Location
}
