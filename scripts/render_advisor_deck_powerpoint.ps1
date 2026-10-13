param([Parameter(Mandatory=$true)][string]$SourcePath,[Parameter(Mandatory=$true)][string]$OutputDirectory)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$source=(Resolve-Path -LiteralPath $SourcePath).Path
if(-not (Test-Path -LiteralPath $OutputDirectory)){New-Item -ItemType Directory -Path $OutputDirectory | Out-Null}
$output=(Resolve-Path -LiteralPath $OutputDirectory).Path
$app=$null;$deck=$null
try{
    $app=New-Object -ComObject PowerPoint.Application
    $deck=$app.Presentations.Open($source,$true,$false,$false)
    for($i=1;$i -le $deck.Slides.Count;$i++){
        $path=Join-Path $output ('slide-{0:D2}.png' -f $i)
        $deck.Slides.Item($i).Export($path,'PNG',1280,720)
        if(-not(Test-Path -LiteralPath $path)){throw "Slide $i did not export"}
        Write-Output "Rendered $i/$($deck.Slides.Count)"
    }
}finally{
    if($null -ne $deck){$deck.Close();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck)}
    if($null -ne $app){$app.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)}
}
