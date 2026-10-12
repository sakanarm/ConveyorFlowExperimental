param(
    [ValidateSet('AuditSource','AuditCandidate','Freeze','RunNext','RunRemaining','AuditLive','SealLive','VerifyAnalysis')]
    [string]$Mode = 'AuditCandidate'
)

$ErrorActionPreference = 'Stop'
$v2Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $v2Root

if ($Mode -eq 'AuditSource') {
    & wsl -d Ubuntu -u root --cd $v2Root -- env CONVEYORFLOW_CONTAINER_COMMAND=podman python3 major_revision_v2_6/audit_scrapy_public_preflight_v1b.py
    exit $LASTEXITCODE
}
if ($Mode -eq 'AuditCandidate') {
    & wsl -d Ubuntu -u root --cd $v2Root -- env CONVEYORFLOW_CONTAINER_COMMAND=podman python3 major_revision_v2_7/prepare_scrapy_pair_v1.py --audit
    exit $LASTEXITCODE
}
if ($Mode -eq 'Freeze') {
    & wsl -d Ubuntu -u root --cd $v2Root -- env CONVEYORFLOW_CONTAINER_COMMAND=podman python3 major_revision_v2_7/run_scrapy_live_pair_v1.py --freeze
    exit $LASTEXITCODE
}
if ($Mode -eq 'AuditLive') {
    & wsl -d Ubuntu -u root --cd $v2Root -- python3 major_revision_v2_7/audit_scrapy_live_pair_v1.py
    exit $LASTEXITCODE
}
if ($Mode -eq 'SealLive') {
    & wsl -d Ubuntu -u root --cd $v2Root -- python3 major_revision_v2_7/audit_scrapy_live_pair_v1.py --seal
    exit $LASTEXITCODE
}
if ($Mode -eq 'VerifyAnalysis') {
    & wsl -d Ubuntu -u root --cd $v2Root -- python3 major_revision_v2_7/analyze_scrapy_live_pair_v1.py --verify
    exit $LASTEXITCODE
}

if (-not $env:MFEC_LITELLM_API_KEY) {
    throw 'Set MFEC_LITELLM_API_KEY in the process environment; never write it to this script or Git.'
}
$priorWslenv = $env:WSLENV
$env:WSLENV = 'MFEC_LITELLM_API_KEY/u'
try {
    $count = if ($Mode -eq 'RunRemaining') { 6 } else { 1 }
    for ($i = 0; $i -lt $count; $i++) {
        & wsl -d Ubuntu -u root --cd $v2Root -- env CONVEYORFLOW_CONTAINER_COMMAND=podman python3 major_revision_v2_7/run_scrapy_live_pair_v1.py --run-next --confirm-paid-v27-bounded
        if ($LASTEXITCODE -ne 0) {
            throw "v2.7 runner stopped with exit code $LASTEXITCODE. Inspect existing request markers; do not blindly retry."
        }
    }
} finally {
    $env:WSLENV = $priorWslenv
}
