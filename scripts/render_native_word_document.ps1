param([Parameter(Mandatory=$true)][string]$SourcePath,[Parameter(Mandatory=$true)][string]$OutputDirectory,[int]$Dpi=150)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$taskV2=(Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$taskSource=(Resolve-Path -LiteralPath $SourcePath).Path
$taskOut=[IO.Path]::GetFullPath($OutputDirectory)
if(-not $taskSource.StartsWith($taskV2+[IO.Path]::DirectorySeparatorChar) -or
   -not $taskOut.StartsWith($taskV2+[IO.Path]::DirectorySeparatorChar)){throw 'Render targets must stay within v2'}
if(Test-Path -LiteralPath $taskOut){throw 'Use a NEW render directory, never stale page PNGs'}
New-Item -ItemType Directory -Path $taskOut | Out-Null
$taskTemp=Join-Path ([IO.Path]::GetTempPath()) ('cf_word_render_'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskTemp | Out-Null
$taskCopy=Join-Path $taskTemp 'manuscript.docx';Copy-Item -LiteralPath $taskSource -Destination $taskCopy
$taskHash=(Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash
$taskApp=$null;$taskDoc=$null;$taskRecords=@()
try{
    $taskApp=New-Object -ComObject Word.Application
    $taskApp.Visible=$false;$taskApp.DisplayAlerts=0;$taskApp.AutomationSecurity=3;$taskApp.Options.AllowReadingMode=$false
    $taskDoc=$taskApp.Documents.Open($taskCopy,$false,$true);$taskDoc.ActiveWindow.View.Type=3
    $taskDoc.Repaginate();$taskCount=$taskDoc.ComputeStatistics(2)
    foreach($taskSection in $taskDoc.Sections){
        foreach($taskHeaderIndex in 1..3){
            foreach($taskStory in @($taskSection.Headers.Item($taskHeaderIndex),$taskSection.Footers.Item($taskHeaderIndex))){
                if(-not $taskStory.Exists){continue}
                for($taskFieldIndex=$taskStory.Range.Fields.Count;$taskFieldIndex -ge 1;$taskFieldIndex--){
                    $taskField=$taskStory.Range.Fields.Item($taskFieldIndex)
                    if($taskField.Code.Text.Trim() -eq 'NUMPAGES'){$taskField.Result.Text=[string]$taskCount;$taskField.Unlink()}
                }
            }
        }
    }
    $taskPages=$taskDoc.ActiveWindow.Panes.Item(1).Pages
    if($taskPages.Count -ne $taskCount){throw 'Word page-count mismatch'}
    for($taskIndex=1;$taskIndex -le $taskCount;$taskIndex++){
        [byte[]]$taskBits=$taskPages.Item($taskIndex).EnhMetaFileBits
        if($taskBits.Length -lt 100){throw 'Empty Word page representation'}
        $taskStream=[IO.MemoryStream]::new($taskBits)
        $taskEmf=[Drawing.Imaging.Metafile]::new($taskStream)
        $taskWidth=[int][Math]::Round($taskDoc.PageSetup.PageWidth*$Dpi/72)
        $taskHeight=[int][Math]::Round($taskDoc.PageSetup.PageHeight*$Dpi/72)
        $taskBitmap=[Drawing.Bitmap]::new($taskWidth,$taskHeight);$taskBitmap.SetResolution($Dpi,$Dpi)
        $taskGraphics=[Drawing.Graphics]::FromImage($taskBitmap);$taskGraphics.Clear([Drawing.Color]::White)
        $taskGraphics.DrawImage($taskEmf,0,0,$taskWidth,$taskHeight)
        $taskPng=Join-Path $taskOut ('page-{0:D2}.png' -f $taskIndex)
        $taskBitmap.Save($taskPng,[Drawing.Imaging.ImageFormat]::Png)
        $taskGraphics.Dispose();$taskBitmap.Dispose();$taskEmf.Dispose();$taskStream.Dispose()
        $taskRecords += [PSCustomObject]@{page=$taskIndex;png=$taskPng;sha256=(Get-FileHash -LiteralPath $taskPng -Algorithm SHA256).Hash}
        Write-Host "Rendered Microsoft Word page $taskIndex/$taskCount"
    }
    if((Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash -ne $taskHash){throw 'Original document changed during rendering'}
    [PSCustomObject]@{source=$taskSource;source_sha256=$taskHash;pages=$taskCount;dpi=$Dpi;renderer='Microsoft Word Page.EnhMetaFileBits';
        native_equations=$taskDoc.OMaths.Count;figures=$taskDoc.InlineShapes.Count;tables=$taskDoc.Tables.Count;
        visual_review_required=$true;page_records=$taskRecords} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $taskOut 'native_word_render_report.json') -Encoding UTF8
}finally{
    if($null -ne $taskDoc){$taskDoc.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc)}
    if($null -ne $taskApp){$taskApp.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskApp)}
}
