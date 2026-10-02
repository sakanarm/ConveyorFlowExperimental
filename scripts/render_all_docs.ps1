param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot
)

$root = [System.IO.Path]::GetFullPath($WorkspaceRoot)
$qaDirectory = Join-Path $root 'v2\.docx_qa'
if (-not (Test-Path -LiteralPath $qaDirectory)) {
    New-Item -ItemType Directory -Path $qaDirectory | Out-Null
}

$renderer = Join-Path $root 'v2\scripts\render_with_word.ps1'
& $renderer `
    -InputDocx (Join-Path $root 'v2\ConveyorFlow_IEEE_Manuscript.docx') `
    -OutputPdf (Join-Path $qaDirectory 'ConveyorFlow_IEEE_Manuscript.pdf')
& $renderer `
    -InputDocx (Join-Path $root 'v2\ConveyorFlow_Advisor_Explanation_TH.docx') `
    -OutputPdf (Join-Path $qaDirectory 'ConveyorFlow_Advisor_Explanation_TH.pdf')
