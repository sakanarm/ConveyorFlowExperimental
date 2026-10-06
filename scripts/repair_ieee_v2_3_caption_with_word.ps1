# Minimal native Word layout repair of a completed progress copy.
param([string]$OutputName='ConveyorFlow_IEEE_Manuscript_v2_3_Progress_Rev7.docx')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$taskV2=Split-Path -Parent $PSScriptRoot
$taskCurrent=Join-Path $taskV2 'CURRENT_MANUSCRIPTS'
$taskSource=Join-Path $taskCurrent 'ConveyorFlow_IEEE_Manuscript_v2_3_Progress_Rev6.docx'
if([IO.Path]::GetFileName($OutputName) -ne $OutputName -or -not $OutputName.EndsWith('.docx')){throw 'New DOCX filename required'}
$taskOutput=Join-Path $taskCurrent $OutputName
if(Test-Path -LiteralPath $taskOutput){throw 'Existing output; refusing overwrite'}
$taskSourceHash=(Get-FileHash -LiteralPath $taskSource).Hash
$taskTemp=Join-Path ([IO.Path]::GetTempPath()) ('cf_ieee_repair_'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskTemp | Out-Null
$taskCopy=Join-Path $taskTemp 'progress.docx'
Copy-Item -LiteralPath $taskSource -Destination $taskCopy
$taskWord=$null;$taskDoc=$null
function Find-ExactParagraph([string]$Prefix){
    $taskRange=$taskDoc.Content.Duplicate
    $taskRange.Find.ClearFormatting();$taskRange.Find.Text=$Prefix;$taskRange.Find.Wrap=0
    $taskRange.Find.MatchWildcards=$false
    if(-not $taskRange.Find.Execute()){throw "Missing text: $Prefix"}
    $taskParagraph=$taskRange.Paragraphs.Item(1).Range.Duplicate
    if(-not $taskParagraph.Text.StartsWith($Prefix)){throw "Prefix is not a paragraph start: $Prefix"}
    return $taskParagraph
}
try{
    Write-Output 'Creating private Microsoft Word helper'
    $taskWord=New-Object -ComObject Word.Application
    $taskWord.Visible=$false;$taskWord.DisplayAlerts=0;$taskWord.AutomationSecurity=3
    $taskWord.ScreenUpdating=$false;$taskWord.Options.AllowReadingMode=$false
    Write-Output 'Opening temporary progress copy'
    $taskDoc=$taskWord.Documents.Open($taskCopy,$false,$false)
    Write-Output 'Temporary copy opened'
    if($taskDoc.ReadOnly -or $taskDoc.InlineShapes.Count -ne 15 -or $taskDoc.OMaths.Count -ne 13 -or $taskDoc.Tables.Count -ne 11){throw 'Unexpected source structure'}
    $taskCaption=Find-ExactParagraph 'Fig. 9.'
    $taskPicture=$null
    foreach($taskShape in $taskDoc.InlineShapes){
        if($taskShape.Range.End -le $taskCaption.Start){$taskPicture=$taskShape}else{break}
    }
    if($null -eq $taskPicture -or $taskCaption.Start-$taskPicture.Range.End -gt 8){throw 'Figure/caption adjacency mismatch'}
    Write-Output 'Repairing Figure 9 isolated section'
    $taskPicture.Range.Sections.Item(1).PageSetup.TextColumns.SetCount(1)
    $taskBreak=$taskPicture.Range.Paragraphs.Item(1).Range.End-1
    if($taskCaption.Start -ne $taskBreak+1){throw 'Picture/caption boundary changed'}
    $taskDoc.Range($taskBreak,$taskBreak+1).Text=[string][char]11
    $taskBlock=$taskPicture.Range.Paragraphs.Item(1).Range
    $taskBlock.ParagraphFormat.KeepTogether=-1;$taskBlock.ParagraphFormat.KeepWithNext=0
    $taskBlock.ParagraphFormat.Alignment=1
    $taskParagraph=Find-ExactParagraph 'Calibration instrument corrections are fully logged'
    $taskParagraph.End-=1
    $taskParagraph.Text=$taskParagraph.Text.Replace('60 executable bundles','60 microtask and repair-surrogate bundles')
    $taskParagraph=Find-ExactParagraph 'The 17 returned responses reported'
    $taskParagraph.End-=1
    $taskParagraph.Text=$taskParagraph.Text.Replace('The new calibration started on 6 October 2026; it is still running in this progress revision.','The separate ecological ML calibration started on 6 October 2026 and is still running in this progress revision.')
    # Verified against the authors' institutional publication record.
    $taskParagraph=Find-ExactParagraph 'The completed repository supporting batch used'
    $taskParagraph.End-=1
    $taskParagraph.Text=$taskParagraph.Text.Replace('cases in Luigi, Matplotlib and pandas,','BugsInPy [21] cases in Luigi, Matplotlib and pandas,')
    $taskEnd=$taskDoc.Content.End-1
    $taskRange=$taskDoc.Range($taskEnd,$taskEnd)
    $taskRange.InsertBefore("`r[21] R. Widyasari et al., BugsInPy: A database of existing bugs in Python programs to enable controlled testing and debugging studies, in Proc. ESEC/FSE, 2020, pp. 1556-1560, doi: 10.1145/3368089.3417943.`r")
    $taskReference=Find-ExactParagraph '[21] R. Widyasari'
    $taskReference.Font.Name='Times New Roman';$taskReference.Font.Size=8;$taskReference.Font.Color=0
    $taskReference.Font.Bold=0;$taskReference.Font.Italic=0
    Write-Output 'Repaginating and saving new progress revision'
    [void]$taskDoc.Fields.Update();$taskDoc.Repaginate();$taskDoc.Save()
    $taskPages=$taskDoc.ComputeStatistics(2)
    $taskDoc.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc);$taskDoc=$null
    Copy-Item -LiteralPath $taskCopy -Destination $taskOutput
    if((Get-FileHash -LiteralPath $taskSource).Hash -ne $taskSourceHash){throw 'Progress source changed'}
    [PSCustomObject]@{output=$taskOutput;authoring='Microsoft Word';figures=15;native_equations=13;tables=11;pages=$taskPages;visual_QA_required=$true} | ConvertTo-Json
}finally{
    if($null -ne $taskDoc){$taskDoc.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc)}
    if($null -ne $taskWord){$taskWord.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskWord)}
}
