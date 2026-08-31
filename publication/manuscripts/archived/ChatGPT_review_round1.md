我把目前上传的四份材料做了交叉审查：revision plan、reviewer evidence mapping、当前 `LLM4AE_rev1.docx`、以及原始 point-by-point reviewer comments；同时对照了 Drug Safety 已发表的 ADE-Eval 方法和近期该刊对数据/代码透明度的做法。先给结论：

**目前的 revision plan 在“覆盖 reviewer comment 的广度”上已经相当完整，但在“真正解决 reviewer concern 的方法学力度”上仍然不够。** 有几个问题不能靠补文字、换 terminology 或增加一个 LLM 就解决。尤其是 **single annotator、random seed、FAERS 四个 drug–AE case series 的外推性、evaluation metric 的重新定义、gold annotation provenance、data availability 前后矛盾**。如果这些问题不处理，我作为 Drug Safety reviewer 仍然会给 **Major Revision，甚至倾向 reject/revise-and-resubmit，而不会推荐 acceptance**。

另外需要特别区分：**当前上传的 `LLM4AE_rev1.docx` 还远没有执行完 revision plan**。所以，如果你问的是“现在这个 docx 能不能投回去”，我的答案是 **不能**；如果问的是“revision plan 全部执行后能不能达到 Drug Safety 水平”，答案是 **有可能，但还需要下面几项关键修正/实验**。 

---

# 一、我认为目前最大的风险并不是 LLM performance，而是 gold standard 的可信度

Reviewer #2 最严重的 concern 从来都不是模型性能，而是：

> corpus only has one annotator。

原始 reviewer 明确提出 ideally 至少两个 annotators，并要求 standard inter-annotator agreement。

现在 revision response material 试图用：

> SME1 与 ETHER / LLM / multi-model consensus 的 overlap F1 > 0.85

来补这个问题。

**我不建议这样回应 reviewer。**

因为：

**model–annotator agreement 不是 inter-annotator agreement。**

更严重的是 ETHER、LLaMA、BioBERT 又恰好是本文被评价的 systems。用被评价的系统来证明 reference annotation 的正确性，很容易被 reviewer 看成 circular validation。

如果 Reviewer #2 已经明确因为 single annotator 而“leaning towards reject”，那么：

> “我们没有第二个 annotator，但模型也比较同意这个 annotator”

不会真正消除 concern。

### 对 Drug Safety 这种 journal，我会把这一项视为 revision 的第一优先级。

不需要重新 double annotate 829 cases。

一个实际、足够有说服力的设计是：

**独立第二 annotator blind re-annotate 约 15–20% FAERS corpus（大约 125–165 reports），按四个 drug–AE series 分层抽样；然后 adjudication。**

至少报告：

* exact-span entity-level agreement/F1；
* overlap-span agreement；
* label agreement on overlapping spans；
* major categories per-category agreement；
* disagreements 的 adjudication taxonomy。

如果条件允许，再给一个 token-level κ/α，但 **不要只报 Cohen κ**，因为大量 O tokens 会使 κ 看起来异常漂亮。

有了这一项，single-annotator concern 才算真正关闭。

---

# 二、10-fold CV 目前并没有完全解决 Reviewer #2 的 random seed concern

这是 revision plan 里第二个容易被误认为“已经解决”的地方。

Reviewer 原话是：

> neural network models may provide slightly different results depending on the **initialization seeds**；建议 several rounds / different seeds / average and SD。

revision plan 现在改成：

> 10-fold cross-validation。

这很好，但**不是同一个问题**。

10-fold CV 主要回答：

> train/test sampling variability。

multiple initialization seeds 回答：

> stochastic training variability。

因此 reviewer 完全可能回复：

> “I requested multiple initialization seeds. The authors instead performed cross-validation.”

### 最稳妥的方法

固定 10 outer folds，每一个 fold：

> **BioBERT × 5 independent random seeds**

也就是每 corpus 50 个 training runs。

然后报告：

* pooled out-of-fold performance；
* mean ± SD across folds；
* seed-level variation；
* 最好简单区分 split variance 与 seed variance。

这样 Reviewer 2.W2 / 2.10 就几乎没有继续追问的空间。

还有一点必须在 manuscript 说明：

**所谓 80/10/10 的 10-fold CV 到底怎么形成。**

标准写法应该是：

> each report serves exactly once in the held-out outer test fold；within the remaining 90%, a validation partition is selected for model selection/early stopping.

如果现在实际上是每次重新随机 80/10/10 十次，那不是严格意义上的 10-fold CV。

---

# 三、我认为 revision plan 漏掉了一个比 random seed 更重要的问题：FAERS 的四个 case-series 会导致 random CV 高估 generalization

当前 manuscript 明确写：

829 FAERS ICSRs 来自四个 drug–AE pairs：

* Azacitidine–QT prolongation
* Tramadol–hypoglycemia
* Baricitinib–hypersensitivity
* Erenumab–stroke。

这对 manuscript 的 external validity 很重要。

如果 random 10-fold CV：

同一个 drug、同一个 target adverse event、类似 narrative templates 会同时出现在 training 和 test folds。

因此得到的 BioBERT F1 更接近：

> **within-case-series interpolation**

而不是：

> **generalization to unseen FAERS drug-event narratives**。

这一点 revision plan 目前基本没有处理。

而 manuscript 又想用：

> “reusable benchmarking dataset”
>
> “generalization”
>
> “robust pharmacovigilance extraction”

这样的语言。

这会给一个严格 reviewer 很好的攻击点。

### 我强烈建议增加一个 grouped generalization analysis

最自然的是：

**Leave-One-Drug–AE-Pair-Out 4-fold evaluation**

例如：

train = 另外三个 case series
test = Tramadol–hypoglycemia

轮换四次。

这实际上比再加一个新 LLM 更有科学价值。

如果数据里一个 FAERS case 有 multiple follow-up versions / highly similar duplicate narratives，还必须确保：

> **same case / follow-up cluster never crosses train/test folds。**

否则依然存在 leakage。

如果你们实在不做这个实验，也可以不做，但 manuscript 就必须明显降低 claim：

> “performance within four selected FAERS case series”

而不能泛化为 FAERS broadly。

---

# 四、目前三个 evaluation schemes 是整个 revision plan 中最需要谨慎处理的部分

这是我最担心 revision 被 reviewer 认为“metric engineering”的地方。

revision plan 准备把 abstract headline 从原来严格 F1 约 0.54 提到：

> BioBERT Scheme 1 F1 ≈ **0.906**

同时把 Scheme 1 定义成：

> C、甚至 wrong-class overlapping predictions 也作为 detection TP，
> non-overlapping FP 只给予 0.25 penalty。

这种 metric **不是不能做**，但是绝对不应该成为 primary headline metric。

否则 reviewer 很容易产生这样的印象：

> 原来 strict NER performance 不高，所以 revision 新建了一个 relaxed metric，把结果变成 0.9。

而且 Reviewer #3 恰恰已经对 error terminology 和 metric interpretation 很敏感。

### Scheme 2 是有坚实依据的

ADE-Eval 在 Drug Safety 本刊发表，确实使用：

* C × 0.5
* S × 0.25
* N × 1

来模拟 pharmacovigilance back-office annotation correction cost。([Springer Link][1])

所以：

**ADE-Eval weighted metric 是非常合适的 secondary/co-primary clinical metric。**

但是这里还有一个技术问题。

ADE-Eval 的 **C 是 paired inexact matches，包括 span 或 MedDRA code 不一致**。

你们现在似乎把：

* same-label boundary mismatch → C
* wrong-label but overlapping → `S_wrong_class`

分开了。

这样的话，当前 Scheme 2 **不一定严格等价于 ADE-Eval**。

因此 manuscript 不能轻易写：

> “ADE protocol”

除非 scorer 的 pairing 和 weighting 完全复现 ADE-Eval。

### 我建议最终只突出两个标准结果

**Primary metric：Strict exact-match micro-F1**

这是传统 NER 的最清楚结果。

**Clinical secondary metric：ADE-Eval back-office weighted micro-F1**

说明其 pharmacovigilance operational interpretation。

Scheme 1 可以保留，但改成：

> **label-agnostic overlap/entity-detection analysis**

放 secondary/supplementary。

不要在 Abstract 最先报 0.9058。

我反而建议 Abstract 写：

> Strict exact-match: BioBERT 0.640 vs Sonnet 0.467 vs LLaMA 0.404
> ADE-Eval weighted: BioBERT 0.782 vs Sonnet 0.644 vs LLaMA 0.625

这样可信度远高于：

> 0.906 vs 0.840 vs 0.856。

---

# 五、Reviewer #3 明确要求不要把普通 false positives 称为 “hallucination”，但 revision plan 仍大量在用

这是一个直接的 reviewer-compliance 问题。

Reviewer #3 两次明确指出：

> non-overlapping predicted span is a false positive / spurious prediction，**not hallucination**。

他甚至专门解释什么情况下才可以称 hallucination。

但是 revision plan 里面仍然有：

* `S_hallucination`
* “pure hallucinations”
* “hallucination-penalized”
* “JSON reduces pure hallucinations by 46.52%”。

这相当于 reviewer 已经明确要求改，你们 revision 又重新用了。

### 应全部换掉

我建议统一：

> **non-overlapping spurious false positive (S_non-overlap)**

或者：

> **ungrounded spurious prediction**

实际上 “ungrounded” 也容易被理解为 LLM terminology，所以最安全是：

> **non-overlapping false positive**。

真正可以单独分析的 hallucination 是：

> model generated text that was not present in the source narrative。

这正好可以利用你们的 `SequenceMatcher` 检测，并单独报告：

* text alteration rate；
* fabricated text rate；
* invalid tag rate。

这样反而是一个很漂亮的 Reviewer #3 response。

---

# 六、目前 gold annotation workflow 存在一个必须在提交前解决的内部矛盾

这是我认为非常危险的 factual inconsistency。

当前 manuscript Section 2.2 明确说：

> annotation process was conducted entirely manually **without assistance from AI-based tools**。

但是 reviewer response materials 写的是：

> LLM generated candidate inline spans → GUI → human reviewed 100% → corrected/deleted/added missed entities。

这两个版本不能同时成立。

而且当前公开的 LLM4AE GitHub README 明确把平台描述成有 **AI-assisted labeling**，也支持 SME1/SME2/adjudication workflow。([GitHub][2])

所以在任何进一步写作之前，需要先确定真实 provenance：

### 情况 A：gold annotation 真的是 fully manual

那么 response to Reviewer 2.5 应该直接说：

> reviewer may have inferred that LLM pre-annotation was used; however, the reference corpus itself was manually annotated. LLM functionality was used only for automated benchmarking / is a capability of the platform.

### 情况 B：确实先有 LLM pre-annotation 再 human correction

那就必须诚实写出来。

而且要承认可能存在：

> anchoring / pre-annotation bias。

此时第二独立 annotator 的 IAA 更加必要。

**这个 factual question 一定不能由语言优化来“折中写”。必须查 annotation provenance/logs 后选一个真实版本。**

---

# 七、Reviewer 3.9 的 BERT ablation 目前也有潜在 test leakage

当前 manuscript 是：

> 用 VAERS 比较 BERT / BioBERT / ClinicalBERT / Bio_ClinicalBERT，选择 BioBERT，然后又在 VAERS 上报告 final performance。

如果 model selection 使用了 final VAERS test data，那么：

> VAERS final performance 不再是完全 independent test estimate。

revision plan 现在说放到 Supplement S2，但只是“补充描述”还不够。

另外，当前 Supplement Table S2 本身并不支持：

> “BioBERT had superior precision and recall”

因为从上传表来看 ClinicalBERT overall precision 反而略高。

更好的写法是：

> BioBERT achieved the highest overall development-set F1 / was selected a priori based on biomedical pretraining and preliminary development-set performance.

但前提必须是真的。

### 最干净的处理

在新的 CV 中：

> base-model selection 只发生在 training/validation data；

或者干脆：

> BioBERT 固定为预先选定 baseline，不再根据 final test performance selection。

不要利用 VAERS final folds 来决定 model architecture。

---

# 八、taxonomy 本身需要一次系统 audit；现在有可能一部分所谓“model confusion”其实来自 guideline ambiguity

这是 manuscript 目前容易被 NLP/clinical reviewer 抓住、但 revision plan 没有充分意识到的问题。

例如当前 Supplement S1：

`DX` 的定义写得更像：

> diagnostic procedure/test name

但 Results 中：

> hepatitis、migraine、hypertension、rheumatoid arthritis

又都被当成 DX。

同时 AE 定义又包括：

> new diagnoses、symptoms、clinical conditions。

那么：

> AE vs DX

天然存在 ontology overlap。

MHX 又依赖 temporal context。

这很可能解释部分 DX→MHX、DX→AE confusion。

因此在强调：

> “LLM confuses closely related concepts”

之前，首先要证明：

> gold taxonomy 对这些概念有 sufficiently operationalized distinction。

### Supplement S1/S2 必须新增

不仅是 definition + examples，还要有：

> **boundary rules + inclusion rules + exclusion rules + disambiguation rules。**

尤其：

* AE vs DX
* DX vs MHX
* LAB vs AE
* STATUS vs AE
* sDrug/cDrug/oDrug
* INDICATION vs DX
* TREATMENT vs DRUG

需要明确。

另外 17 → 10/11 categories 的 mapping 应提供一个完整 mapping table，并通过脚本自动 reconcile counts。

当前 manuscript 中的 raw table 和 normalized table 从渲染出来看也有一些计数/表号异常，提交前必须程序化核对。

---

# 九、“VAERS vocabulary 3.5× richer”这个表述我建议删掉或降级

13,819 unique symptom terms vs 3,991 unique AE terms，确实可以是事实。

但是 unique strings 很容易受到：

* capitalization
* spelling variants
* plural/singular
* abbreviations
* punctuation
* boundary differences

影响。

所以它证明的是：

> **higher observed surface-form diversity**

而不严格证明：

> “3.5× richer clinical vocabulary”。

Drug Safety reviewer 对这种解释性 language 会比较敏感。

建议正文写：

> VAERS contained 3.5-fold more unique symptom surface forms under the specified normalization procedure.

然后明确 normalization：

lowercase? lemmatization? punctuation? exact span text?

---

# 十、output-format experiment 是好的，但它不能完全替代 Reviewer #3 对 prompt sensitivity 的 concern

XML vs JSON full-corpus comparison是 revision plan 很好的新增部分。

但 Reviewer 3.12 实际上还问：

> zero-shot vs few-shot，以及 more examples 是否改善。

目前 plan 只做：

> one-shot + XML/JSON。

严格说只解决了 output representation，不完全解决 few-shot landscape。

一个很小但非常有价值的 supplemental experiment 是：

> 0-shot vs 1-shot vs 3-shot

在预先定义的 development subset 上做。

然后固定 prompt，再在 held-out evaluation set 上运行。

不要：

> 用全部 829 cases 比 5 个 prompts → 选最好的 → 再在同 829 cases 报 final。

那相当于 prompt test-set tuning。

---

# 十一、Reviewer 3.22 的 BERT probability threshold 只放 Future Work，我认为“能过”，但不是最佳 response

Reviewer 明确指出：

> BERT confidence threshold 可以改变 precision/recall trade-off。

revision plan 目前只是 Discussion 里说：

> future work。

这不是不可以。

但既然你们已经要重新跑 BioBERT，我会建议顺便做。

尤其 Drug Safety audience 很关心：

> 高 recall screening 还是 high precision extraction？

可以在 validation folds 上得到：

> span confidence threshold → precision-recall curve。

然后在 test fold 锁定 threshold。

哪怕只放 Supplement，也会显著提高 manuscript 的 practical PV relevance。

---

# 十二、还缺少 uncertainty / statistical comparison；目前很多 “outperformed” 并没有统计依据

例如：

> LLM significantly outperformed ETHER

当前 manuscript section title 就用了 “significantly”。

但没有显著性检验。

revision plan 仍主要是 point estimates。

建议使用：

> **document-level paired bootstrap**

因为每个模型都可以在相同 reports 上比较。

报告：

* F1 95% CI；
* ΔF1 95% CI；
* BioBERT vs Sonnet；
* BioBERT vs LLaMA；
* LLaMA vs ETHER。

对于 INDICATION = 162 这样的 rare category，这尤其重要。

不要写：

> “BioBERT collapses while LLMs maintain strong semantic capture”。

F1 0.38 本身也谈不上绝对意义的 “strong”。

更中性：

> “Both LLMs achieved higher F1 than BioBERT for INDICATION, although absolute performance remained modest.”

这更像 Drug Safety 的语言。

---

# 十三、ETHER 比较需要一个 common-schema analysis

ETHER 本来就不支持 LAB、STATUS、AGE、SEX 等类别。

如果“overall F1”直接把这些类别都算入 denominator，那么：

> LLM > ETHER

一部分反映的是：

> schema coverage

而不是：

> extraction accuracy on the same task。

我会建议同时报告：

**Full-schema utility evaluation**

体现实际 system coverage。

以及：

**Common-category head-to-head evaluation**

只在双方都支持的类别上比较。

这样对 ETHER 更公平，也使结论更可信。

---

# 十四、data availability 目前还是 unresolved，而且不能轻易在 revision plan 中承诺 public `dataset.db`

这是另一个严重 contradiction。

当前 manuscript：

> expert annotations are **not publicly available** due to institutional/regulatory restrictions。

revision plan：

> entire `dataset.db` with 1,829 reports and annotations will be publicly released。

我检查了目前公开的 LLM4AE repository：repository 本身是 public，但从当前公开页面我**无法验证 `dataset.db` 已经公开发布**。([GitHub][2])

这一点不能等投稿时再解决。

因为 reviewer #2 已明确把 public corpus availability 作为 major weakness。

而且 Drug Safety 自己近年来的 methodological guidance 强调，应清楚说明 preprocessing/postprocessing data、code、software version，并尽可能提供 versioned URL/DOI；若因为 legal/licensing restriction 无法共享，也要明确说明。([Springer Link][3])

### 最佳做法

如果允许 release：

> 在 resubmission **之前**完成 release，最好 Zenodo/OSF DOI + GitHub commit/tag。

不要只写：

> “will be publicly available”。

如果不允许 raw FAERS narrative release：

就不要承诺 `dataset.db` raw text。

可以考虑：

> annotations + document identifiers + schema + scorer + reproducible extraction instructions + permitted derived data。

但同时必须降低：

> “fully reusable public benchmark”

的 claim。

---

# 十五、Reviewer #3 的 3.23 并没有被完全回答

目前 plan 用：

1. XML vs JSON；
2. 加 Claude Sonnet 4.6；

来回应 prompt/model breadth。

这是合理的，但 Reviewer 3.23 还有两个点：

* Shapley / interpretability；
* another local downloadable model。



我认为 **SHAP 不需要做**。

可以非常合理地回应：

> token-level SHAP analyses are outside the principal objective of comparing extraction accuracy; instead, we expanded systematic span- and class-level error analyses.

Reviewer 大概率会接受。

第三个 local LLM 也不是 mandatory。

Sonnet + LLaMA 已经足够支持 plural “LLMs”。

不过 title 里的：

> **“Frontier Large Language Models”**

我建议删掉。

截至现在，Anthropic 已经发布 Sonnet 5；Sonnet 4.6 当然仍然是有效 benchmark，但称它为当前 “leading/frontier” 没有必要，而且会迅速过时。Anthropic 的正式命名也是 **Claude Sonnet 4.6**。([Anthropic][4])

更加中性、耐久的 title 是：

> **Clinical Concept Extraction from Spontaneous Safety Report Narratives: Benchmarking BioBERT and Large Language Models on FAERS and VAERS Corpora**

我认为比当前 revision plan 的 title 更适合 Drug Safety。

---

# 十六、editorial comments 目前并没有被 revision plan 完整覆盖

这部分是比较明确的。

| Editorial requirement                         | 当前 plan                                            |
| --------------------------------------------- | -------------------------------------------------- |
| ESM metadata / standalone PDF                 | ✅ 基本覆盖                                             |
| Running header ≤100 characters                | ❌ revision plan 没看到                                |
| Written permission for named acknowledgements | ❌ 没覆盖                                              |
| Funding                                       | ✅                                                  |
| Conflict of interest for all authors          | ⚠️ 需确认                                             |
| Ethics approval / clear rationale             | ❌ 当前只有 “Not Applicable”                            |
| Consent to participate                        | ⚠️                                                 |
| Consent for publication                       | ⚠️                                                 |
| Data/material availability                    | ❌ 与 plan 矛盾                                        |
| Code availability                             | ✅ 但需要 exact version/commit                         |
| Authors’ contributions                        | ⚠️ 要用 editor 要求的 final wording                     |
| AI use heading                                | ❌ 当前 AI disclosure 在 Declarations 之前，而且需要更新为真实使用情况 |

这些要求都在 editor 的原始 letter 中明确列出。

尤其：

> Ethics approval: Not Applicable

不能只写这三个字。

editor 已经要求：

> 如果 N/A，要给 clear rationale。

如果分析的是内部 safety narratives，还应有明确的 institutional determination，而不是作者自己判断一句 N/A。

另外当前 manuscript 说 Elsa 用于 reference identification / grammar。

最终 AI-use statement 要反映**实际 revision 过程里真实使用过的 AI tools**，而不是机械保留旧版本。

---

# 十七、当前 `LLM4AE_rev1.docx` 本身还不是可以 resubmit 的 manuscript

这是和 revision plan 分开的判断。

我把 DOCX 渲染检查了一遍。它目前明显仍是 working draft：

* title 仍是旧版本；
* Abstract 仍是 single LLM / old numbers；
* 仍写 zero-shot；
* BioBERT 仍是单次 80/20 split；
* Supplementary prompt 仍存在 Reviewer #3 指出的 malformed example / incomplete tag specification；
* current manuscript 仍写 annotations entirely manual；
* Data Availability 仍写 annotations unavailable；
* current supplement 尚无完整 VAERS guideline table；
* current response letter 大量 comments 仍然 blank；
* Word tracked insertions/deletions 尚未 clean；
* 目前表号还能看到类似 “Table 12” 这样的 revision artifact。 

所以：

**不要把目前这个 docx 看成“已经达到 70–80% submission-ready”。**

从 journal submission 的角度，它现在更像：

> **scientifically promising revision-in-progress**

而不是：

> **resubmission-ready manuscript**。

---

# 十八、如果我是 Drug Safety 的独立 reviewer，我现在会怎么决定？

基于**目前 revision plan，而不是 optimistic wording**：

| Dimension                               | 我的判断                     |
| --------------------------------------- | ------------------------ |
| Pharmacovigilance relevance             | **Strong**               |
| Dataset/resource novelty                | **Potentially strong**   |
| FAERS/VAERS dual-corpus design          | **Strong**               |
| Model comparison breadth after revision | **Good**                 |
| Error analysis                          | **Potentially strong**   |
| Gold-standard validity                  | **Currently inadequate** |
| Experimental robustness                 | **Partially addressed**  |
| External generalizability               | **Currently weak**       |
| Metric transparency                     | **At risk**              |
| Reproducibility                         | **Not yet resolved**     |
| Data transparency                       | **Unresolved**           |
| Reviewer-comment closure                | **Broad but uneven**     |
| Current manuscript readiness            | **Not ready**            |

所以我的 editorial recommendation 会是：

> **Major Revision — potentially publishable after substantial methodological closure.**

不是 “accept with minor revision”。

如果在没有 second-annotator validation、没有真正 seed replication、继续把 Scheme 1 0.90 当 headline、继续使用 “hallucination”、且 public dataset 仍未落实的情况下 resubmit，我认为 **Reviewer #2 再次倾向 reject 的风险仍然相当高**。

反过来，如果把这些关键问题处理好，这篇文章的 story 会明显增强：

> **reference-standard validation → supervised vs generative extraction → strict vs PV-use-case evaluation → cross-case-series robustness → clinically interpretable error modes**

这个 story 是能够达到 Drug Safety 水平的，而且比单纯“BERT beats LLM”更有价值。

---

# 最后：我认为需要补的实验 / 分析完整清单

按重要程度，我会这样安排：

1. **【必须】Independent human re-annotation / IAA**：第二名独立 annotator 对约 15–20% FAERS reports 做 blind annotation，四个 drug–AE case series 分层抽样；报告 exact-span、overlap、label agreement、per-category agreement，并 adjudicate disagreements。不要用 model consensus 代替 IAA。

2. **【必须】真正的 seed robustness**：BioBERT 10 outer folds × 至少 5 initialization seeds；明确 outer test folds mutually exclusive，并报告 pooled OOF performance、fold variance 和 seed variance。

3. **【强烈建议接近必须】Case-series generalization**：Leave-One-Drug–AE-Pair-Out 4-fold evaluation；如存在同一 case 的 follow-up/duplicate narratives，必须按 case/duplicate cluster group split。若不做，则大幅收窄 generalizability claim。

4. **【必须】Scorer validation**：重新 audit M/C/S/N pairing；Scheme 3 与标准 exact NER scorer 对照；Scheme 2 要么严格实现 ADE-Eval，要么明确称 “adapted ADE-Eval”；加入 toy-case unit tests 并公开 scorer。彻底移除普通 FP 的 “hallucination” terminology。

5. **【必须】Paired uncertainty/statistics**：对所有模型使用 document-level paired bootstrap，报告 95% CI 和 ΔF1 CI；之后才使用 “significantly outperformed”。

6. **【必须】BioBERT model-selection leakage audit**：确认 BERT/BioBERT/ClinicalBERT 的选择从未使用 final test data；若使用过，需要在 train/validation 内重新选择，或将 BioBERT 固定为 a priori baseline。当前 S2 selection rationale 也要重新写。

7. **【强烈建议】Prompt ablation**：0-shot vs 1-shot vs 3-shot，加上 XML vs JSON；prompt selection 只在 development set 完成，final test 不用于选择 prompt。所有 exact prompts 保存为 versioned artifact/hash。

8. **【强烈建议】BERT precision–recall threshold analysis**：validation 上选择 span-level confidence threshold，给 PR curve / operating points，再锁定至 test；至少放 Supplement。

9. **【强烈建议】LLM repeatability analysis**：固定 exact model snapshot、temperature/top-p 等，在 stratified 10–20% subset 上重复推理 ≥3 次，报告 run-to-run span agreement；如果 full-dataset 成本可接受则更好。

10. **【强烈建议】Schema-adherence / text-integrity analysis**：分别报告 invalid tags、unknown tags、source-text alteration、fabricated-text rate、non-target-category output rate。Out-of-scope categories 可以在 NER scoring 前 filter，但不能“静默消失”，要单独报告 schema violation rate。

11. **【强烈建议】ETHER common-schema comparison**：除 full-schema comparison 外，再提供 ETHER 与 LLM/BioBERT 在共同支持 categories 上的公平 head-to-head comparison。

12. **【可选】真正独立的 external FAERS validation set**：如果能够再取得来自其他 drug–AE pairs 的一小批 cases，它比增加第三个 LLM 更能提高论文层级；如果有这个数据，可以替代/增强 leave-one-pair-out。

13. **【可选】第三个 local/open-weight LLM**：不是 publication blocker。LLaMA + Claude 已经基本回应 Reviewer #3；与其加入第三模型，我会优先做 IAA、group CV 和 statistical uncertainty。

14. **【仅当要把 hybrid pipeline 作为“结果”】LLM→BioBERT cascade experiment**：revision plan 的 two-stage hybrid pipeline 目前只能作为 Discussion hypothesis。如果 Abstract/Key Points 想说 hybrid architecture improves PV extraction，就必须实际做 cascade benchmark；否则明确写成 proposed future workflow 即可。

我认为其中 **1、2、4、5、6 是真正的 resubmission blockers；3 非常值得做，因为它直接决定文章能否把结果从“四个 case series”推到更广泛的 FAERS；7–11 会把这篇文章从“勉强回应 reviewer”提升到比较像 Drug Safety 的完整方法学论文。**

[1]: https://link.springer.com/article/10.1007/s40264-020-00996-3?utm_source=chatgpt.com "ADE Eval: An Evaluation of Text Processing Systems for Adverse Event Extraction from Drug Labels for Pharmacovigilance | Drug Safety | Springer Nature Link"
[2]: https://github.com/seldas/LLM4AE "GitHub - seldas/LLM4AE · GitHub"
[3]: https://link.springer.com/article/10.1007/s40264-024-01423-7?utm_source=chatgpt.com "The REporting of A Disproportionality Analysis for DrUg Safety Signal Detection Using Individual Case Safety Reports in PharmacoVigilance (READUS-PV): Explanation and Elaboration | Drug Safety | Springer Nature Link"
[4]: https://www.anthropic.com/news/claude-sonnet-4-6?r=0&utm_source=chatgpt.com "Introducing Sonnet 4.6 \ Anthropic"
