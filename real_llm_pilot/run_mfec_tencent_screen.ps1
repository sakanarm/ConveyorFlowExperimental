$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "ENTER MFEC KEY - Final Tencent L1 screen"
$secureKey = Read-Host "MFEC LiteLLM API key (input is hidden)" -AsSecureString
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr)
    $env:MFEC_LITELLM_API_KEY = $plainKey
    python v2/real_llm_pilot/run_mfec_heterogeneity_screen.py --config v2/real_llm_pilot/config.mfec_tencent_screen.json --output-root v2/real_llm_pilot/tencent_screen_output
    if ($LASTEXITCODE -ne 0) { throw "Tencent screen failed with exit code $LASTEXITCODE" }
}
finally {
    Remove-Item Env:MFEC_LITELLM_API_KEY -ErrorAction SilentlyContinue
    if ($keyPtr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr) }
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable secureKey -ErrorAction SilentlyContinue
}
