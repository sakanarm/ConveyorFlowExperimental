param(
    [string]$Config = "v2/real_llm_pilot/config.mfec_candidate.json",
    [string]$Probes = "v2/real_llm_pilot/calibration_probes.jsonl"
)

$ErrorActionPreference = "Stop"
$secureKey = Read-Host "MFEC LiteLLM API key (input is hidden)" -AsSecureString
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr)
    $env:MFEC_LITELLM_API_KEY = $plainKey
    python v2/real_llm_pilot/run_mfec_calibration.py --config $Config --probes $Probes
    if ($LASTEXITCODE -ne 0) {
        throw "Calibration runner failed with exit code $LASTEXITCODE"
    }
}
finally {
    Remove-Item Env:MFEC_LITELLM_API_KEY -ErrorAction SilentlyContinue
    if ($keyPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr)
    }
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable secureKey -ErrorAction SilentlyContinue
}
