param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$v2 = Split-Path -Parent $PSScriptRoot
$current = Join-Path $v2 'CURRENT_MANUSCRIPTS'
if (-not (Test-Path -LiteralPath $current -PathType Container)) { throw 'CURRENT_MANUSCRIPTS missing' }

function Copy-Verified {
    param([string]$Source, [string]$Destination)
    $sourcePath = Join-Path $v2 $Source
    $destinationPath = Join-Path $current $Destination
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "Missing source: $Source" }
    $parent = Split-Path -Parent $destinationPath
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    $sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    if (Test-Path -LiteralPath $destinationPath) {
        $destinationHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash
        if ($destinationHash -ne $sourceHash) { throw "Conflicting destination; no overwrite: $Destination" }
        return [pscustomobject]@{source=$Source;destination=$Destination;sha256=$sourceHash;status='already_identical'}
    }
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -ErrorAction Stop
    $destinationHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash
    if ($destinationHash -ne $sourceHash) { throw "Copy verification failed: $Destination" }
    return [pscustomobject]@{source=$Source;destination=$Destination;sha256=$sourceHash;status='copied'}
}

$report = @()
$bounded = 'major_revision_v2_6/manuscripts_bounded_v2_6'
foreach ($name in @(
    'ConveyorFlow_IEEE_Manuscript_Bounded_v2_6.docx',
    'ConveyorFlow_AJSTR_Blinded_Bounded_v2_6.docx',
    'ConveyorFlow_AJSTR_Unblinded_Bounded_v2_6.docx')) {
    $report += Copy-Verified "$bounded/$name" $name
}
$report += Copy-Verified 'AJSTR Journal/ConveyorFlow_AJSTR_Blinded_Manuscript.docx' 'ARCHIVE_FROM_OTHER_LOCATIONS/AJSTR_Journal_source/ConveyorFlow_AJSTR_Blinded_Manuscript.docx'
$report += Copy-Verified 'Back up/ConveyorFlow_IEEE_Manuscript.docx' 'ARCHIVE_FROM_OTHER_LOCATIONS/Back_up/ConveyorFlow_IEEE_Manuscript.docx'
foreach ($file in (Get-ChildItem -LiteralPath (Join-Path $v2 'AJSTR Journal/v2_3_word_work') -File -Filter '*.docx' | Sort-Object Name)) {
    $report += Copy-Verified "AJSTR Journal/v2_3_word_work/$($file.Name)" "ARCHIVE_FROM_OTHER_LOCATIONS/v2_3_word_work/$($file.Name)"
}

$report += Copy-Verified 'ConveyorFlow_diagrams_en_working.drawio' 'DIAGRAMS/ConveyorFlow_diagrams_en_working.drawio'
$diagramDirs = @(
    @('AJSTR Journal', 'v2_0'),
    @('AJSTR Journal/figures_v2_1', 'v2_1'),
    @('AJSTR Journal/figures_v2_2', 'v2_2')
)
foreach ($pair in $diagramDirs) {
    $folder = $pair[0]
    $label = $pair[1]
    foreach ($file in (Get-ChildItem -LiteralPath (Join-Path $v2 $folder) -File -Filter '*.drawio' | Sort-Object Name)) {
        $report += Copy-Verified "$folder/$($file.Name)" "DIAGRAMS/$label/$($file.Name)"
    }
}
foreach ($file in (Get-ChildItem -LiteralPath (Join-Path $v2 'AJSTR Journal/figures_v2_2/legacy_style_corrected') -File -Filter 'Figure_*.png' | Sort-Object Name)) {
    $report += Copy-Verified "AJSTR Journal/figures_v2_2/legacy_style_corrected/$($file.Name)" "DIAGRAMS/v2_2/corrected_exports/$($file.Name)"
}
$report | ConvertTo-Json -Depth 4
