param([Parameter(Mandatory=$true)][string]$PageDirectory,[int]$Columns=3,[int]$Rows=4,[int]$ThumbWidth=330,[string]$Pattern='page-*.png',[switch]$Landscape)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$folder=(Resolve-Path -LiteralPath $PageDirectory).Path
$pages=@(Get-ChildItem -LiteralPath $folder -Filter $Pattern -File | Sort-Object Name)
if($pages.Count -eq 0){throw 'No rendered Word pages found'}
$cellW=$ThumbWidth+20
$cellH=if($Landscape){[int][Math]::Round($ThumbWidth*0.59)+35}else{[int][Math]::Round($ThumbWidth*1.42)+35}
$perSheet=$Columns*$Rows
for($start=0;$start -lt $pages.Count;$start+=$perSheet){
    $sheet=[Drawing.Bitmap]::new($cellW*$Columns,$cellH*$Rows)
    $graphics=[Drawing.Graphics]::FromImage($sheet)
    $graphics.Clear([Drawing.Color]::White)
    $graphics.InterpolationMode=[Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $font=[Drawing.Font]::new('Arial',12)
    $brush=[Drawing.Brushes]::Black
    for($slot=0;$slot -lt $perSheet -and $start+$slot -lt $pages.Count;$slot++){
        $page=$pages[$start+$slot]
        $image=[Drawing.Image]::FromFile($page.FullName)
        try{
            $col=$slot%$Columns
            $row=[int][Math]::Floor($slot/$Columns)
            $x=$col*$cellW+10
            $y=$row*$cellH+23
            $targetH=[int][Math]::Round($ThumbWidth*$image.Height/$image.Width)
            $graphics.DrawString($page.Name,$font,$brush,$x,$row*$cellH+2)
            $graphics.DrawImage($image,$x,$y,$ThumbWidth,$targetH)
            $graphics.DrawRectangle([Drawing.Pens]::LightGray,$x,$y,$ThumbWidth,$targetH)
        }finally{$image.Dispose()}
    }
    $index=[int][Math]::Floor($start/$perSheet)+1
    $output=Join-Path $folder ('contact-{0:D2}.png' -f $index)
    $sheet.Save($output,[Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose();$sheet.Dispose();$font.Dispose()
    Write-Output $output
}
