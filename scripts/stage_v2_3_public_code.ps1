param([switch]$StageFiles)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$taskRepo = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
Push-Location -LiteralPath $taskRepo
try {
    $taskPaths = @('.gitattributes','.gitignore','pytest.ini','REPRODUCE_V2_3.ps1','REPRODUCIBILITY_V2_3.md',
                   'ConveyorFlow_diagrams_en_working.drawio','scripts/stage_v2_3_public_code.ps1',
                   'scripts/build_ieee_v2_3_progress_with_word.ps1',
                   'scripts/repair_ieee_v2_3_caption_with_word.ps1',
                   'scripts/render_native_word_document.ps1')
    foreach ($taskFolder in @('major_revision_v2_3','major_revision_v2_3/ecological_v1')) {
        $taskPaths += @(Get-ChildItem -LiteralPath $taskFolder -File | Where-Object {
            $_.Extension -in @('.py','.md','.json') -or $_.Name.StartsWith('Dockerfile.')
        } | ForEach-Object { $taskFolder + '/' + $_.Name })
    }
    foreach ($taskFolder in @('major_revision_v2_3/ecological_v1/prepared_design',
                              'major_revision_v2_3/smoke_dag_candidate',
                              'major_revision_v2_3/smoke_candidate','tests')) {
        $taskPaths += @(Get-ChildItem -LiteralPath $taskFolder -File | Where-Object {
            $_.Extension -in @('.py','.json')
        } | ForEach-Object { $taskFolder + '/' + $_.Name })
    }
    $taskPaths += @('major_revision_v2_3/ml_cases/case_manifest.json',
                    'major_revision_v2_3/ml_cases/quality_gates.json',
                    'major_revision_v2_3/requirements_ml_eval.lock.txt')
    # Four completed aggregate files only; never stage raw paid evidence.
    $taskAggregate='public_results/v2_3/ecological_repository_calibration_v1'
    if(Test-Path -LiteralPath $taskAggregate){
        foreach($taskName in @('audit.json','summary.json','evidence_manifest.json','RESULTS.md')){
            $taskPaths += $taskAggregate+'/'+$taskName
        }
    }
    $taskPaths = @($taskPaths | Sort-Object -Unique)
    $taskSuspicious = @()
    foreach ($taskPath in $taskPaths) {
        $taskText = [System.IO.File]::ReadAllText((Join-Path $taskRepo $taskPath))
        $taskHasKey = $env:MFEC_LITELLM_API_KEY -and $taskText.Contains($env:MFEC_LITELLM_API_KEY)
        # Boundary prevents the harmless suffix in "task-specification" matching "sk-".
        if ($taskHasKey -or $taskText -match '(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----') {
            $taskSuspicious += $taskPath
        }
    }
    if ($taskSuspicious.Count) {
        $taskSuspicious
        throw 'Credential-like content found. Values were not printed; no files staged.'
    }
    $taskBytes = ($taskPaths | ForEach-Object { (Get-Item -LiteralPath $_).Length } | Measure-Object -Sum).Sum
    Write-Output "Selected files: $($taskPaths.Count); bytes: $taskBytes; credential scan: clean"
    if ($StageFiles) {
        # Explicit files only. Never git-add the candidate/data/result directory.
        & git -c core.longpaths=true -c core.safecrlf=false add -- @taskPaths
        if ($LASTEXITCODE -ne 0) { throw 'Scoped staging failed' }
        & git diff --cached --shortstat
    }
} finally { Pop-Location }
