param(
    [switch]$Execute
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "ConveyorFlow Extension Resume (GLM 3004 + GPT)"
$pilotRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\Sakan P\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$shortDrive = $null
$driveCandidates = @("T:", "U:", "V:", "W:", "X:", "Y:", "Z:")
foreach ($candidate in $driveCandidates) {
    if (-not (Test-Path -LiteralPath $candidate)) {
        $shortDrive = $candidate
        break
    }
}
if ($null -eq $shortDrive) { throw "No free temporary drive letter is available" }

& subst.exe $shortDrive $pilotRoot
if ($LASTEXITCODE -ne 0) { throw "Unable to create short validator path with subst" }
$shortRoot = "$shortDrive\"
$cases = Join-Path $shortRoot "case_manifest.csv"
$adapter = Join-Path $shortRoot "mfec_adapter.py"
$preflightRoot = Join-Path $shortRoot "preflight_extension_resume"
$outputRoot = Join-Path $shortRoot "extension_mfec_output"
$resumePlan = @(
    [pscustomobject]@{
        ConditionId = "HOM_GLM_GENERALIST"
        Config = "config.extension.h_glm.json"
        SeedFrom = 3004
    },
    [pscustomobject]@{
        ConditionId = "HOM_GPT_PROFILE"
        Config = "config.extension.h_gpt.json"
        SeedFrom = $null
    }
)

$executionStateSource = @"
using System;
using System.Runtime.InteropServices;
public static class ConveyorFlowResumeExecutionState {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@
Add-Type -TypeDefinition $executionStateSource -ErrorAction SilentlyContinue
[ConveyorFlowResumeExecutionState]::SetThreadExecutionState([uint32]2147483649) | Out-Null
$secureKey = Read-Host "MFEC LiteLLM API key" -AsSecureString
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $env:MFEC_LITELLM_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr)

    foreach ($item in $resumePlan) {
        $config = Join-Path $shortRoot $item.Config
        $preflight = Join-Path $preflightRoot $item.ConditionId
        & $python (Join-Path $shortRoot "run_extension.py") --dry-run --config $config --cases $cases --output $preflight
        if ($LASTEXITCODE -ne 0) { throw "Preflight failed for $($item.ConditionId)" }
        $manifest = Get-Content -LiteralPath (Join-Path $preflight "dry_run_manifest.json") -Raw | ConvertFrom-Json
        if ($manifest.status -ne "ready_not_executed") { throw "Extension remains blocked for $($item.ConditionId)" }
    }

    if (-not $Execute) {
        Write-Host "Resume preflights passed. Re-run with -Execute to start billable calls."
        return
    }

    foreach ($item in $resumePlan) {
        $config = Join-Path $shortRoot $item.Config
        $conditionOutput = Join-Path $outputRoot $item.ConditionId
        $arguments = @(
            (Join-Path $shortRoot "run_extension.py"),
            "--config", $config,
            "--cases", $cases,
            "--output", $conditionOutput,
            "--adapter", $adapter
        )
        if ($null -ne $item.SeedFrom) {
            $arguments += @("--seed-from", [string]$item.SeedFrom)
            Write-Host "Resuming $($item.ConditionId) from frozen seed $($item.SeedFrom)..."
        } else {
            Write-Host "Starting $($item.ConditionId) for all 10 frozen seeds..."
        }
        & $python @arguments
        if ($LASTEXITCODE -ne 0) { throw "Real-LLM execution failed for $($item.ConditionId)" }
        Write-Host "Completed $($item.ConditionId)"
    }
}
finally {
    $env:MFEC_LITELLM_API_KEY = $null
    [ConveyorFlowResumeExecutionState]::SetThreadExecutionState([uint32]2147483648) | Out-Null
    if ($keyPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr)
    }
    if ($null -ne $shortDrive) {
        & subst.exe $shortDrive /D | Out-Null
    }
}

