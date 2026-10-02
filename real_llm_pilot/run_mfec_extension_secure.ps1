param(
    [switch]$Execute,
    [ValidateSet("ALL", "HET_NO_STANDDOWN", "HOM_GLM_GENERALIST", "HOM_GPT_PROFILE")]
    [string]$Condition = "ALL"
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "ConveyorFlow Extension Resume"
$pilotRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "C:\Users\Sakan P\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$shortDrive = $null
$shortRoot = $null
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
$preflightRoot = Join-Path $shortRoot "preflight_extension"
$outputRoot = Join-Path $shortRoot "extension_mfec_output"
$conditionConfigs = [ordered]@{
    "HET_NO_STANDDOWN" = "config.extension.no_standdown.json"
    "HOM_GLM_GENERALIST" = "config.extension.h_glm.json"
    "HOM_GPT_PROFILE" = "config.extension.h_gpt.json"
}

$executionStateSource = @"
using System;
using System.Runtime.InteropServices;
public static class ConveyorFlowExtensionExecutionState {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@
Add-Type -TypeDefinition $executionStateSource -ErrorAction SilentlyContinue
[ConveyorFlowExtensionExecutionState]::SetThreadExecutionState([uint32]2147483649) | Out-Null
$secureKey = Read-Host "MFEC LiteLLM API key" -AsSecureString
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $env:MFEC_LITELLM_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr)
    $selected = if ($Condition -eq "ALL") { @($conditionConfigs.Keys) } else { @($Condition) }
    foreach ($conditionId in $selected) {
        $config = Join-Path $shortRoot $conditionConfigs[$conditionId]
        $preflight = Join-Path $preflightRoot $conditionId
        & $python (Join-Path $shortRoot "run_extension.py") --dry-run --config $config --cases $cases --output $preflight
        if ($LASTEXITCODE -ne 0) { throw "Preflight failed for $conditionId" }
        $manifest = Get-Content -LiteralPath (Join-Path $preflight "dry_run_manifest.json") -Raw | ConvertFrom-Json
        if ($manifest.status -ne "ready_not_executed") { throw "Extension remains blocked for $conditionId" }
    }

    if (-not $Execute) {
        Write-Host "All selected extension preflights passed. Re-run with -Execute to start billable calls."
        return
    }

    foreach ($conditionId in $selected) {
        $config = Join-Path $shortRoot $conditionConfigs[$conditionId]
        $conditionOutput = Join-Path $outputRoot $conditionId
        Write-Host "Starting $conditionId (10 frozen seeds)..."
        & $python (Join-Path $shortRoot "run_extension.py") --config $config --cases $cases --output $conditionOutput --adapter $adapter
        if ($LASTEXITCODE -ne 0) { throw "Real-LLM execution failed for $conditionId" }
        Write-Host "Completed $conditionId"
    }
}
finally {
    $env:MFEC_LITELLM_API_KEY = $null
    [ConveyorFlowExtensionExecutionState]::SetThreadExecutionState([uint32]2147483648) | Out-Null
    if ($keyPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr)
    }
    if ($null -ne $shortDrive) {
        & subst.exe $shortDrive /D | Out-Null
    }
}
