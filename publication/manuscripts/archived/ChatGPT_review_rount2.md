LLM4AE Manuscript Revision Plan — Issue Audit and Required Corrections

Purpose: This document consolidates the issues identified in the current revised manuscript_revision_plan(1).md and reviewer_response_materials(1).md so that the next revision-plan update can be made systematically before rewriting the manuscript and point-by-point response.

Review perspective: Drug Safety / pharmacovigilance methods manuscript; emphasis on methodological defensibility, reviewer-comment closure, statistical accuracy, reproducibility, and avoiding optimistic overstatement.

Current fixed constraints (do not plan around changing these):

The original FAERS dataset / curated reference dataset cannot be publicly released. This is a data-governance constraint and should be handled transparently in the manuscript and response letter rather than treated as something to be “solved” by public release.

A second independent annotator / formal IAA study cannot be added. The revision must therefore acknowledge this limitation directly and strengthen transparency and QA documentation without implying that internal QA is equivalent to inter-annotator agreement.

Executive assessment

The current revision strategy is substantially stronger than the earlier version. In particular, the following changes materially improve the manuscript:

BioBERT evaluation has been expanded from a single 80/20 experiment to 10-fold cross-validation with 5 random seeds.

FAERS now includes leave-one-drug–AE-pair-out cross-case-series evaluation with 5 seeds, directly addressing the limited four-case-series composition of the FAERS corpus.

The previous relaxed Scheme 1 has been removed from the primary analysis, leaving strict exact-match NER as the primary endpoint and a weighted pharmacovigilance-oriented metric as secondary.

The terminology around ordinary false positives has been improved by removing routine use of “hallucination.”

Prompt documentation, a second LLM, VAERS supplementary material, and error analyses have all been expanded.

With the two fixed constraints above, no additional large model-training experiment is currently mandatory. However, the current two planning documents still contain several statistical, methodological, and factual inconsistencies that should be corrected before they are used to rewrite the manuscript or reviewer response.

The highest-priority problems are:

public-data claims contradict the actual data constraint;

LOO confidence intervals are mathematically inconsistent with the reported means;

the reported “1.75% relative” generalization gap is incorrectly described;

single-annotator QA language currently overstates what can be demonstrated without IAA;

annotation provenance creates a potential pre-annotation anchoring issue that should be acknowledged;

seed/fold/case-series variability are mixed together in current summary language;

the BioBERT model-selection rationale is not yet methodologically clean;

the modified ADE-Eval metric must be named and implemented precisely;

taxonomy/schema mapping and filtering rules need a consistency audit;

several results statements remain more optimistic than the data support.

Priority 0 — Must be corrected before the next revision plan is considered stable

P0.1 — Remove all claims that the original dataset / dataset.db will be publicly released

Current problem

The current revision plan states in the Abstract section that the unified SQLite database containing 1,829 reports and annotations will be publicly released. The reviewer-response document similarly states that the complete database containing raw narratives and annotations has been made publicly accessible and uses public release as part of the response to both the single-annotator concern and Reviewer #2’s data-availability concern.

These statements are incompatible with the actual data constraint: the original dataset cannot be made public.

Affected locations include at least:

manuscript_revision_plan(1).md — Abstract modifications;

manuscript_revision_plan(1).md — Section 2.2, Single-Annotator QA Framework, pillar 5;

reviewer_response_materials(1).md — Reviewer 2.W1, “Open-Source Release for Community Adjudication”;

reviewer_response_materials(1).md — Reviewer 2.W3, Public Corpus Availability;

any future Data and Code Availability section derived from these documents.

Required change

Replace the public-release strategy with a transparent restricted-data strategy.

The revised plan should explicitly distinguish:

data that cannot be released: original FAERS narratives and/or the curated reference dataset, according to the actual institutional/data-governance restriction;

materials that can be released, if permitted: source code, scoring scripts, prompt templates, annotation guidelines, schema definitions, aggregate statistics, environment/configuration files, and possibly non-sensitive derived artifacts;

access language: only use “available upon reasonable request” if that is genuinely permitted. Do not add this phrase automatically.

Recommended reviewer-response framing for Reviewer 2.W3

Use a response along the following logic:

We agree that public availability would increase the reuse potential of the corpus. However, the underlying FAERS narratives and the curated reference dataset used in this study cannot be redistributed publicly under the applicable institutional/data-governance constraints. We have revised the manuscript to state this limitation explicitly and have removed wording implying that the corpus itself is openly reusable. To maximize reproducibility within these constraints, we provide the annotation schema/guidelines, complete model prompts, scoring methodology, code, and aggregate corpus statistics [only list items that are actually released].

Manuscript implication

Avoid claims such as:

“public benchmark dataset”;

“open benchmark corpus”;

“publicly released reference corpus”;

“community adjudication of the complete data.”

Safer wording:

“expert-curated reference corpus”;

“reference benchmark used in this study”;

“a benchmark resource for evaluating clinical concept extraction under the study’s data-access constraints.”

Important note

Non-public data availability by itself does not invalidate the study. The risk comes from inconsistency between the actual access status and claims in the manuscript/response letter.

P0.2 — Recalculate the LOO 95% confidence intervals

Current problem

The revision plan currently reports:

Strict LOO: 0.5930 ± 0.0542, 95% CI [0.5758, 0.5921]

ADE-weighted LOO: 0.7463 ± 0.0298, 95% CI [0.7543, 0.7649]

These intervals are internally impossible:

the strict CI does not contain the reported mean of 0.5930;

the ADE-weighted CI lies entirely above the reported mean of 0.7463.

This is a submission-blocking numerical issue because a reviewer can identify it immediately.

Required change

Recompute the CIs directly from the underlying result files and document exactly what the statistical unit is.

Before calculating the CI, decide what uncertainty the interval is intended to represent:

between-document uncertainty — preferably document-level bootstrap;

between-held-out-case-series uncertainty — only four LOO domains, so uncertainty will be wide;

random-seed variability — five repeated trainings within each fold;

combined fold × seed variability — should not be treated as 20 fully independent observations without justification.

Do not simply pool the 4 folds × 5 seeds as 20 independent samples unless the statistical interpretation is explicitly justified.

Recommended reporting approach

For the main text, one defensible approach is:

report the four held-out case-series results individually;

report their mean as a descriptive cross-case-series summary;

report seed SD within each held-out series;

if a CI is needed for model comparison, use a clearly described document-level paired bootstrap based on held-out predictions.

If no valid CI analysis is available, it is better to omit the CI than report an incorrect one.

P0.3 — Correct the “1.75% relative generalization gap” statement

Current problem

The current plan states that the LOO transfer gap is “only 1.75% relative to 10-fold CV.”

Using the currently reported means:

Strict: 0.6099 − 0.5930 = 0.0169 absolute F1

ADE-weighted: 0.7638 − 0.7463 = 0.0175 absolute F1

The relative decreases are approximately:

Strict: 0.0169 / 0.6099 ≈ 2.77% relative

ADE-weighted: 0.0175 / 0.7638 ≈ 2.29% relative

Thus, 1.75% is not a correct relative decline. It corresponds approximately to an absolute F1 difference of 0.0175, i.e. 1.75 percentage points on a 0–1 scale.

Required change

Prefer avoiding percentage language entirely:

Compared with random 10-fold cross-validation, mean leave-one-pair-out performance decreased by 0.0169 in strict F1 and 0.0175 in the weighted F1 metric.

This is clearer and avoids ambiguity between absolute and relative change.

P0.4 — Do not describe cross-case-series LOO as proving “minimal OOD decay”

Current problem

The plan currently interprets the LOO experiment as demonstrating minimal out-of-distribution decay.

However, the four held-out series are heterogeneous:

Azacitidine–QT: strict 0.6280

Baricitinib–hypersensitivity: strict 0.6563

Tramadol–hypoglycemia: strict 0.5602

Erenumab–stroke: strict 0.5274

The average degradation is modest, but the results also show meaningful variation by held-out case series.

Further, this is not a fully independent external OOD dataset: all cases remain within the same FAERS study corpus, annotation framework, and broader source domain.

Required change

Rename the analysis and moderate the interpretation.

Preferred terminology:

“Leave-One-Drug–Event-Pair-Out Cross-Case-Series Evaluation”

“Cross-Case-Series Generalization”

“distribution-shift evaluation across held-out drug–event case series”

Recommended interpretation:

Performance was broadly preserved across held-out drug–event case series, although the magnitude of transfer varied by case series.

Avoid:

“strong OOD generalization”;

“minimal OOD decay”;

“external validation.”

P0.5 — Rewrite the single-annotator response so QA is not presented as a substitute for IAA

Current problem

The current response uses a “5-pillar QA framework,” including “near-perfect closed-vocabulary extraction” and public community adjudication, to respond to Reviewer #2’s request for a second annotator / IAA.

Two problems remain:

internal QA is not equivalent to independent inter-annotator agreement;

public community adjudication is not possible if the original dataset cannot be released.

The current wording risks sounding defensive or as if the methodological limitation has been fully eliminated.

Required change

The response should explicitly state that formal IAA was not obtained and cannot be retrospectively substituted by internal checks.

Recommended structure:

agree that dual annotation and IAA would provide stronger validation;

state that independent double annotation was not feasible within the study;

do not claim equivalence between QA and IAA;

describe the actual safeguards:

annotator clinical qualification;

task-specific calibration;

detailed operational guidelines;

full-narrative review rather than review of model proposals only;

iterative/multi-pass verification if this actually occurred;

transparent limitation statement;

reframe the dataset as an expert-curated reference corpus, not an independently adjudicated gold standard.

Suggested response language

We agree that independent dual annotation and formal inter-annotator agreement would provide a stronger assessment of annotation reliability. An independent second annotation set sufficient for formal IAA analysis was not feasible within the scope of this study. We therefore do not present our quality-control procedures as equivalent to independently adjudicated dual annotation. Instead, we strengthened transparency and annotation consistency through explicit operational guidelines, clinical annotator qualification and calibration, full-narrative review, and documented multi-pass verification. We now refer to the resource as an expert-curated reference corpus and explicitly identify the absence of independent IAA as a limitation.

Remove or revise

“Open Community Adjudication” based on public release;

“5-pillar QA” if it sounds like a formal validation framework unsupported by an external reference;

any wording implying that the single-annotator concern has been empirically “resolved.”

P0.6 — Reconsider “near-perfect consistency” claims for AGE/SEX/DOSE

Current problem

The revision plan states that deterministic multi-pass verification demonstrated “near-perfect consistency on closed-vocabulary structural entities (AGE, SEX, DOSE).”

This does not directly address the categories where annotation ambiguity is most consequential, such as AE/DX/MHX/LAB/STATUS. In addition, DOSE is not naturally described as a closed vocabulary in the same sense as SEX and perhaps AGE patterns.

The phrase also raises an immediate question: consistency against what independent standard?

Required change

Unless there is a clearly defined, separately computed validation analysis, remove “verified near-perfect” from the reviewer response.

If such an audit exists, describe it precisely:

what was compared;

what denominator was used;

whether it was deterministic pattern validation, re-review agreement, or something else;

why it is relevant.

Do not use it as evidence equivalent to IAA.

P0.7 — Align the annotation provenance everywhere and acknowledge potential pre-annotation anchoring

Current problem

The current revised documents now state that the human reference annotations were produced through:

LLM candidate/pre-tag generation;

human review of the proposed spans;

boundary correction, relabeling, deletion;

addition of missed entities.

This is a major improvement over the old manuscript’s contradictory claim that annotation was entirely manual without AI assistance.

However, this workflow creates a potential pre-annotation anchoring / incorporation bias concern, particularly because an LLM is later evaluated against the human-corrected reference annotations.

Required change

Methods should clearly state that the annotator reviewed the entire narrative, not only the model-proposed spans, and could add entities de novo.

Limitations should add a concise statement such as:

Because model-generated candidate spans were displayed during annotation, pre-annotation anchoring cannot be completely excluded despite full-narrative human review and manual addition of missed entities.

Optional high-value analysis if existing logs permit it

If version-control history already contains the necessary information, calculate the proportion of initial pre-annotations that were:

accepted unchanged;

boundary-modified;

relabeled;

deleted;

newly added by the human annotator.

This is not required if logs are unavailable, but it would be a stronger and more directly relevant QA analysis than model-consensus comparisons or claims about closed-vocabulary entities.

Do not reconstruct these statistics retrospectively if the audit trail does not support them.

P0.8 — Clarify exactly how 10-fold CV × 5 seeds was performed and summarized

Current problem

The plan states “stratified 10-fold cross-validation (80% train, 10% dev, 10% test per fold) repeated across 5 seeds.” This needs a precise operational description.

Questions that must be unambiguous:

Is the test fold fixed across seeds?

Does every report serve as test exactly once per seed?

How is the 10% development set selected from the remaining 90%?

Are train/dev/test partitions identical across the five seeds, with only initialization/training stochasticity changed?

What does “stratified” mean for multi-label narrative data?

Are duplicate/follow-up reports grouped to prevent leakage across partitions, if such related reports exist?

Required change

Document the actual algorithm rather than only the percentages.

A clean description, if accurate, would look like:

The corpus was divided into 10 fixed outer folds. In each outer iteration, one fold (10%) was held out for testing. The remaining 90% was split into training and development partitions, yielding approximately 80% training and 10% development data. The outer folds and train/development assignments were fixed across the five random seeds so that seed replication measured optimization variability rather than resampling variability.

Only use this wording if it reflects the actual implementation.

P0.9 — Separate random-seed variability from fold/case-series variability

Current problem

The reviewer-response document says:

“Across all folds, stochastic optimization variance remained low (SD ≤ 0.019), demonstrating strong stability.”

Yet the overall LOO strict result is reported as 0.5930 ± 0.0542.

These numbers may both be valid if the larger SD reflects between-case-series heterogeneity and the smaller SD reflects within-fold seed variation, but the current wording does not explain this distinction.

Required change

Report the two sources of variation separately:

within-fold / within-case-series seed SD;

between-fold / between-case-series variation.

A stronger scientific interpretation is:

Optimization-related seed variability was relatively small within each held-out case series, whereas performance variation across held-out drug–event pairs was larger, indicating that case-series/domain heterogeneity contributed more variability than random initialization.

Only make this claim after confirming the corresponding statistics.

Also audit the meaning of all reported “mean ± SD” values

Do not mix:

SD across 50 CV runs;

SD across 10 fold-level pooled metrics;

SD across 5 seed-level pooled out-of-fold metrics;

SD across four LOO series.

The manuscript table footnotes should define the aggregation unit explicitly.

P0.10 — “Paired bootstrap 95% CI” is claimed but not yet documented

Current problem

Reviewer 2.W1 response states that the evaluation was expanded to include “paired bootstrap 95% confidence intervals,” but the revision plan does not specify the bootstrap method or give the corresponding comparison results.

This creates a risk of claiming an analysis that has not actually been finalized.

Required change

Choose one of two paths:

Path A — implement and document it

Specify:

resampling unit (document/report, not entity token unless justified);

number of bootstrap replicates;

paired resampling across models;

which comparisons are tested;

whether CIs are for F1 itself or ΔF1 between systems.

Path B — remove the claim

If paired bootstrap has not been performed, remove it from the reviewer response and do not say “significantly outperformed” unless a statistical comparison is actually available.

P0.11 — BioBERT model-selection rationale must be historically and statistically accurate

Current problem

The new documents use two different framings:

“BioBERT a priori selection rationale”;

“BioBERT was selected based on superior tokenization fidelity for chemical and pharmacological entity stems.”

The earlier manuscript described an empirical ablation among BERT variants on VAERS. Therefore, the new wording risks retroactively reframing an empirical model-selection step as “a priori.”

Also, “superior tokenization fidelity” should not be claimed unless this was actually measured.

Required change

First establish the real provenance of model selection:

Was BioBERT selected before the final experiments based on domain relevance?

Was it selected using an exploratory VAERS comparison?

Did that comparison use a development set or the final evaluation data?

Then write the exact truth.

If the previous ablation used final evaluation data

Do not use that ablation to justify an unbiased final-test model selection. Possible defensible options include:

present the ablation as exploratory only;

state that BioBERT was fixed as the principal encoder based on biomedical pretraining/domain suitability, not on the final test outcome;

if necessary, rerun only the model-selection comparison on development data, but this should be done only if required by the actual experimental history.

Avoid unsupported language

Delete “superior tokenization fidelity” unless a specific tokenization analysis exists.

P0.12 — Validate the weighted metric against ADE-Eval before calling it “ADE-Eval”

Current problem

The updated metric now defines:

C_boundary: overlapping same-label boundary mismatch;

C_class: overlapping mention with class mismatch;

S_non_overlap: zero-overlap false positive;

C receives 0.5 credit;

S receives 0.25 denominator weight.

This is conceptually closer to the published ADE-Eval framework than the earlier version, but the manuscript must ensure that the matching/pairing algorithm is also compatible.

A major unresolved issue is one-to-one matching when:

one predicted span overlaps multiple gold entities;

multiple predictions overlap one gold entity;

spans overlap with different labels.

The formula alone does not define the matching algorithm.

Required change

Audit the scorer and document:

one-to-one pairing rule;

precedence of exact match over partial match;

handling of multiple overlaps;

handling of class mismatch;

how unmatched gold and unmatched predictions are assigned to N and S.

Naming rule

If the implementation is not an exact reproduction of published ADE-Eval matching and weighting, call it:

“adapted ADE-Eval weighted mention metric”

or

“ADE-Eval–inspired weighted mention metric.”

Do not call it simply “ADE-Eval” unless the implementation is demonstrably aligned.

Primary metric naming

Instead of “Standard CoNLL/SemEval” unless a specific official scorer is used, the safest manuscript wording is:

strict exact-span, exact-label micro-averaged entity F1.

This states exactly what was measured without unnecessary benchmark-name claims.

P0.13 — The new C definition is inconsistent with the current error-analysis wording

Current problem

Section 2.4 now defines:

C_total = C_boundary + C_class

But Section 3.4 still says:

“Category C Granularity: Mean IoU … 85–90% of C mismatches are superphrase context extensions.”

If C_total includes class-confusion errors, then an IoU-based “superphrase” statement logically applies only to C_boundary, not all C errors.

Required change

Split the analysis explicitly:

Boundary errors (C_boundary) → IoU distribution, over-span vs under-span, superphrase/subphrase analysis;

Class errors (C_class) → label-confusion matrix;

Non-overlap errors (S_non_overlap) → false-positive taxonomy.

All figures, captions, and text should use these exact names consistently.

P0.14 — Resolve the contradiction between schema filtering and “schema overflow” false positives

Current problem

The plan says:

non-gold categories (e.g., TEMPORAL/DOSE/AGE/SEX in VAERS) are filtered before scoring rather than counted as false positives.

But the error analysis says 20% of S_non_overlap errors are “schema overflow.”

If out-of-schema outputs are filtered before scoring, it is unclear how schema overflow remains part of the scored S category.

Required change

Define two separate concepts:

Main-task scoring errors within the corpus-specific target schema;

schema-violation outputs outside the target schema.

Recommended handling:

main P/R/F1 is computed only over the pre-specified target schema;

out-of-schema predictions are not silently treated as standard NER FPs if the task definition excludes them;

however, report the number/rate of schema violations separately, because this is operationally relevant for LLM reliability.

Do not classify an output simultaneously as “filtered out” and as part of the scored false-positive count.

P0.15 — Audit the 17-category → normalized-category taxonomy before final tables are produced

Current problem

The current documents contain several schema counts/labels that require reconciliation:

FAERS is described as having 17 functional categories;

the main evaluation is described as an 11-category table;

older versions referred to 10 major categories;

TEMPORAL appears in the new per-category results;

the original category list included labels such as DATE and role-specific drug categories;

VAERS has its own separate schema and filtered categories.

Without a single canonical mapping table, there is a risk that Tables 1–4, prompts, scoring scripts, and Supplement S1/S2 use slightly different label sets.

Required change

Create one canonical taxonomy mapping artifact before manuscript drafting, containing at least:

Corpus

Raw annotation label

Definition

Normalized evaluation label

Included in main scoring?

Notes

Then automatically reconcile:

raw annotation counts;

normalized counts;

gold totals used by scorer;

category names in figures;

tag names in prompts;

category names in Methods/Results/Supplement.

No manuscript table should be manually assembled from a different label mapping.

Priority 1 — Important for a strong Drug Safety resubmission

P1.1 — Tone down the INDICATION interpretation

Current problem

The plan says:

BioBERT “collapses” on INDICATION;

the LLMs “maintain robust semantic capture” at F1 ≈ 0.37–0.38.

The relative comparison is interesting, but absolute LLM performance remains modest.

Required change

Use neutral wording such as:

For the sparse INDICATION category, both LLMs achieved higher F1 than BioBERT, although absolute performance remained modest.

Possible interpretation:

This pattern is consistent with a potential advantage of in-context semantic priors for very sparse categories, but the small number of reference instances limits strong conclusions.

Avoid “robust” or “strong” unless supported by both absolute performance and uncertainty estimates.

P1.2 — Report full output-format performance, not only the favorable components

Current problem

The XML-vs-JSON result currently highlights:

46.52% fewer non-overlap false positives with JSON;

11.26% higher recall with tagged XML.

This is useful but incomplete and could appear selective.

Required change

Table 5 should show, for both output formats:

strict precision;

strict recall;

strict F1;

adapted ADE-weighted precision;

adapted ADE-weighted recall;

adapted ADE-weighted F1;

exact match M;

boundary C;

class C;

non-overlap S;

N;

invalid-format rate / parsing failure rate if available.

Then the narrative can fairly describe the precision–recall trade-off.

Also confirm that XML vs JSON comparisons used the same:

model/version;

cases;

model parameters;

semantic instructions/examples, except for output representation;

scoring code.

P1.3 — Respond directly to Reviewer 3.22 on BERT probability thresholding

Current problem

The response currently says that the two-tier metric evaluates different penalty regimes. That does not directly answer the reviewer’s suggestion about BERT token/span confidence thresholding.

Required change

No new threshold experiment is necessarily required. A direct response is preferable:

We agree that confidence-threshold calibration could provide an additional deployment-specific precision–recall operating-point analysis. We did not optimize the decoding threshold post hoc on the evaluation set because our primary objective was model comparison under a fixed pre-specified inference procedure. We have added threshold calibration as a limitation and future deployment-oriented direction.

Do not imply that metric weighting is equivalent to model probability calibration.

P1.4 — Use exact model identifiers and inference settings for LLM reproducibility

Current problem

The plan uses general names such as Claude 4.6 Sonnet and llama-4-maverick, while the old manuscript used a more specific LLaMA model string.

API-hosted and open-weight model results are difficult to reproduce without complete model/configuration metadata.

Required change

For each LLM report:

exact model identifier/version available at the time of inference;

provider/serving environment;

inference date or model snapshot if relevant;

temperature;

top-p/top-k if applicable;

max output tokens;

system prompt and user prompt structure;

number of demonstrations;

retry policy;

parsing/repair logic;

whether outputs were generated once or repeatedly.

Do not use marketing terms such as “frontier” unless necessary.

P1.5 — Ensure cross-corpus conclusions do not imply that both LLMs were evaluated on VAERS

Current issue

The revised FAERS benchmark includes Claude Sonnet and LLaMA 4, whereas the VAERS benchmark listed in the plan includes BioBERT and LLaMA 4 but not Sonnet.

Required change

When discussing “LLMs” across both FAERS and VAERS, distinguish:

FAERS: two instruction-tuned LLMs;

VAERS: LLaMA 4 comparison only, unless Sonnet VAERS experiments are actually available.

Avoid a sentence implying that the same multi-LLM finding was independently reproduced on VAERS when only one LLM was tested there.

P1.6 — The ETHER comparison should distinguish task coverage from head-to-head extraction accuracy

Current issue

ETHER does not support the full entity schema. A full-schema F1 therefore partly measures coverage of supported entity types, not only extraction accuracy on a shared task.

Recommended improvement

If feasible from existing outputs, report two views:

full-schema utility comparison — reflects practical coverage;

common-schema comparison — restrict to entity categories supported by both ETHER and the compared model.

This is not a mandatory new experiment if all predictions already exist; it is primarily a rescoring/analysis issue.

If not added, explicitly state that ETHER’s lower overall score partly reflects its intentionally narrower schema.

P1.7 — Define the normalization used for “unique surface-form diversity”

Current issue

The plan appropriately tones down “3.5× richer vocabulary” to “3.5× higher surface-form symptom expression diversity under exact string matching.”

This is much better, but the exact normalization procedure still needs to be stated.

Required change

Specify whether unique spans were counted after:

lowercasing;

whitespace normalization;

punctuation normalization;

lemmatization;

exact raw string matching;

normalization of spelling variants.

If it is truly exact string matching, state that clearly and avoid biological/clinical interpretations stronger than surface-form diversity.

P1.8 — Error-analysis percentages must be traceable to the newly defined error classes

Current issue

The plan includes precise claims such as:

85–90% of boundary errors are superphrase extensions;

non-overlap false positives are 52% physiological/anatomical, 28% negation-scope, 20% schema overflow;

specific confusion counts.

Because the M/C/S taxonomy has changed, these figures must be recomputed or at least verified under the new definitions.

Required change

For every error-analysis claim, ensure the source script/result table uses the same final definitions as Methods.

Create a simple provenance table for internal use:

Claim

Final error definition

Source file/script

Recomputed after metric redesign?

Do not carry percentages forward from the previous Scheme 1/2/3 pipeline if category membership changed.

P1.9 — The hybrid LLM → encoder pipeline must remain clearly hypothetical unless it is actually tested

Current issue

The Discussion proposes:

LLM semantic recall filter → fine-tuned encoder boundary regularizer.

This is a reasonable discussion hypothesis but has not been described as an implemented benchmark experiment.

Required change

Keep it in Discussion as:

a proposed deployment architecture;

a hypothesis generated from complementary error profiles;

future work.

Do not state or imply that the hybrid pipeline improves performance unless an actual cascade experiment is run.

Priority 2 — Editorial and presentation corrections

P2.1 — Ethics/data wording must be consistent with the actual non-public data status

Current issue

The reviewer-response document proposes:

“Ethics approval was not required as this study analyzed de-identified publicly accessible spontaneous reports...”

This statement may be too broad if the actual curated FAERS dataset is not publicly distributable.

Required change

Use the precise institutional basis for the study’s ethics determination. The statement should distinguish:

the nature/source of the underlying reports;

the study’s secondary research use;

de-identification status if applicable;

why IRB/ethics review was not required or what determination/waiver applies.

Do not use “publicly accessible” merely as a convenient justification if it does not accurately describe the study dataset.

P2.2 — Data Availability should be written as a limitation/constraint, not an apology or contradiction

Recommended structure:

The underlying FAERS narratives and the curated reference annotations used in this study are not publicly distributable under applicable institutional/data-governance restrictions. [State what can be shared: code, prompts, annotation guidelines, aggregate results, etc., only if true.] The VAERS source data availability should be described separately according to its actual source/publication.

Avoid conflating FAERS and VAERS access status.

P2.3 — Editorial comments should still be answered one by one

The next reviewer-response document should retain separate responses for:

ESM metadata and PDF format;

running header ≤100 characters;

acknowledgement permissions;

funding;

competing interests;

ethics approval/rationale;

consent to participate;

consent for publication;

data/material availability;

code availability;

authors’ contributions and required final-approval statement;

AI-use disclosure.

Do not collapse all declaration issues into one generic paragraph.

P2.4 — AI-use disclosure must reflect actual use in this revision

The current planning text says AI assistance was used “strictly for stylistic proofreading.” That wording should only be used if factually correct for the full manuscript-development process.

The final statement should match the actual use of AI tools in:

drafting/editing;

reference identification;

code generation/debugging;

data analysis;

figure generation;

summarization;

language polishing.

The key issue is accuracy, not minimizing the disclosed role.

Recommended new structure for the next revision plan

The next manuscript_revision_plan.md should be reorganized around a stable set of methodological decisions rather than optimistic result statements.

A. Fixed study constraints

single expert reference annotator; no formal IAA;

original FAERS reference data not publicly distributable;

FAERS corpus consists of four drug–event case series;

LLM pre-annotation was used during human curation (if confirmed as the factual workflow).

B. Primary methodological upgrades

BioBERT 10-fold CV × 5 seeds;

cross-case-series leave-one-pair-out × 5 seeds;

strict exact-span/exact-label micro-F1 as primary metric;

adapted ADE-Eval weighted metric as secondary, if implementation audit confirms this naming;

two LLMs on FAERS; LLaMA 4 on VAERS;

complete prompt and inference documentation;

FAERS and VAERS taxonomy/guideline supplements;

FAERS/VAERS error anatomy with final error definitions.

C. Explicit limitations

no independent IAA;

potential pre-annotation anchoring;

four-case-series FAERS composition;

no fully independent external validation dataset;

prompt sensitivity;

no BERT threshold optimization;

data redistribution restriction;

model/API temporal versioning.

D. Claims that should be avoided

“definitive gold standard”;

“publicly reusable benchmark dataset”;

“minimal OOD decay”;

“robust semantic capture” for F1 ≈0.38;

“strong stability” unless seed and fold variance are separated;

“significantly better” without a formal paired statistical analysis;

“ADE-Eval” without implementation verification;

“a priori BioBERT selection” unless historically true;

“superior tokenization fidelity” unless directly measured;

“community adjudication” of a dataset that cannot be released.

Suggested manuscript-level quantitative reporting hierarchy

To reduce confusion and prevent metric cherry-picking, use the following hierarchy consistently in Abstract, Results, Tables, and Discussion.

Primary endpoint

Strict exact-span, exact-label micro-F1

BioBERT 10-fold CV;

BioBERT cross-case-series LOO;

Claude Sonnet FAERS;

LLaMA 4 FAERS/VAERS;

ETHER where applicable.

Secondary endpoint

Adapted ADE-Eval weighted micro-F1

Use only after scorer audit and consistent M/C/S/N pairing definitions.

Error characterization

exact matches M;

C_boundary;

C_class;

S_non_overlap;

N;

schema violations reported separately;

malformed-format outputs reported separately.

Variability

seed variability: within fixed split/fold;

fold/case-series variability: separate;

CI: only with a clearly defined resampling/statistical unit.

Recommended response strategy for the two unavoidable reviewer concerns

Reviewer #2 — Single annotator

Goal: acknowledge, constrain claim, document safeguards; do not pretend to provide IAA.

Core message:

Formal IAA was not feasible. The revised manuscript no longer characterizes the reference set as independently adjudicated. Annotation reliability is supported through annotator qualification, calibration, operationalized rules, full-narrative review, and transparent limitations, but the absence of a second annotator remains a limitation.

This is more defensible than constructing a substitute “validation” from model agreement.

Reviewer #2 — Dataset not public

Goal: explain restriction, change the manuscript claim, maximize reproducibility with materials that can legally/institutionally be shared.

Core message:

The authors agree that public release would improve reuse, but redistribution of the original FAERS/reference dataset is not permitted. The manuscript has therefore been revised to remove claims that the corpus is openly reusable and to describe the data-access restriction transparently. Reproducibility is supported through the shareable methodological artifacts [list only what is actually shareable].

Do not make data availability sound like it has been resolved by releasing dataset.db.

Additional experiments/analyses: what is still necessary?

No new large experiment is currently mandatory if the reported BERT runs are valid

The following already address the major experimental criticism:

10-fold CV;

five random seeds;

leave-one-drug–event-pair-out analysis;

second LLM on FAERS;

output-format comparison;

expanded error analysis.

High-value analysis using existing artifacts, if available

Human correction audit from annotation version history

accepted / modified / relabeled / deleted / added de novo.

Separate seed vs case-series variance summary

no new training required if per-run results already exist.

Correct document-level paired bootstrap

no new training required if predictions are saved.

Common-schema ETHER rescoring

no new training required.

Schema-violation / malformed-output rate

no new inference if raw outputs are saved.

Not required for this revision

second annotator / formal IAA (not feasible; handle transparently);

third LLM;

SHAP analysis;

full threshold sweep for BioBERT;

testing the proposed hybrid pipeline;

new external FAERS corpus, unless already available without delaying revision.

Final pre-revision-plan checklist

Before producing the next version of the revision plan, verify all items below.

Remove every statement that dataset.db / raw FAERS narratives / curated annotations are publicly released.

Rewrite Reviewer 2.W3 response around the actual data-governance restriction.

Remove “community adjudication” as a single-annotator QA argument.

Rewrite Reviewer 2.4 response to acknowledge that formal IAA is unavailable.

Remove or substantiate “near-perfect AGE/SEX/DOSE consistency.”

Confirm and document the true LLM-assisted annotation workflow.

Add pre-annotation anchoring to Limitations.

Recompute LOO confidence intervals from raw results using a defined statistical unit.

Replace “1.75% relative gap” with correct absolute/relative wording.

Rename LOO section as cross-case-series generalization rather than strong OOD validation.

Define the exact 10-fold CV/dev/test construction.

Confirm splits are fixed across seeds if seed variability is being interpreted independently.

Separate seed SD from fold/case-series SD.

Either implement/document paired bootstrap or remove the claim.

Verify BioBERT model-selection provenance and remove unsupported “a priori/tokenization fidelity” wording.

Audit ADE-Eval matching/pairing; rename to “adapted ADE-Eval” if not identical.

Update error-analysis terminology so C_boundary, C_class, and S_non_overlap are distinct.

Resolve schema-filtering vs schema-overflow inconsistency.

Build one canonical raw-label → normalized-label mapping table.

Reconcile 17 vs 10/11 category references, including TEMPORAL/DATE and VAERS labels.

Tone down INDICATION claims.

Expand XML-vs-JSON Table 5 to full P/R/F1 and error-count comparison.

Make Reviewer 3.22 response directly about threshold calibration.

Record exact LLM model identifiers and inference parameters.

Ensure cross-corpus wording does not imply Sonnet was evaluated on VAERS if it was not.

Define unique-surface-form normalization.

Verify all error-analysis percentages after the final metric redesign.

Keep the hybrid pipeline explicitly hypothetical.

Rewrite ethics/data statements to match the actual restricted-data situation.

Complete all editorial declarations individually.

Ensure AI-use disclosure accurately reflects actual manuscript-development use.

Bottom-line recommendation

After correction of the issues above, the current experimental package is sufficient to support a serious Drug Safety resubmission without adding a second annotator or another large modeling experiment. The strongest revised scientific story is not “we solved every limitation,” but rather:

an expert-curated pharmacovigilance reference corpus with transparent single-annotator limitations;

substantially strengthened BioBERT robustness evaluation across folds, seeds, and held-out drug–event case series;

strict NER performance as the primary benchmark, with a clearly defined pharmacovigilance-oriented weighted secondary metric;

complementary encoder/LLM error profiles documented through boundary, class-confusion, and non-overlap error analyses;

reproducible methods and shareable code/prompts/guidelines within the actual data-access constraints.

That framing is methodologically more defensible than trying to offset the unavoidable single-annotator and non-public-data constraints with optimistic language.