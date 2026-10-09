param([ValidateSet('IEEE','AJSTR_Blinded','AJSTR_Unblinded','All')][string]$Mode='All')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$v2Root=Split-Path -Parent $PSScriptRoot
$current=Join-Path $v2Root 'CURRENT_MANUSCRIPTS'
$analysisPath=Join-Path $v2Root 'major_revision_v2_3/ecological_v1/main_analysis_with_replacement_v1.json'
$analysis=Get-Content -LiteralPath $analysisPath -Raw -Encoding UTF8 | ConvertFrom-Json
if($analysis.status -ne 'audited_main_vector_analysis_with_disclosed_replacement'){
    throw "Unexpected main analysis status: $($analysis.status)"
}
if($analysis.blocks.Count -ne 6 -or -not $analysis.interrupted_original_block_excluded){throw 'The six-block replacement analysis is not complete'}
$expectedHash='4808c4b22923c25c30b7fd686c33edf266755fcb5aaa4eb6b0ef7cd0dd3e44e7'
if((Get-FileHash -LiteralPath $analysisPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash){throw 'Main analysis hash changed; review the text before authoring'}

function Find-Paragraph($Document,[string]$Prefix){
    $r=$Document.Content.Duplicate
    $r.Find.ClearFormatting();$r.Find.Text=$Prefix;$r.Find.Wrap=0;$r.Find.MatchWildcards=$false
    while($r.Find.Execute()){
        $p=$r.Paragraphs.Item(1).Range.Duplicate
        if($p.Text.StartsWith($Prefix)){return $p}
        $r.Start=$p.End;$r.End=$Document.Content.End
    }
    throw "Missing paragraph: $Prefix"
}
function Replace-Paragraph($Document,[string]$Prefix,[string]$Text){
    $p=Find-Paragraph $Document $Prefix
    $p.End-=1
    $p.Text=$Text
}
function Insert-Paragraph($Document,[string]$Anchor,[string]$Text,[bool]$Heading=$false){
    $anchorPara=Find-Paragraph $Document $Anchor
    $at=$anchorPara.Start
    $r=$Document.Range($at,$at)
    $r.InsertBefore($Text+"`r")
    $r=$Document.Range($at,$at+$Text.Length+1)
    $r.Style=$Document.Styles.Item(-1)
    $r.Font.Name='Times New Roman';$r.Font.Color=0
    $r.Font.Size=10
    $r.Font.Bold=if($Heading){-1}else{0}
    $r.Font.AllCaps=0;$r.Font.SmallCaps=0
    $r.ParagraphFormat.Alignment=0
    $r.ParagraphFormat.KeepWithNext=if($Heading){-1}else{0}
    $r.ParagraphFormat.SpaceAfter=if($Heading){5}else{4}
}
function Insert-ResultsTable($Document,[string]$Anchor,[string]$Caption,[bool]$IEEE){
    Insert-Paragraph $Document $Anchor $Caption $false
    $captionPara=Find-Paragraph $Document $Caption
    $captionPara.ParagraphFormat.KeepWithNext=-1
    $captionPara.ParagraphFormat.Alignment=1
    $captionPara.Font.Size=8
    $rows=@(
        @('Allocation','Verified /18','Jobs/h','Cost / job'),
        @('CF-Fit','11','1.833','0.02991'),
        @('Central-Fit','10','1.667','0.03060'),
        @('Static Owners','12','2.000','0.02880')
    )
    $at=$captionPara.End
    $table=$Document.Tables.Add($Document.Range($at,$at),4,4)
    $table.AllowAutoFit=$false
    $table.PreferredWidthType=3
    $widths=if($IEEE){@(72,52,50,64)}else{@(90,65,65,80)}
    for($j=1;$j -le 4;$j++){$table.Columns.Item($j).Width=$widths[$j-1]}
    for($i=1;$i -le 4;$i++){
        for($j=1;$j -le 4;$j++){$table.Cell($i,$j).Range.Text=$rows[$i-1][$j-1]}
        $table.Rows.Item($i).AllowBreakAcrossPages=$false
    }
    $table.Range.Font.Name='Times New Roman';$table.Range.Font.Size=8
    $table.Range.ParagraphFormat.SpaceAfter=2
    $table.TopPadding=3;$table.BottomPadding=3
    $table.Rows.Item(1).HeadingFormat=-1;$table.Rows.Item(1).Range.Font.Bold=-1
    $table.Borders.Enable=0
    foreach($edge in @(-1,-3,-5)){$table.Borders.Item($edge).LineStyle=1}
}
function Edit-IEEE($doc){
    Replace-Paragraph $doc 'Abstract—' 'Abstract—Heterogeneous large-language-model agents differ in capability, time, and cost. ConveyorFlow lets idle agents choose dependency-ready tasks on a shared belt through local capability-task assessment, fit, and soft stand-down. A frozen 22,500-run simulation evaluated allocation trade-offs and controlled team heterogeneity. CF-Fit raised verified throughput over static controls by 9.4–45.3% but increased cost by 4.7–52.4%; fit and aging had clearer effects than stand-down. A separate 60-case real-model microtask tier and a matched 2,160-run architecture extension tested implementation and decision-path controls. We then ran a six-block real-LLM study on executable Adult and Beijing four-stage ML pipelines and BugsInPy repository repairs. Each block compared CF-Fit, a centralized implementation of the same fit rule, and fixed Static Owners using the same three-agent roster and fixed 3,600-second horizon. Within the horizon, CF-Fit, Central-Fit, and Static Owners verified 11/18, 10/18, and 12/18 jobs, respectively. The arms verified 11, 10, and 11 of 12 ML pipelines; only Static Owners verified one of six repository repairs. Mean verified throughput was 1.833, 1.667, and 2.000 jobs/hour, respectively. CF-Fit completed its successful jobs faster than Static Owners but did not verify as many jobs. The small, reused-workload study does not establish equivalence, a causal decision-locus effect, or system-wide fault tolerance. ConveyorFlow is evaluated as a measurable trade-off mechanism, not a universally superior allocator.'
    Replace-Paragraph $doc 'Research progress version 2.3' 'Research revision 2.3, 8 October 2026. The executable paired real-LLM main study is complete and independently audited. Human difficulty validation and broader repository-repair replication remain open; this manuscript requires final journal-format and coauthor review before submission.'
    Replace-Paragraph $doc 'The next ML calibration was frozen' 'Ecological calibration was frozen before the paired main run at 24 new task specifications, four stages, and three dated deployments (288 first attempts). Corpus-level data and row splits were reused, so the specifications are variants from two corpora rather than independent datasets. Stage-specific outcomes informed workload-dependent operational routing profiles; model brand, price, and release date did not define Ability Rank. The six-block main study used the frozen three-agent roster, not a profile revised after seeing allocation outcomes.'
    Replace-Paragraph $doc 'The original Central-Fit contrast changes' 'The original Central-Fit contrast changes both candidate pairs and assignment rule. A separate Central-Matched simulation holds local proposals fixed and adds a relay. In the ecological real-LLM main, CF-Fit and CENTRAL_RULE_MATCHED use the same fit rule, roster, READY frontier, verifier, retry bounds, and atomic claim store; the pure allocation choice is evaluated in agent processes or one coordinator process, respectively. Real-time model assignments and provider latency can still differ. The six-block comparison therefore narrows, but does not completely isolate, the causal effect of decision location. Shared belt, claim store, verifier, and gateway remain common dependencies.'
    Replace-Paragraph $doc 'Probability provenance remains explicit.' 'Probability provenance remains explicit. The original simulation curves and arrivals are scenario assumptions, not estimates from MFEC executions. Completed ecological calibration supplied operational profiles for the separate live main, but it does not retroactively fit the 22,500 simulated runs or validate their assumed probabilities.'
    Replace-Paragraph $doc 'Figure 1 describes the original simulation' 'Figure 1 describes the original simulation and microtask engines. The later container-based executable studies use separate harnesses. The paired ecological main uses a shared READY belt with real agent-process choices, atomic claims, stage-gated ML artifacts, and container-verified repository patches; it should not be described as the exact same executable core as either original tier.'
    Replace-Paragraph $doc 'The ecological ML sandbox also imposes' 'The ecological ML sandbox imposes a frozen 256 MiB file-size limit. CPU, memory, and time limits were stated in the prompt, but this file limit was not explicit. One Beijing training attempt reached it; the failure remains in the ledger. Such outcomes reflect the full artifact contract, not intrinsic regression ability. No selective investigator repair promoted the failed observation.'
    Replace-Paragraph $doc 'The Real-LLM study used the selected' 'The original Real-LLM microtask study used the selected three-agent team, 60 ML microtasks and repair-surrogate cases, deterministic validators, and ten paired seeds. Each atomic-claim winner was executed once at a time per agent, while independent agents ran concurrently without a round barrier. Provider failures after the frozen retry limit invalidated a policy run rather than being counted as task-quality failures. Table VII reports this original tier, not the later executable six-block main. The 22,500-run simulation remains the controlled mechanism analysis.'
    Replace-Paragraph $doc 'The 17 returned responses reported' 'The 17 returned responses reported 223,970 input tokens and 223,724 output tokens, with 0.199841350 provider-reported cost units. One unresolved request has unknown billing. These supporting results show bounded executable repairs under this contract, not autonomous repository-wide repair or an allocation-policy advantage. The later ecological calibration and six-block paired allocation main are reported separately.'
    Replace-Paragraph $doc 'Returned responses recorded 164113' 'Returned responses recorded 164113 input tokens, 183522 output tokens, and 0.159635836 provider cost units. Billing remains unknown for two provider-unresolved requests. The operational denominator retains every planned pair, including failures and unresolved requests. Source files were investigator-localized, and verification used ten case-specific public regressions and fresh replay. With two cases per repository and deployment, nominal Wilson intervals are descriptive references, not uncertainty estimates for a general repository population. This calibration does not itself assign universal Ability Ranks or estimate a difficulty-specific success curve; the separate completed paired main uses a frozen operational profile.'
    Insert-Paragraph $doc 'VI. RESULTS' 'I. Frozen Ecological Real-LLM Allocation Main' $true
    Insert-Paragraph $doc 'VI. RESULTS' 'Six mixed-workload blocks each admitted one Adult ML DAG, one Beijing ML DAG, and one BugsInPy repair at 0, 20, and 40 seconds. ML jobs required verified ingest, preprocessing, training, and packaging in order. The three arms shared job specifications, agent roster, capability/resource profiles, validators, and a 3,600-second observation horizon. Arm order was balanced across all six permutations. Static Owners assigned task ownership before execution; it made no runtime assignment choice. The repository verifier required a guarded patch, visible bug test, public regressions, and fresh replay. The prespecified outcome vector was verified jobs/hour, completion time conditional on verification, busy-agent fraction, and provider-reported cost units per verified job. Failures, dead letters, unsettled work, and unknown billing were retained separately.'
    Insert-Paragraph $doc 'VII. DISCUSSION' 'M. Paired Ecological Main Results' $true
    Insert-Paragraph $doc 'VII. DISCUSSION' 'All six analyzed blocks have independent audit capsules and 155 recorded provider attempts. Blocks 01–04 and 06 used the original lock. The original Block 05 was interrupted by a user pause and has no complete three-arm result; its partial ledger remains archived, including one request with unknown provider/billing outcome. Block 05_R1 reran all three arms under a separately hashed technical replacement lock with the same cases, order, seed, models, and limits. No original partial Block 05 result entered the analysis.'
    Insert-ResultsTable $doc 'VII. DISCUSSION' 'TABLE XII. AUDITED SIX-BLOCK ECOLOGICAL REAL-LLM RESULTS' $true
    Insert-Paragraph $doc 'VII. DISCUSSION' 'CF-Fit verified 11 of 12 ML pipelines and no repository repair. Central-Fit verified 10 ML pipelines and no repair. Static Owners verified 11 ML pipelines and one Matplotlib repair, yielding 12/18 verified jobs overall. Mean successful-job completion times were 322.20, 273.59, and 719.53 s for CF-Fit, Central-Fit, and Static Owners. Mean busy-agent fractions were 0.0714, 0.0510, and 0.0914. The cost column reports the mean of six block-level provider-reported cost/verified-job ratios; its monetary currency is unconfirmed. Completion time is conditional on different verified-job subsets, and higher busy fraction is not automatically better.'
    Insert-Paragraph $doc 'VII. DISCUSSION' 'For CF-Fit minus Central-Fit, mean paired-block differences were +0.167 verified jobs/hour, +48.61 s in conditional successful-job completion, +0.0205 in busy fraction, and −0.00069 reported cost units per verified job. For CF-Fit minus Static Owners they were −0.167 jobs/hour, −397.33 s, −0.0200, and +0.00111 units/job. The five original complete blocks alone gave 0.000 jobs/hour for CF-Fit minus Central-Fit and −0.200 for CF-Fit minus Static, showing sensitivity to the technical replacement. A descriptive six-block bootstrap interval for the first throughput contrast was [−0.333, +0.667] jobs/hour. With two reused ML corpora, three repository projects, and only six blocks, these intervals are descriptive rather than population confidence intervals; no equivalence test is claimed.'
    Replace-Paragraph $doc 'The live MFEC execution provides' 'The original 60-case MFEC microtask tier provides an implementation check and retains its separate denominator. The executable six-block main adds stage-gated ML pipelines and real repository repair attempts. It shows no universal winner: Static Owners verified the most jobs, CF-Fit finished its verified subset much faster than Static, and Central-Fit had the shortest conditional completion time. The single successful repository repair occurred under Static Owners. CF-Fit and Central-Fit use a matched fit rule, but their observed outputs do not prove equivalence or a pure causal decision-locus effect. Removing a global matcher reduces reliance on an allocation decision point, while shared services and provider gateways remain untested failure dependencies.'
    Replace-Paragraph $doc 'Internal validity is strengthened' 'Internal validity is strengthened by frozen seeds, common random numbers in simulation, source hashes, append-only ledgers, predeclared live cases and validators, and independent block audits. The six-block live main reuses Adult and Beijing data variants and contains only three repository projects. Provider time and model assignment vary despite matched rules. The interrupted original Block 05 was excluded, and its full technical replacement is disclosed. Strict unified-diff output and token limits affected many repair attempts; CF-Fit itself verified no repository repair in this main. The six blocks do not establish population effects, architectural equivalence, or fault tolerance. Human difficulty validation, additional providers, more repositories, and genuine component-failure tests remain future work.'
    Replace-Paragraph $doc 'ConveyorFlow reframes heterogeneous' 'ConveyorFlow lets heterogeneous agents self-select dependency-ready work on a shared belt using capability fit, soft stand-down, aging, and atomic claims. The 22,500-run simulation supports context-dependent throughput, time, utilization, cost, and task-outcome trade-offs against static and centralized controls; fit and aging were more consequential than stand-down in the tested settings. The audited six-block real-LLM main verified 11/18 CF-Fit jobs, 10/18 Central-Fit jobs, and 12/18 Static Owners jobs, including one real repository repair only under Static. CF-Fit completed its verified subset faster than Static but did not verify as many jobs. These observations support executable feasibility and an interpretable allocation comparison, not universal superiority, equivalence, or system-wide fault tolerance. Human difficulty validation and broader repair replication remain open.'
}

function Edit-AJSTR($doc,[bool]$Blinded){
    Replace-Paragraph $doc 'Abstract:' 'Abstract: Large language model agents differ in ability, speed, and cost. ConveyorFlow lets idle agents choose dependency-ready tasks on a shared belt. Local capability fit guides their bids, while overqualified agents can temporarily stand down. A frozen simulation with 22,500 runs found higher verified throughput than static allocation but also higher cost in the tested settings. A separate 2,160-run extension checked a matched coordinator path. We then ran six paired real-model blocks on Adult and Beijing four-stage ML pipelines and BugsInPy repository repairs. Each block used the same three-agent roster, tasks, verifier, and 3,600-second horizon under CF-Fit, a centralized version of the same fit rule, and fixed Static Owners. CF-Fit verified 11/18 jobs, Central-Fit 10/18, and Static Owners 12/18. The arms verified 11, 10, and 11 ML pipelines; only Static Owners verified one repository repair. Mean verified throughput was 1.833, 1.667, and 2.000 jobs/hour. CF-Fit finished its successful jobs faster than Static, but verified fewer jobs. These six blocks reuse two ML corpora and three repository projects, so the results do not show equivalence, a pure effect of decision location, or system-wide fault tolerance. The evidence describes trade-offs rather than one policy winning every measure.'
    Replace-Paragraph $doc 'The executable pipeline, decoded repository repair' 'The executable pipeline, separate repair pilots, completed ecological calibration, and audited six-block paired main address different questions and retain separate denominators. The main tests allocation on full ML DAGs and real repository attempts; the earlier microtasks cannot substitute for it. The single verified main-tier repair was obtained under Static Owners, not CF-Fit. Six blocks across reused corpora and three repositories do not establish general repository-repair superiority.'
    Replace-Paragraph $doc 'Ingest validation checks the public column' 'Ingest validation checks the public column and row manifest. Preprocessing and training require successful container exit and nonempty artifacts, and successor release checks predecessor reports and artifact hashes. Packaging must produce exactly the hidden test row IDs and finite predictions. The final quality gate uses ROC-AUC for Adult and mean absolute error for Beijing and was frozen before provider calls. These feasibility checks alone do not prove training-only fitting, robustness to all input changes, or production-quality model selection. The later ecological main adds stage-gated execution and clean verification, but still does not establish production ML quality.'
    Replace-Paragraph $doc 'Returned responses reported 223,970' 'Returned responses reported 223,970 input tokens and 223,724 output tokens, with 0.199841350 provider-reported cost units from 17 responses. One call had an unknown or missing cost amount. These units are not labelled US dollars or total billed cost. This separate first-attempt batch establishes bounded executable repository repairs under its frozen contract; its cases and outcomes are not pooled with the later six-block allocation main.'
    Replace-Paragraph $doc 'The simulation uses assumed success' 'The simulation uses assumed success, time, token-demand, assessment, and cost functions. Its ranks are behavioral settings, not model versions. Public datasets shape task variants but do not supply the assumed simulation probabilities. The original real-model tier tests small independent tabular calculations and repair surrogates. The later executable main tests staged ML pipelines and actual repository patches in containers, but its small, reused workload does not support a population claim.'
    Replace-Paragraph $doc 'Frozen seeds, common random numbers' 'Frozen simulation seeds, source hashes, append-only ledgers, predeclared live cases and validators, and independent audits support traceability. The six-block live main reuses Adult and Beijing corpora, samples only three repository projects, and depends on dated provider aliases. CF-Fit and Central-Fit share a fit rule, but live model assignment and provider delay can differ, so this is not a pure causal estimate of decision location. The user-interrupted original Block 05 was excluded and fully rerun as a separately locked technical replacement. Strict patch format and output caps limited repository success. Human difficulty labels, wider provider and repository samples, and component-failure tests remain open.'
    Replace-Paragraph $doc 'ConveyorFlow lets heterogeneous agents choose' 'ConveyorFlow lets heterogeneous agents choose dependency-ready work on a shared belt through local fit and temporary stand-down. In the controlled simulation, CF-Fit improved throughput against several static controls but cost more, while fit and aging contributed more visibly than stand-down. In six audited real-model blocks, CF-Fit verified 11/18 jobs, Central-Fit 10/18, and Static Owners 12/18. CF-Fit finished its verified subset faster than Static but did not verify as many jobs; only Static verified a repository repair. The mechanism removes a global assignment decision, not the shared belt or claim store. These results establish measured trade-offs and executable feasibility in this setting, not universal superiority, policy equivalence, or system-wide fault tolerance.'
    Insert-Paragraph $doc '3. Results and Discussion' '2.4.4. Frozen paired ecological allocation' $true
    Insert-Paragraph $doc '3. Results and Discussion' 'The ecological main used six mixed-workload blocks. Each block admitted one Adult ML pipeline, one Beijing ML pipeline, and one BugsInPy repository repair at 0, 20, and 40 seconds. ML stages followed ingest, preprocessing, training, and packaging; a successor could use only verified predecessor artifacts. CF-Fit, CENTRAL_RULE_MATCHED, and Static Owners shared the jobs, three-agent roster, ability/resource profiles, verifier, retry bounds, and 3,600-second horizon. Arm order covered all six permutations. Static ownership was fixed before execution; the central and local arms used the same fit rule and atomic claim store. The four reported outcomes were verified jobs/hour, completion time conditional on verification, busy-agent fraction, and provider-reported cost units per verified job. Failures and unresolved outcomes stayed in the accounting.'
    Insert-Paragraph $doc '3.12. Interpretation' '3.11.3. Paired ecological real-model results' $true
    Insert-Paragraph $doc '3.12. Interpretation' 'Independent audits covered all six analyzed blocks and 155 provider attempts. Blocks 01–04 and 06 followed the original lock. A user pause interrupted original Block 05 before all three arms finished; its partial ledger was preserved and excluded. Block 05_R1 reran all three arms under a separately hashed technical replacement lock with unchanged cases, order, seed, models, and limits. One original interrupted request has an unknown provider and billing outcome. Neither its partial result nor any attempted cost was silently merged with the replacement.'
    Insert-ResultsTable $doc '3.12. Interpretation' 'Table 11. Audited ecological real-model allocation results' $false
    Insert-Paragraph $doc '3.12. Interpretation' 'CF-Fit verified 11/12 ML pipelines and 0/6 repository repairs. Central-Fit verified 10/12 and 0/6; Static Owners verified 11/12 and 1/6. The successful repair was Matplotlib case 28 in the Static arm; visible and regression checks passed again in fresh containers. Mean successful-job completion times were 322.20, 273.59, and 719.53 seconds for CF-Fit, Central-Fit, and Static Owners. Busy-agent fractions were 0.0714, 0.0510, and 0.0914. Table 11 gives the mean of six block-level cost-per-verified-job ratios. Provider cost currency is unconfirmed. Time is conditional on different successful subsets, and higher busy time need not mean better resource use.'
    Insert-Paragraph $doc '3.12. Interpretation' 'Mean paired CF-Fit minus Central-Fit differences were +0.167 verified jobs/hour, +48.61 seconds for successful-job completion, +0.0205 busy fraction, and −0.00069 reported cost units per verified job. Against Static Owners they were −0.167 jobs/hour, −397.33 seconds, −0.0200, and +0.00111 units/job. With only the five original complete blocks, the throughput differences were 0.000 and −0.200 jobs/hour. The descriptive six-block bootstrap interval for CF-Fit minus Central-Fit throughput was [−0.333, +0.667] jobs/hour. These intervals are not population confidence intervals or equivalence tests: six blocks reuse two ML corpora and three repositories.'
    Replace-Paragraph $doc 'The main finding is a trade-off' 'The main finding is a trade-off. In the controlled simulation, CF-Fit improved some speed and throughput outcomes but did not beat the centralized matcher on the primary cost-throughput pair. In the executable six-block main, Static Owners verified the most jobs, CF-Fit completed its verified subset much faster than Static, and Central-Fit had the shortest conditional completion time. The central and local real-model arms use the same fit rule, yet live assignment and provider timing can differ. Thus the comparison is informative but does not isolate decision location completely.'
    Replace-Paragraph $doc 'The live study supports a narrower claim.' 'The 60-case real-model microtask study remains a separate supplementary tier. Its original CF-Fit versus Central-Fit comparison did not establish equivalence. The later matched-rule ecological main adds full ML DAGs and actual repository attempts, with one verified repair under Static only. Local self-selection removes a global agent-task matcher, but the READY belt, atomic store, verifier, and provider gateway remain shared. The synthetic coordinator-outage simulation does not prove production fault tolerance.'
    if(-not $Blinded){
        Replace-Paragraph $doc 'The project code repository is' 'Code, frozen configurations, public-data manifests, analysis scripts, editable diagrams, and derived results are available at https://github.com/sakanarm/ConveyorFlowExperimental. Historical raw provider and container artifacts are retained by the investigators; not all are distributed. New runs require their own dated provider and container audit. Public datasets remain at their original sources under their licenses.'
    }
}

$items=@()
if($Mode -in @('All','IEEE')){$items+=@{name='IEEE';source='ConveyorFlow_IEEE_Manuscript_v2_3_Progress_Rev6.docx';output='ConveyorFlow_IEEE_Manuscript_v2_3_Main_Rev7.docx';figures=15;equations=13;tables=11}}
if($Mode -in @('All','AJSTR_Blinded')){$items+=@{name='AJSTR_Blinded';source='ConveyorFlow_AJSTR_v2_3_Blinded_Manuscript_Progress_Rev4.docx';output='ConveyorFlow_AJSTR_v2_3_Blinded_Manuscript_Main_Rev5.docx';figures=16;equations=13;tables=10}}
if($Mode -in @('All','AJSTR_Unblinded')){$items+=@{name='AJSTR_Unblinded';source='ConveyorFlow_AJSTR_v2_3_Unblinded_Manuscript_Progress_Rev4.docx';output='ConveyorFlow_AJSTR_v2_3_Unblinded_Manuscript_Main_Rev5.docx';figures=16;equations=13;tables=10}}
foreach($item in $items){if(Test-Path -LiteralPath (Join-Path $current $item.output)){throw "Output exists: $($item.output)"}}

$word=$null
try{
    $word=New-Object -ComObject Word.Application
    $word.Visible=$false;$word.DisplayAlerts=0;$word.AutomationSecurity=3;$word.ScreenUpdating=$false
    foreach($item in $items){
        $source=Join-Path $current $item.source
        $output=Join-Path $current $item.output
        $working=Join-Path ([IO.Path]::GetTempPath()) ('cf_v23_main_'+[guid]::NewGuid().ToString('N')+'.docx')
        Copy-Item -LiteralPath $source -Destination $working
        $doc=$null
        try{
            $doc=$word.Documents.Open($working,$false,$false)
            if($doc.InlineShapes.Count -ne $item.figures -or $doc.OMaths.Count -ne $item.equations -or $doc.Tables.Count -ne $item.tables){throw "Unexpected source structure: $($item.name)"}
            if($item.name -eq 'IEEE'){Edit-IEEE $doc}else{Edit-AJSTR $doc ($item.name -eq 'AJSTR_Blinded')}
            if($doc.InlineShapes.Count -ne $item.figures -or $doc.OMaths.Count -ne $item.equations -or $doc.Tables.Count -ne ($item.tables+1)){throw "Preservation check failed: $($item.name)"}
            [void]$doc.Fields.Update()
            $doc.Repaginate()
            $doc.Save()
            Copy-Item -LiteralPath $working -Destination $output
            Write-Host "$($item.name): $output pages=$($doc.ComputeStatistics(2)) figures=$($doc.InlineShapes.Count) equations=$($doc.OMaths.Count) tables=$($doc.Tables.Count)"
        }finally{
            if($null -ne $doc){$doc.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc)}
        }
    }
}finally{
    if($null -ne $word){$word.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)}
    [GC]::Collect();[GC]::WaitForPendingFinalizers()
}
