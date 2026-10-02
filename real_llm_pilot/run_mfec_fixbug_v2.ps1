$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "ENTER MFEC KEY - ConveyorFlow FixBug v2"
$secureKey = Read-Host "MFEC LiteLLM API key (input is hidden)" -AsSecureString
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr)
    $env:MFEC_LITELLM_API_KEY = $plainKey
    python v2/real_llm_pilot/run_mfec_fixbug_v2.py
    if ($LASTEXITCODE -ne 0) { throw "Fix Bug calibration v2 failed with exit code $LASTEXITCODE" }
}
finally {
    Remove-Item Env:MFEC_LITELLM_API_KEY -ErrorAction SilentlyContinue
    if ($keyPtr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr) }
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable secureKey -ErrorAction SilentlyContinue
}
