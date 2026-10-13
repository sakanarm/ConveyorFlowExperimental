param()
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$v2Root=Split-Path -Parent $PSScriptRoot
$manuscripts=Join-Path $v2Root 'CURRENT_MANUSCRIPTS'
$auditPath=Join-Path $v2Root 'major_revision_v2_3/results/ecological_repair_followup_audit_v1/audit.json'
$audit=Get-Content -LiteralPath $auditPath -Raw -Encoding UTF8 | ConvertFrom-Json
if($audit.status -ne 'complete_audited' -or $audit.planned_holdout_cases -ne 6 -or
   $audit.qualified_cases -ne 5 -or $audit.completed_pairs -ne 15 -or
   $audit.status_counts.VERIFIED -ne 7 -or
   $audit.status_counts.VISIBLE_TEST_FAILED -ne 4 -or
   $audit.status_counts.UNFINISHED_OR_EMPTY_OUTPUT -ne 4){
    throw 'The independent holdout audit does not match the manuscript claims.'
}

$method='This post-main, gold-free feasibility follow-up tested a revised exact-edits output contract on unused BugsInPy holdouts; it was not an allocation-policy arm. Six cases were prespecified. All passed container environment qualification, but one Matplotlib case had only nine active passes among ten hash-selected public regression nodes and was excluded before any model call, without replacement. Five cases passed source-import and prompt-context gates. Each of three frozen MFEC deployments received the same localized buggy source and visible public test for each eligible case. There was one call per pair, no retry, a 32,768-output-token ceiling, and 15 planned calls. A guarded adapter applied exact before/after edits only to allowed production files. Verification required the visible bug test, all ten selected public regressions, and fresh-container replay of both checks.'
$result='The independently audited batch completed 15/15 started calls: 7 verified repairs, 4 visible-test failures, and 4 unfinished or empty outputs. Tencent HY3 verified 5/5, GPT-5 mini 1/5, and GLM-5.3-flash 1/5; four GLM responses were empty with finish_reason=length at the output ceiling. These are observations of named deployments under this contract, not general model rankings. The gateway reported 166,363 input and 246,358 output tokens in total; its cost currency remains unverified. The original six-block allocation result remains unchanged: CF-Fit and Central-Fit verified no repository repair, whereas Static Owners verified one. The new 7/15 feasibility result is not pooled with that result or used to recalibrate Ability Ranks.'
$caveat='This follow-up establishes conditional localized repair feasibility on five qualified public holdouts. It does not establish unseen-repository reliability, autonomous repository navigation, a CF-Fit advantage, or a pure causal effect of decentralized decision-making. Public tests may be represented in model training data. A further paired allocation comparison would need the same exact-edits contract in every arm.'

$specs=@(
    [PSCustomObject]@{Name='IEEE';Source='ConveyorFlow_IEEE_Manuscript_v2_3_Main_Rev7.docx';Output='ConveyorFlow_IEEE_Manuscript_v2_3_Main_Rev8.docx';Marker='VII. DISCUSSION';Heading='N. Post-Main Holdout Repository-Repair Feasibility';StylePrefix='M. Paired Ecological Main Results';Figures=15;Tables=12},
    [PSCustomObject]@{Name='AJSTR_Blinded';Source='ConveyorFlow_AJSTR_v2_3_Blinded_Manuscript_Main_Rev5.docx';Output='ConveyorFlow_AJSTR_v2_3_Blinded_Manuscript_Main_Rev6.docx';Marker='3.12. Interpretation';Heading='3.11.4. Post-main holdout repository-repair feasibility';StylePrefix='3.11.3. Paired ecological real-model results';Figures=16;Tables=11},
    [PSCustomObject]@{Name='AJSTR_Unblinded';Source='ConveyorFlow_AJSTR_v2_3_Unblinded_Manuscript_Main_Rev5.docx';Output='ConveyorFlow_AJSTR_v2_3_Unblinded_Manuscript_Main_Rev6.docx';Marker='3.12. Interpretation';Heading='3.11.4. Post-main holdout repository-repair feasibility';StylePrefix='3.11.3. Paired ecological real-model results';Figures=16;Tables=11}
)

function Find-Paragraph {
    param($Document,[string]$Text)
    $found=$Document.Content.Duplicate
    $found.Find.ClearFormatting()
    $found.Find.Text=$Text
    $found.Find.Wrap=0
    $found.Find.MatchWildcards=$false
    if(-not $found.Find.Execute()){throw "Missing paragraph: $Text"}
    $paragraph=$found.Paragraphs.Item(1).Range.Duplicate
    if(-not $paragraph.Text.StartsWith($Text)){throw "Unexpected paragraph match: $Text"}
    return $paragraph
}

$word=$null
$document=$null
$reports=@()
try {
    $word=New-Object -ComObject Word.Application
    $word.Visible=$false
    $word.DisplayAlerts=0
    $word.AutomationSecurity=3
    $word.ScreenUpdating=$false
    foreach($spec in $specs){
        $source=Join-Path $manuscripts $spec.Source
        $output=Join-Path $manuscripts $spec.Output
        if(Test-Path -LiteralPath $output){throw "Refusing to overwrite $output"}
        $sourceHash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        Copy-Item -LiteralPath $source -Destination $output
        try {
            $document=$word.Documents.Open($output,$false,$false)
            if($document.InlineShapes.Count -ne $spec.Figures -or
               $document.OMaths.Count -ne 13 -or
               $document.Tables.Count -ne $spec.Tables){throw "Input preservation count mismatch: $($spec.Name)"}
            $headingStyle=(Find-Paragraph $document $spec.StylePrefix).Style
            $marker=Find-Paragraph $document $spec.Marker
            $start=$marker.Start
            $paragraphs=@($spec.Heading,$method,$result,$caveat)
            $block=($paragraphs -join "`r")+"`r"
            $document.Range($start,$start).InsertBefore($block)
            $inserted=$document.Range($start,$start+$block.Length)
            if($inserted.Paragraphs.Count -ne 4){throw "Inserted paragraph count mismatch: $($spec.Name)"}
            $inserted.Paragraphs.Item(1).Range.Style=$headingStyle
            $inserted.Paragraphs.Item(1).Range.ParagraphFormat.KeepWithNext=-1
            for($i=2;$i -le 4;$i++){
                $inserted.Paragraphs.Item($i).Range.Style=$document.Styles.Item(-1)
            }
            if($document.InlineShapes.Count -ne $spec.Figures -or
               $document.OMaths.Count -ne 13 -or
               $document.Tables.Count -ne $spec.Tables){throw "Output preservation count mismatch: $($spec.Name)"}
            [void]$document.Fields.Update()
            $document.Repaginate()
            $pages=$document.ComputeStatistics(2)
            $document.Save()
            $document.Close($false)
            [void][Runtime.InteropServices.Marshal]::ReleaseComObject($document)
            $document=$null
            if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $sourceHash){throw "Source changed: $source"}
            $reports += [PSCustomObject]@{name=$spec.Name;output=$output;pages=$pages;figures=$spec.Figures;tables=$spec.Tables;equations=13;source_sha256=$sourceHash;output_sha256=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash}
        } catch {
            if($null -ne $document){$document.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($document);$document=$null}
            throw
        }
    }
    $reports | ConvertTo-Json -Depth 3
} finally {
    if($null -ne $document){$document.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($document)}
    if($null -ne $word){$word.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)}
}
