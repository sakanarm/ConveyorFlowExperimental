param(
    [string]$BaseUrl = "https://gpt.mfec.co.th/litellm",
    [string]$OutputPath = "v2/real_llm_pilot/mfec_model_catalog.json"
)

$ErrorActionPreference = "Stop"
$secureKey = Read-Host "MFEC LiteLLM API key (input is hidden)" -AsSecureString
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr)
    $headers = @{ Authorization = "Bearer $plainKey" }
    $candidateUrls = @(
        "$($BaseUrl.TrimEnd('/'))/v1/models",
        "$($BaseUrl.TrimEnd('/'))/models"
    )

    $response = $null
    $usedUrl = $null
    foreach ($url in $candidateUrls) {
        try {
            $response = Invoke-RestMethod -Method Get -Uri $url -Headers $headers
            $usedUrl = $url
            break
        }
        catch {
            if ($url -eq $candidateUrls[-1]) { throw }
        }
    }

    $models = @($response.data)
    if ($models.Count -eq 0 -and $response.models) {
        $models = @($response.models)
    }
    if ($models.Count -eq 0) {
        throw "The endpoint responded successfully but no model records were found."
    }

    $sanitized = [ordered]@{
        retrieved_at_utc = [DateTime]::UtcNow.ToString("o")
        endpoint = $usedUrl
        model_count = $models.Count
        models = @(
            $models | ForEach-Object {
                [ordered]@{
                    id = $_.id
                    owned_by = $_.owned_by
                    created = $_.created
                }
            } | Sort-Object id
        )
    }

    $resolvedOutput = [IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath))
    $outputDir = Split-Path -Parent $resolvedOutput
    if (-not (Test-Path -LiteralPath $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir | Out-Null
    }
    $sanitized | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $resolvedOutput -Encoding UTF8

    Write-Host "Saved sanitized model catalog to: $resolvedOutput"
    Write-Host "Models found: $($models.Count)"
}
finally {
    if ($keyPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr)
    }
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable secureKey -ErrorAction SilentlyContinue
}
