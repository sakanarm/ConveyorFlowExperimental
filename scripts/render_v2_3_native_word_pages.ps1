param([ValidateSet('Blinded','Unblinded')][string]$Mode='Blinded',[int]$Dpi=150,[ValidateRange(1,9)][int]$Revision=1,[string]$SourcePath='', [string]$OutputDirectory='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$v2Root=Split-Path -Parent $PSScriptRoot
$source=if($SourcePath){(Resolve-Path -LiteralPath $SourcePath).Path}else{Join-Path $v2Root "CURRENT_MANUSCRIPTS/ConveyorFlow_AJSTR_v2_3_${Mode}_Manuscript_Progress_Rev$Revision.docx"}
$taskRevisionSuffix=if($Revision -eq 1){''}else{"_rev$Revision"}
$out=if($OutputDirectory){$OutputDirectory}else{Join-Path $v2Root "AJSTR Journal/v2_3_word_work/qa_$($Mode.ToLower())$taskRevisionSuffix"}
if(-not(Test-Path -LiteralPath $out)){New-Item -ItemType Directory -Path $out | Out-Null}
$taskFolder=Join-Path ([IO.Path]::GetTempPath()) ('cf_word_pages_'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskFolder | Out-Null
$taskCopy=Join-Path $taskFolder 'manuscript.docx'
Copy-Item -LiteralPath $source -Destination $taskCopy
$taskApp=$null
$taskDoc=$null
$taskReports=@()
try{
    $taskApp=New-Object -ComObject Word.Application
    $taskApp.Visible=$false
    $taskApp.DisplayAlerts=0
    $taskApp.AutomationSecurity=3
    $taskDoc=$taskApp.Documents.Open($taskCopy,$false,$true)
    $taskDoc.ActiveWindow.View.Type=3 # print layout
    $taskDoc.Repaginate()
    $taskCount=$taskDoc.ComputeStatistics(2)
    # Word's page-metafile export reevaluates NUMPAGES against each transient
    # page and can draw '2 of 2'. Materialize only that field in the read-only
    # QA copy, using the complete paginated document count. The deliverable's
    # PAGE/NUMPAGES fields remain dynamic and unchanged on disk.
    for($taskSectionIndex=1;$taskSectionIndex -le $taskDoc.Sections.Count;$taskSectionIndex++){
        $taskSection=$taskDoc.Sections.Item($taskSectionIndex)
        for($taskHeaderIndex=1;$taskHeaderIndex -le 3;$taskHeaderIndex++){
            $taskHeader=$taskSection.Headers.Item($taskHeaderIndex)
            if(-not $taskHeader.Exists){continue}
            for($taskFieldIndex=$taskHeader.Range.Fields.Count;$taskFieldIndex -ge 1;$taskFieldIndex--){
                $taskField=$taskHeader.Range.Fields.Item($taskFieldIndex)
                if($taskField.Code.Text.Trim() -eq 'NUMPAGES'){
                    $taskField.Result.Text=[string]$taskCount
                    $taskField.Unlink()
                }
            }
        }
    }
    $taskPages=$taskDoc.ActiveWindow.Panes.Item(1).Pages
    if($taskPages.Count -ne $taskCount){throw 'Word page count mismatch'}
    Write-Host "Rendering $taskCount pages through native Word Page.EnhMetaFileBits"
    for($taskIndex=1;$taskIndex -le $taskCount;$taskIndex++){
        $taskPage=$taskPages.Item($taskIndex)
        [byte[]]$taskBytes=$taskPage.EnhMetaFileBits
        if($taskBytes.Length -lt 100){throw "Missing page representation $taskIndex"}
        $taskStream=New-Object IO.MemoryStream(,$taskBytes)
        $taskEmf=[Drawing.Imaging.Metafile]::new($taskStream)
        $taskWidth=[int][Math]::Round($taskDoc.PageSetup.PageWidth*$Dpi/72)
        $taskHeight=[int][Math]::Round($taskDoc.PageSetup.PageHeight*$Dpi/72)
        $taskBitmap=[Drawing.Bitmap]::new($taskWidth,$taskHeight)
        $taskBitmap.SetResolution($Dpi,$Dpi)
        $taskGraphics=[Drawing.Graphics]::FromImage($taskBitmap)
        $taskGraphics.Clear([Drawing.Color]::White)
        $taskGraphics.DrawImage($taskEmf,0,0,$taskWidth,$taskHeight)
        $taskPng=Join-Path $out ('page-{0:D2}.png' -f $taskIndex)
        $taskBitmap.Save($taskPng,[Drawing.Imaging.ImageFormat]::Png)
        $taskGraphics.Dispose();$taskBitmap.Dispose();$taskEmf.Dispose();$taskStream.Dispose()
        $taskReports += [PSCustomObject]@{page=$taskIndex;png=$taskPng;emf_bytes=$taskBytes.Length}
        Write-Host "Rendered native Word page $taskIndex/$taskCount"
    }
    [PSCustomObject]@{mode=$Mode;source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash;
        renderer='Microsoft Word Page.EnhMetaFileBits with GDI rasterization';word_version=$taskApp.Version;
        pages=$taskCount;dpi=$Dpi;numPages_materialized_only_in_qa_copy=$true;visual_review_required=$true;page_records=$taskReports} |
        ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $out 'native_word_render_report.json') -Encoding UTF8
}finally{
    if($null -ne $taskDoc){$taskDoc.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc)}
    if($null -ne $taskApp){$taskApp.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskApp)}
}
