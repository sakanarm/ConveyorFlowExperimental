param(
    [switch]$Execute,
    [switch]$Calibrate,
    [int]$OnlySeed = -1,
    [int]$SeedFrom = -1,
    [ValidateSet("CF_FIT", "S3", "CENTRAL_FIT")]
    [string[]]$OnlyPolicy = @()
)

$ErrorActionPreference = "Stop"
$pilotRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\Sakan P\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$executionStateSource = @"
using System;
using System.Runtime.InteropServices;
public static class ConveyorFlowExecutionState {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@
Add-Type -TypeDefinition $executionStateSource -ErrorAction SilentlyContinue
[ConveyorFlowExecutionState]::SetThreadExecutionState([uint32]2147483649) | Out-Null
$secureKey = Read-Host "MFEC LiteLLM API key" -AsSecureString
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $env:MFEC_LITELLM_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr)
    & $python (Join-Path $pilotRoot "probe_mfec_metadata.py")
    if ($LASTEXITCODE -ne 0) { throw "MFEC metadata probe failed" }

    & $python (Join-Path $pilotRoot "freeze_mfec_main_config.py")
    if ($LASTEXITCODE -ne 0 -and ($Calibrate -or $Execute)) {
        & $python (Join-Path $pilotRoot "calibrate_mfec_headers.py")
        if ($LASTEXITCODE -ne 0) { throw "MFEC calibration did not expose stable deployment/cost headers" }
        & $python (Join-Path $pilotRoot "freeze_mfec_main_config.py")
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Metadata is incomplete; re-run with -Calibrate or request immutable mappings/prices from MFEC"
    }

    $config = Join-Path $pilotRoot "config.mfec_main_frozen.json"
    $cases = Join-Path $pilotRoot "case_manifest.csv"
    $preflight = Join-Path $pilotRoot "preflight_mfec_main"
    & $python (Join-Path $pilotRoot "run_pilot.py") --dry-run --config $config --cases $cases --output $preflight
    if ($LASTEXITCODE -ne 0) { throw "Main preflight failed" }

    $manifest = Get-Content -LiteralPath (Join-Path $preflight "dry_run_manifest.json") -Raw | ConvertFrom-Json
    if ($manifest.status -ne "ready_not_executed") {
        throw "Main execution remains blocked; inspect preflight_mfec_main/dry_run_manifest.json"
    }

    if ($Execute) {
        $output = Join-Path $pilotRoot "main_mfec_output"
        $runArgs = @(
            (Join-Path $pilotRoot "run_pilot.py"),
            "--config", $config,
            "--cases", $cases,
            "--output", $output,
            "--adapter", (Join-Path $pilotRoot "mfec_adapter.py")
        )
        if ($OnlySeed -ge 0) {
            $runArgs += @("--only-seed", $OnlySeed)
        }
        if ($SeedFrom -ge 0) {
            $runArgs += @("--seed-from", $SeedFrom)
        }
        foreach ($policy in $OnlyPolicy) {
            $runArgs += @("--only-policy", $policy)
        }
        & $python @runArgs
        if ($LASTEXITCODE -ne 0) { throw "Main Real-LLM execution failed" }
    }
    else {
        Write-Host "Preflight passed. Re-run with -Execute to start billable Main Real-LLM calls."
    }
}
finally {
    $env:MFEC_LITELLM_API_KEY = $null
    [ConveyorFlowExecutionState]::SetThreadExecutionState([uint32]2147483648) | Out-Null
    if ($keyPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr)
    }
}
