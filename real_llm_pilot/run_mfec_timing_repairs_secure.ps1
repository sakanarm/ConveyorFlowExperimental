$ErrorActionPreference = "Stop"
$pilotRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\Sakan P\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$executionStateSource = @"
using System;
using System.Runtime.InteropServices;
public static class ConveyorFlowRepairExecutionState {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@
Add-Type -TypeDefinition $executionStateSource -ErrorAction SilentlyContinue
[ConveyorFlowRepairExecutionState]::SetThreadExecutionState([uint32]2147483649) | Out-Null
$secureKey = Read-Host "MFEC LiteLLM API key" -AsSecureString
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $env:MFEC_LITELLM_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr)
    $config = Join-Path $pilotRoot "config.mfec_main_frozen.json"
    $cases = Join-Path $pilotRoot "case_manifest.csv"
    $output = Join-Path $pilotRoot "main_mfec_output"
    $adapter = Join-Path $pilotRoot "mfec_adapter.py"
    $preflight = Join-Path $pilotRoot "preflight_mfec_timing_repairs"

    & $python (Join-Path $pilotRoot "run_pilot.py") --dry-run --config $config --cases $cases --output $preflight
    if ($LASTEXITCODE -ne 0) { throw "Timing-repair preflight failed" }
    $manifest = Get-Content -LiteralPath (Join-Path $preflight "dry_run_manifest.json") -Raw | ConvertFrom-Json
    if ($manifest.status -ne "ready_not_executed") { throw "Timing-repair preflight remains blocked" }

    $repairs = @(
        @{ Seed = 3001; Policy = "CENTRAL_FIT" },
        @{ Seed = 3006; Policy = "S3" },
        @{ Seed = 3009; Policy = "CF_FIT" }
    )
    foreach ($repair in $repairs) {
        Write-Host "Repairing timing: $($repair.Policy) seed $($repair.Seed)"
        & $python (Join-Path $pilotRoot "run_pilot.py") --config $config --cases $cases --output $output --adapter $adapter --only-seed $repair.Seed --only-policy $repair.Policy
        if ($LASTEXITCODE -ne 0) { throw "Timing repair failed: $($repair.Policy) seed $($repair.Seed)" }
    }
}
finally {
    $env:MFEC_LITELLM_API_KEY = $null
    [ConveyorFlowRepairExecutionState]::SetThreadExecutionState([uint32]2147483648) | Out-Null
    if ($keyPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr)
    }
}
