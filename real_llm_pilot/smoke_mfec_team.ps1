param(
    [string]$BaseUrl = "https://gpt.mfec.co.th/litellm",
    [string]$OutputPath = "v2/real_llm_pilot/mfec_smoke_results.json"
)

$ErrorActionPreference = "Stop"
$models = @("gemini-3-flash", "gemini-3.5-flash", "gemini-3.8-flash")
$secureKey = Read-Host "MFEC LiteLLM API key (input is hidden)" -AsSecureString
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr)
    $headers = @{
        Authorization = "Bearer $plainKey"
        "Content-Type" = "application/json"
    }
    $url = "$($BaseUrl.TrimEnd('/'))/v1/chat/completions"
    $results = @()

    foreach ($model in $models) {
        $body = @{
            model = $model
            messages = @(@{
                role = "user"
                content = "Infrastructure smoke test. Reply with exactly: OK"
            })
            temperature = 0
            max_tokens = 8
        } | ConvertTo-Json -Depth 6

        $timer = [Diagnostics.Stopwatch]::StartNew()
        try {
            $response = Invoke-RestMethod -Method Post -Uri $url -Headers $headers -Body $body
            $timer.Stop()
            $reply = [string]$response.choices[0].message.content
            $results += [ordered]@{
                requested_model = $model
                status = "success"
                returned_model = $response.model
                latency_ms = $timer.ElapsedMilliseconds
                prompt_tokens = $response.usage.prompt_tokens
                completion_tokens = $response.usage.completion_tokens
                total_tokens = $response.usage.total_tokens
                exact_ok = ($reply.Trim() -eq "OK")
                error_type = $null
            }
        }
        catch {
            $timer.Stop()
            $results += [ordered]@{
                requested_model = $model
                status = "error"
                returned_model = $null
                latency_ms = $timer.ElapsedMilliseconds
                prompt_tokens = $null
                completion_tokens = $null
                total_tokens = $null
                exact_ok = $false
                error_type = $_.Exception.GetType().Name
            }
        }
    }

    $sanitized = [ordered]@{
        test_type = "infrastructure_smoke_not_research_result"
        retrieved_at_utc = [DateTime]::UtcNow.ToString("o")
        endpoint = $url
        generation = [ordered]@{ temperature = 0; max_tokens = 8 }
        results = $results
    }

    $resolvedOutput = [IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath))
    $sanitized | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resolvedOutput -Encoding UTF8
    Write-Host "Saved sanitized smoke results to: $resolvedOutput"
}
finally {
    if ($keyPtr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr)
    }
    Remove-Variable plainKey -ErrorAction SilentlyContinue
    Remove-Variable secureKey -ErrorAction SilentlyContinue
}
