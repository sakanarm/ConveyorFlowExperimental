# Native Microsoft Word authoring. Creates a new progress manuscript; never overwrites v2.2.
param([string]$OutputName='ConveyorFlow_IEEE_Manuscript_v2_3_Progress_Rev7.docx')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$taskV2=Split-Path -Parent $PSScriptRoot
$taskCurrent=Join-Path $taskV2 'CURRENT_MANUSCRIPTS'
$taskSource=Join-Path $taskCurrent 'ConveyorFlow_IEEE_Manuscript.docx'
$taskFigures=Join-Path $taskCurrent 'ConveyorFlow_AJSTR_v2_3_Unblinded_Manuscript_Progress_Rev4.docx'
if([IO.Path]::GetFileName($OutputName) -ne $OutputName -or -not $OutputName.EndsWith('.docx')){throw 'Output must be a new .docx filename'}
$taskOutput=Join-Path $taskCurrent $OutputName
if(Test-Path -LiteralPath $taskOutput){throw 'New revision already exists; refusing overwrite'}
$taskMajor=Join-Path $taskV2 'major_revision_v2_3'
$taskML=Get-Content -LiteralPath (Join-Path $taskMajor 'results/ml_isolated_stage_pilot_v2_final/summary.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$taskRepo=Get-Content -LiteralPath (Join-Path $taskMajor 'results/repository_first_attempt_v1_audit_20261005.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$taskNewRepoPath=Join-Path $taskMajor 'results/ecological_repository_calibration_v1_final/summary.json'
$taskNewRepo=$null
if(Test-Path -LiteralPath $taskNewRepoPath){
    $taskNewRepo=Get-Content -LiteralPath $taskNewRepoPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if($taskNewRepo.status -ne 'completed_localized_repository_calibration' -or $taskNewRepo.total.planned_and_completed -ne 18){throw 'New repository result capsule is incomplete'}
}
if($taskML.completed_pairs -ne 36 -or -not $taskRepo.complete -or $taskRepo.completed_pairs -ne 18){throw 'Completed evidence capsules required'}
$taskSourceHash=(Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash
$taskFigureHash=(Get-FileHash -LiteralPath $taskFigures -Algorithm SHA256).Hash
$taskTemp=Join-Path ([IO.Path]::GetTempPath()) ('cf_ieee_v23_'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskTemp | Out-Null
$taskCopy=Join-Path $taskTemp 'ieee.docx';Copy-Item -LiteralPath $taskSource -Destination $taskCopy
$taskFigureCopy=Join-Path $taskTemp 'figures.docx';Copy-Item -LiteralPath $taskFigures -Destination $taskFigureCopy
$taskApp=$null;$taskDoc=$null;$taskFigDoc=$null

function Find-Paragraph($Document,[string]$Prefix){
    $r=$Document.Content.Duplicate
    $r.Find.ClearFormatting();$r.Find.Text=$Prefix;$r.Find.Wrap=0;$r.Find.MatchWildcards=$false
    while($r.Find.Execute()){
        $p=$r.Paragraphs.Item(1).Range.Duplicate
        if($p.Text.StartsWith($Prefix)){return $p}
        $r.Start=$p.End;$r.End=$Document.Content.End
    }
    throw "Missing paragraph prefix: $Prefix"
}
function Replace-Paragraph($Document,[string]$Prefix,[string]$Text){
    $r=Find-Paragraph $Document $Prefix;$r.End-=1;$r.Text=$Text
}
function Insert-Paragraph($Document,[string]$Anchor,[string]$Text,[int]$Style=-1){
    $p=Find-Paragraph $Document $Anchor;$at=$p.Start
    $r=$Document.Range($at,$at);$r.InsertBefore($Text+"`r")
    $r=$Document.Range($at,$at+$Text.Length+1);$r.Style=$Document.Styles.Item($Style)
    $r.Font.Name='Times New Roman';$r.Font.Size=10;$r.Font.Color=0;$r.Font.Bold=0;$r.Font.Italic=0
    $r.ParagraphFormat.KeepWithNext=0
    if($Style -eq -3){$r.Font.Bold=-1;$r.ParagraphFormat.KeepWithNext=-1}
    return $at
}
function Nearest-Figure($Document,$Caption){
    $shape=$null
    foreach($candidate in $Document.InlineShapes){if($candidate.Range.End -le $Caption.Start){$shape=$candidate}else{break}}
    if($null -eq $shape -or $Caption.Start-$shape.Range.End -gt 8){throw 'Caption is not adjacent to its picture'}
    return $shape
}
function Insert-Table($Document,[string]$Caption,$Rows){
    [void](Insert-Paragraph $Document 'VII. DISCUSSION' $Caption)
    $p=Find-Paragraph $Document $Caption;$p.ParagraphFormat.Alignment=1;$p.ParagraphFormat.KeepWithNext=-1;$p.Font.Size=8
    $at=$p.End;$table=$Document.Tables.Add($Document.Range($at,$at),$Rows.Count,4)
    $table.AllowAutoFit=$false;$table.PreferredWidthType=3;$table.PreferredWidth=238
    $widths=@(85,36,55,62)
    for($j=1;$j -le 4;$j++){$table.Columns.Item($j).Width=$widths[$j-1]}
    for($i=1;$i -le $Rows.Count;$i++){
        for($j=1;$j -le 4;$j++){$table.Cell($i,$j).Range.Text=[string]$Rows[$i-1][$j-1]}
        $table.Rows.Item($i).AllowBreakAcrossPages=$false
    }
    $table.Range.Font.Name='Times New Roman';$table.Range.Font.Size=8;$table.Range.ParagraphFormat.SpaceAfter=2
    $table.TopPadding=3;$table.BottomPadding=3;$table.Rows.Item(1).HeadingFormat=-1;$table.Rows.Item(1).Range.Font.Bold=-1
    $table.Borders.Enable=0
    foreach($edge in @(-1,-3,-5)){$table.Borders.Item($edge).LineStyle=1}
}

try{
    $taskApp=New-Object -ComObject Word.Application
    $taskApp.Visible=$false;$taskApp.DisplayAlerts=0;$taskApp.AutomationSecurity=3;$taskApp.ScreenUpdating=$false
    $taskApp.Options.AllowReadingMode=$false
    $taskDoc=$taskApp.Documents.Open($taskCopy,$false,$false)
    $taskFigDoc=$taskApp.Documents.Open($taskFigureCopy,$false,$true)
    $taskFigDoc.ActiveWindow.View.Type=3
    $taskDoc.Activate();$taskDoc.ActiveWindow.View.Type=3
    if($taskDoc.ReadOnly){throw 'The new working copy opened read-only'}
    if($taskDoc.InlineShapes.Count -ne 15 -or $taskDoc.OMaths.Count -ne 13 -or $taskDoc.Tables.Count -ne 8){throw 'Unexpected IEEE source structure'}
    $taskTitle=$taskDoc.Paragraphs.Item(1).Range
    $taskTitle.Style=$taskDoc.Styles.Item(-63)
    $taskDoc.Styles.Item(-63).ParagraphFormat.Borders.Enable=0
    $taskTitle.ParagraphFormat.Borders.Enable=0;$taskTitle.Font.Color=0
    $taskTitle.Font.Name='Times New Roman';$taskTitle.Font.Size=18
    $taskTitle.ParagraphFormat.Alignment=1
    Replace-Paragraph $taskDoc 'Sakan Punyanon' 'Sakan Punyanon, Chaiyaporn Khemapatapan, and Aomduan Jeamaon'
    Replace-Paragraph $taskDoc 'Affiliation and corresponding-author' 'College of Innovative Technology and Engineering, Dhurakij Pundit University, Thailand. Corresponding author: Sakan Punyanon (68140010@dpu.ac.th).'
    [void](Insert-Paragraph $taskDoc 'I. INTRODUCTION' 'Research progress version 2.3, 6 October 2026. Completed supporting execution studies are reported separately. New ecological calibration is running; paired live allocation main and independent human difficulty validation remain incomplete. This draft is not submission-ready.')
    for($n=1;$n -le 5;$n++){
        $dst=Find-Paragraph $taskDoc "Fig. $n."
        $src=Find-Paragraph $taskFigDoc "Figure $n."
        $old=Nearest-Figure $taskDoc $dst;$new=Nearest-Figure $taskFigDoc $src
        $width=$old.Width;$height=$old.Height;$at=$old.Range.Start
        $old.Range.FormattedText=$new.Range.FormattedText
        $replacement=$taskDoc.Range($at,$at+1).InlineShapes.Item(1)
        $replacement.LockAspectRatio=-1;$replacement.Width=$width
        if($replacement.Height -gt $height){$replacement.Height=$height}
        $replacement.AlternativeText=$src.Text.Trim()
        Replace-Paragraph $taskDoc "Fig. $n." ($src.Text.Trim().Replace("Figure $n.","Fig. $n."))
    }
    Replace-Paragraph $taskDoc 'Figure 2 traces' ((Find-Paragraph $taskFigDoc 'Figure 2 traces').Text.Trim())
    Replace-Paragraph $taskDoc 'Figure 5 defines' ((Find-Paragraph $taskFigDoc 'Figure 5 gives').Text.Trim())
    Replace-Paragraph $taskDoc 'The scientific contribution is therefore not' 'The scientific contribution is the allocation mechanism, not the policy count. Agents differ in capability and resource cost, so each idle agent chooses suitable work from the READY belt. Capability-task fit guides its bid. In the main simulator, soft stand-down adds a decaying priority penalty when an agent is overqualified; it does not require that agent to refuse every easy task. Aging relaxes the penalty. The experiments test the resulting cost, throughput, time, utilization and failure trade-offs, not universal dominance.'
    Replace-Paragraph $taskDoc 'Construct validity is limited by simulated' 'Construct validity is limited by simulated success, time, token, assessment and cost functions. Simulation Ability Ranks are ordinal scenario profiles, not statistically estimated capabilities of current provider models. Public corpora shape the workloads, but a simulated task is not equivalent to building an executable ML pipeline or repairing a repository. The original 60-case live study uses ML microtasks and repair surrogates; CodeXGLUE pairs are not executable repository repairs. Supporting executable studies are therefore reported separately.'
    Replace-Paragraph $taskDoc 'The live validators establish task-specific' 'The original live validators establish narrow functional success for microtasks and repair surrogates. They do not establish complete ML-build or repository-repair ability. The new isolated-stage and localized-repair verifiers narrow that gap, but public tests, explicit localization and trusted predecessors limit generalization. Provider, generation, execution and unresolved outcomes remain distinct. No stage probe is counted as a completed pipeline or as evidence of an allocation-policy advantage.'
    $taskLiveDescription=Find-Paragraph $taskDoc 'The Real-LLM tier freezes 60'
    Replace-Paragraph $taskDoc 'The Real-LLM tier freezes 60' ($taskLiveDescription.Text.Trim().Replace('60 executable cases','60 ML microtasks and repair-surrogate cases'))
    $taskLiveStudy=Find-Paragraph $taskDoc 'The Real-LLM study used the selected'
    Replace-Paragraph $taskDoc 'The Real-LLM study used the selected' ($taskLiveStudy.Text.Trim().Replace('60 executable cases','60 ML microtasks and repair-surrogate cases'))
    $taskCalibrationNote=Find-Paragraph $taskDoc 'Calibration instrument corrections are fully logged'
    Replace-Paragraph $taskDoc 'Calibration instrument corrections are fully logged' ($taskCalibrationNote.Text.Trim().Replace('60 executable bundles','60 microtask and repair-surrogate bundles'))
    $taskCostDescription=Find-Paragraph $taskDoc 'For each valid run, completion'
    Replace-Paragraph $taskDoc 'For each valid run, completion' ($taskCostDescription.Text.Trim().Replace('cost is computed from recorded input/output tokens and the frozen observed price metadata','cost is summed from the recorded provider response-cost values'))
    Replace-Paragraph $taskDoc 'Equation (13) replaces' 'Equation (13) replaces simulation ticks with measured monotonic wall time T. Each call_cost is the recorded provider response-cost value when supplied; token counts and declared rates are used only when that alternative is configured and known. Creal includes recorded calls on failed attempts. The currency of the MFEC response-cost values is unconfirmed. The extension provider-gap exclusions affect only timing-based quantities, not completion or recorded cost.'
    $taskExecution=Find-Paragraph $taskDoc 'Every paired policy run uses'
    Replace-Paragraph $taskDoc 'Every paired policy run uses' ($taskExecution.Text.Trim().Replace('churn schedule','fixed agent pool'))
    $abstract=Find-Paragraph $taskDoc 'Abstract';$text=$abstract.Text.Trim()
    $text=$text.Replace('volunteer, and temporarily stand down when overqualified.','volunteer, and lower their bid priority when overqualified.')
    $text=$text.Replace('In a supplementary ten-seed Real-LLM study,','In a supplementary ten-seed Real-LLM microtask and repair-surrogate study,')
    $text=$text.Replace('Against a matched centralized fit controller,','Against a centralized fit comparator,')
    Replace-Paragraph $taskDoc 'Abstract' $text

    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' 'H. Executable Workload Extension' -3)
    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' 'Executable workloads address a specific limitation of the original microtask study: a valid answer alone does not demonstrate a usable ML artifact or a repair that passes repository tests. We first check deterministic stage and repair contracts before testing their allocation on a live belt. Supporting feasibility observations, ecological calibration and paired allocation main are separate experimental tiers; their denominators and outcomes are not pooled.')
    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' 'In the completed ML supporting pilot, three reused specifications (two Adult and one Beijing) each supplied four isolated stages to all three deployments, giving 36 pairs. Every stage received identical trusted predecessors so that an upstream model failure could not hide later-stage performance. Generated code and serialized models ran only in locked, network-disabled Linux containers. Verification required the stage contract and fresh replay; output predictions were checked against verifier-only labels. These are conditional stage observations, not full model-built pipelines or held-out calibration.')
    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' 'The completed repository supporting batch used six environment-qualified cases in Luigi, Matplotlib and pandas, with one attempt per deployment and 18 planned pairs. Candidate images contained buggy production packages but no fixed tree, gold patch, repository history or protected tests. Investigators localized allowed files using public APIs and buggy tracebacks. Exact edits were converted to guarded patches. Verified repairs passed the visible test and 53 case-specific withheld public regression identities, then repeated those checks in fresh containers. The regression tests were public, not novel hidden tests; they were not all run against every repair.')
    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' 'The next ML calibration was frozen before calls at 24 new task specifications, four stages and three dated deployments, or 288 first attempts (12 specifications per corpus and stage). Feature subsets are held out from earlier study tasks, but source corpora and row splits are reused. Thus the design has two corpus clusters, not 24 independent datasets or a raw-data holdout. Stage-specific observations and uncertainty must precede profile freezing; brand, price or release date cannot assign Ability Ranks. We do not fit difficulty-specific coefficients without difficulty variation and label provenance.')
    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' 'The original Central-Fit contrast changes both the considered candidate pairs and assignment rule. The older Central-Matched simulation retains local proposals and adds a coordinator relay; it isolates an extra coordination path, not who computes every choice. The new CENTRAL_RULE_MATCHED control moves the same pure choice function to one coordinator while CF-Fit computes it in agent processes. Separate-process parity and shared SQLite-claim invariants pass fixture checks, but their live allocation comparison remains unfinished. The shared belt and claim store remain common failure dependencies.')
    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' 'Probability provenance remains explicit. The original simulation success curve and arrival process are scenario assumptions with documented internal range checks and sensitivity analyses, not probabilities estimated from provider executions. The supporting pilot and ongoing calibration cannot retroactively validate the 22,500 simulation runs as empirically fitted real-LLM behavior. Main profiles will be frozen from completed calibration with failed and unresolved observations retained.')
    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' ((Find-Paragraph $taskFigDoc 'Probability parameter provenance.').Text.Trim()))
    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' 'Figure 1 describes the original simulation and microtask allocation engines. The new container-based ML-stage and repository studies use supporting execution harnesses, not a shared executable core inherited from that drawing. The paired live allocation backend still needs end-to-end integration; completed supporting verifier observations cannot be substituted for that main experiment.')
    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' 'The new repository calibration freezes six different cases from an outcome-blind environment pool, giving 18 first-attempt pairs across three deployments. Each case has ten fixed, case-specific public regression identities. Before model calls, all six candidate environments passed source hashes, no-op reproduction and an import-sentinel test. Matplotlib case 10 needed pinned pandas and pytz dependencies to activate two skipped tests; the same ten test identities then passed both buggy and fixed baselines. A separate context amendment added public formatter-method excerpts before calls. Neither instrument amendment is a model observation, and no gold patch was used to select editable source.')
    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' 'Cost units are kept separate from billing claims. The original MFEC microtask study and new executable studies use the reported x-litellm-response-cost values. Their currency has not been independently confirmed, so live-study cost figures are provider-reported units, not confirmed US dollars or invoiced payments. Simulation costs remain the declared scenario resource units. Relative contrasts retain their original numeric values; they do not establish a monetary saving in a confirmed currency.')
    [void](Insert-Paragraph $taskDoc 'VI. RESULTS' 'The ecological ML sandbox also imposes a frozen 256 MiB file-size limit. CPU, memory and execution time were stated in the prompt, but this file limit was not explicitly stated. One Beijing train attempt reached that limit while serializing its estimator and remains a stage-contract failure. Such failures measure operational fulfillment under this artifact budget, not intrinsic regression ability. The running batch is unchanged; future main prompts must disclose all resource limits before outcomes. Selective reruns or investigator code repairs are not used to promote failed observations.')
    # Historical numeric values are retained, but unsupported dollar labels
    # must not survive in the body or tables. Figure images are untouched.
    $taskDollar=$taskDoc.Content.Duplicate
    $taskDollar.Find.ClearFormatting();$taskDollar.Find.Replacement.ClearFormatting()
    $taskDollar.Find.Text='$';$taskDollar.Find.Replacement.Text='';$taskDollar.Find.Wrap=0
    $taskDollar.Find.MatchWildcards=$false
    [void]$taskDollar.Find.Execute('$',$false,$false,$false,$false,$false,$true,0,$false,'',2)

    [void](Insert-Paragraph $taskDoc 'VII. DISCUSSION' 'J. Supporting Executable ML Results' -3)
    [void](Insert-Paragraph $taskDoc 'VII. DISCUSSION' 'The isolated-stage pilot completed all 36 pairs: 28 verified, six generation or stage-contract failures, and two unresolved provider requests. Table IX reports each deployment. A verified observation passed its frozen stage contract and fresh replay. Two corpora, three reused specifications and dependent stages limit inference; these counts do not rank general model ability or compare allocation policies.')
    $rows=@();$rows+=,@('Deployment','N','Verified','Unresolved')
    foreach($m in $taskML.models){$u=0;if($null -ne $m.outcomes.PSObject.Properties['PROVIDER_UNRESOLVED']){$u=[int]$m.outcomes.PROVIDER_UNRESOLVED};$rows+=,@($m.model_alias,[string]$m.planned_pairs,[string]$m.verified,[string]$u)}
    Insert-Table $taskDoc 'TABLE IX. ISOLATED ML STAGE OBSERVATIONS' $rows
    [void](Insert-Paragraph $taskDoc 'VII. DISCUSSION' 'The 34 returned responses reported 77,899 input tokens and 372,642 output tokens, with 0.250668134 provider-reported cost units. Two request billing outcomes remain unknown. The currency is unconfirmed; this is not total billed cost and is not labelled US dollars. Failed and unresolved pairs are retained, without investigator repairs or model retries.')
    [void](Insert-Paragraph $taskDoc 'VII. DISCUSSION' 'K. Supporting Repository Repair Results' -3)
    [void](Insert-Paragraph $taskDoc 'VII. DISCUSSION' 'All 18 new-case pairs completed. Tencent verified four of six repairs, GPT one of six and GLM two of six; one GLM request was unresolved. Table X retains that outcome separately. Differences can reflect localized source context, output compliance and deployment conditions as well as repair skill. Six cases and three repository clusters do not support a population-wide ability ranking or a difficulty-specific success curve.')
    $rows=@();$rows+=,@('Deployment','N','Verified','Unresolved')
    foreach($m in $taskRepo.cells){$rows+=,@($m.model_alias,[string]$m.planned_pairs,[string]$m.verified,[string]$m.unresolved)}
    Insert-Table $taskDoc 'TABLE X. FIRST ATTEMPT LOCALIZED REPAIRS' $rows
    [void](Insert-Paragraph $taskDoc 'VII. DISCUSSION' 'The 17 returned responses reported 223,970 input tokens and 223,724 output tokens, with 0.199841350 provider-reported cost units. One unresolved request has unknown billing. These results show bounded executable repairs under this contract, not autonomous repository-wide repair or an allocation-policy advantage. The separate ecological ML calibration started on 6 October 2026 and is still running in this progress revision. No partial calibration counts are treated as a final result.')
    if($null -ne $taskNewRepo){
        [void](Insert-Paragraph $taskDoc 'VII. DISCUSSION' 'L. Completed Repository Calibration' -3)
        $taskTotal=$taskNewRepo.total
        [void](Insert-Paragraph $taskDoc 'VII. DISCUSSION' ("The separate ecological repository calibration completed all 18 first-attempt pairs on six different cases: $($taskTotal.verified) verified, $($taskTotal.model_failed) model failures and $($taskTotal.unresolved) unresolved outcomes. Table XI reports deployment counts. The cases were selected from an outcome-blind environment pool, not from model successes, and are not pooled with the supporting batch in Table X."))
        $rows=@();$rows+=,@('Deployment','N','Verified','Unresolved')
        foreach($m in $taskNewRepo.models){$rows+=,@($m.alias,[string]$m.planned_and_completed,[string]$m.verified,[string]$m.unresolved)}
        Insert-Table $taskDoc 'TABLE XI. ECOLOGICAL REPOSITORY CALIBRATION' $rows
        $taskAccounts=$taskNewRepo.accounting
        [void](Insert-Paragraph $taskDoc 'VII. DISCUSSION' ("Returned responses recorded $($taskAccounts.observed_input_tokens) input tokens, $($taskAccounts.observed_output_tokens) output tokens and $([string]::Format([Globalization.CultureInfo]::InvariantCulture,'{0:F9}',$taskAccounts.observed_provider_cost_units)) provider cost units. Billing remains unknown for $($taskAccounts.provider_unresolved_billable_outcomes) provider-unresolved requests. The operational denominator retains every planned pair, including failures and unresolved requests. Source files were investigator-localized, and verification used ten case-specific public regressions and fresh replay. With two cases per repository and deployment, nominal Wilson intervals are descriptive binomial references, not uncertainty estimates for a general repository population. The report assigns no Ability Ranks and fits no difficulty-specific success curve. ML calibration and paired live allocation main remain incomplete."))
    }
    [void](Insert-Paragraph $taskDoc 'REFERENCES' 'AUTHOR CONTRIBUTIONS' -3)
    [void](Insert-Paragraph $taskDoc 'REFERENCES' 'Sakan Punyanon: investigation, software, validation, formal analysis, visualization and original draft. Chaiyaporn Khemapatapan: conceptualization, methodology and supervision. Aomduan Jeamaon: conceptualization, experimental design, supervision and manuscript review. The authors should confirm the final contribution wording before submission.')
    [void](Insert-Paragraph $taskDoc 'REFERENCES' 'FUNDING AND CONFLICTS OF INTEREST' -3)
    [void](Insert-Paragraph $taskDoc 'REFERENCES' 'The research received no external research funding and was self-funded by the first author. Dhurakij Pundit University supports the article processing charges. The authors declare no conflicts of interest.')
    [void](Insert-Paragraph $taskDoc 'REFERENCES' 'Code and editable diagrams are available at https://github.com/sakanarm/ConveyorFlowExperimental. API credentials, raw provider responses, heavy data and model artifacts, and working Office drafts are not committed. The reproducibility guide records dated code-test counts and integration checks requiring prepared data or the external benchmark. Code tests do not constitute live-model results. Historical audits additionally require dated investigator capsules.')
    Replace-Paragraph $taskDoc 'The v2 research package contains' 'The public repository provides experimental source, frozen configurations, public-data manifests, annotation protocols, analysis utilities, editable diagrams and the v2.3 code/contract checks. Detailed dated provider and execution capsules are retained by the investigators; raw responses and heavy artifacts are not all committed. Historical hash audits require those capsules, whereas a new reviewer run records its own provider date, image identity and outputs. Upstream datasets and benchmarks remain subject to their licenses. Provider aliases and prices are observed metadata, not independently verified immutable model lineage. An archival DOI will be added only after a release exists.'
    $taskExpectedTables=if($null -ne $taskNewRepo){11}else{10}
    if($taskDoc.InlineShapes.Count -ne 15 -or $taskDoc.OMaths.Count -ne 13 -or $taskDoc.Tables.Count -ne $taskExpectedTables){throw 'Figure/equation/table preservation failed'}
    # Keep every figure with its caption; no half-caption on the next page.
    for($n=1;$n -le 15;$n++){
        $taskCaption=Find-Paragraph $taskDoc "Fig. $n."
        $taskCaption.ParagraphFormat.KeepTogether=-1
        $taskPicture=Nearest-Figure $taskDoc $taskCaption
        $taskPicture.Range.ParagraphFormat.KeepWithNext=-1
        if($n -eq 1 -and $taskPicture.Height -gt 290){$taskPicture.LockAspectRatio=-1;$taskPicture.Height=290}
    }
    # This isolated figure section previously balanced picture/caption into
    # opposite columns. Give the figure its own full-width section and keep
    # the image/caption together without deleting either section boundary.
    foreach($taskFigureNumber in @(6,9)){
        $taskCaption=Find-Paragraph $taskDoc "Fig. $taskFigureNumber."
        $taskPicture=Nearest-Figure $taskDoc $taskCaption
        $taskPicture.Range.Sections.Item(1).PageSetup.TextColumns.SetCount(1)
        $taskBreak=$taskPicture.Range.Paragraphs.Item(1).Range.End-1
        if($taskCaption.Start -ne $taskBreak+1){throw "Fig. $taskFigureNumber caption adjacency changed"}
        $taskDoc.Range($taskBreak,$taskBreak+1).Text=[string][char]11
        $taskBlock=$taskPicture.Range.Paragraphs.Item(1).Range
        $taskBlock.ParagraphFormat.KeepTogether=-1;$taskBlock.ParagraphFormat.KeepWithNext=0
        $taskBlock.ParagraphFormat.Alignment=1
    }
    # A table caption must travel with the first row, including older tables.
    foreach($taskParagraph in $taskDoc.Paragraphs){
        if($taskParagraph.Range.Text.StartsWith('TABLE ')){
            $taskParagraph.Range.ParagraphFormat.KeepWithNext=-1
            $taskParagraph.Range.ParagraphFormat.KeepTogether=-1
        }
    }
    [void]$taskDoc.Fields.Update();$taskDoc.Repaginate();$taskDoc.Save()
    $taskPageCount=$taskDoc.ComputeStatistics(2)
    $taskDoc.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc);$taskDoc=$null
    # Word authored all manuscript content. Its metadata COM interface is not
    # exposed by this installation; update only core properties in the closed
    # package, leaving document.xml, media, equations and layout unchanged.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    Add-Type -AssemblyName System.IO.Compression
    $taskZip=[IO.Compression.ZipFile]::Open($taskCopy,[IO.Compression.ZipArchiveMode]::Update)
    try{
        $taskEntry=$taskZip.GetEntry('docProps/core.xml')
        $taskReader=[IO.StreamReader]::new($taskEntry.Open());[xml]$taskCore=$taskReader.ReadToEnd();$taskReader.Dispose()
        $taskNs=[Xml.XmlNamespaceManager]::new($taskCore.NameTable)
        $taskNs.AddNamespace('cp','http://schemas.openxmlformats.org/package/2006/metadata/core-properties')
        $taskNs.AddNamespace('dc','http://purl.org/dc/elements/1.1/')
        foreach($taskSpec in @(@('creator','Sakan Punyanon; Chaiyaporn Khemapatapan; Aomduan Jeamaon'),
                               @('title','ConveyorFlow decentralized capability aware self selection for heterogeneous LLM agent teams'))){
            $taskNode=$taskCore.SelectSingleNode('/cp:coreProperties/dc:'+$taskSpec[0],$taskNs)
            if($null -eq $taskNode){$taskNode=$taskCore.CreateElement('dc',$taskSpec[0],'http://purl.org/dc/elements/1.1/');[void]$taskCore.DocumentElement.AppendChild($taskNode)}
            $taskNode.InnerText=$taskSpec[1]
        }
        $taskLast=$taskCore.SelectSingleNode('/cp:coreProperties/cp:lastModifiedBy',$taskNs)
        if($null -ne $taskLast){$taskLast.InnerText='Sakan Punyanon'}
        $taskEntry.Delete();$taskNewEntry=$taskZip.CreateEntry('docProps/core.xml')
        $taskStream=$taskNewEntry.Open();$taskCore.Save($taskStream);$taskStream.Dispose()
    }finally{$taskZip.Dispose()}
    Copy-Item -LiteralPath $taskCopy -Destination $taskOutput
    if((Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash -ne $taskSourceHash -or
       (Get-FileHash -LiteralPath $taskFigures -Algorithm SHA256).Hash -ne $taskFigureHash){throw 'Source manuscript changed'}
    [PSCustomObject]@{output=$taskOutput;authoring='Microsoft Word';source_sha256=$taskSourceHash;
        figures=15;native_equations=13;tables=$taskExpectedTables;pages=$taskPageCount;
        ecological_calibration='running_not_final';allocation_main='not_completed';visual_QA_required=$true} | ConvertTo-Json
}finally{
    if($null -ne $taskFigDoc){$taskFigDoc.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskFigDoc)}
    if($null -ne $taskDoc){$taskDoc.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc)}
    if($null -ne $taskApp){$taskApp.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskApp)}
}
