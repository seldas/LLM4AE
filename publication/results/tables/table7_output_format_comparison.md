# Table 7: Impact of LLM Output Format Paradigm (Inline Tagged XML vs. Structured JSON Schema Offsets)

Empirical comparison between **Inline Tagged XML (`P2_TAG`)** and **Structured JSON Schema (`P1_JSON`)** representations evaluated on the full FAERS corpus (N = 829 Reports) across all 17 clinical concept categories.

| Model | Prompt Strategy & Output Paradigm | Strict Exact-Match F1 | Adapted ADE-Eval F1 | Boundary Alignment Success |
| :--- | :--- | :---: | :---: | :---: |
| **LLaMA 4 (1-shot)** | Inline Tagged XML (`P2_TAG`) | **0.4043** | **0.6249** | 100.0% |
| **LLaMA 4 (1-shot)** | JSON Schema (Structured Span Offsets) | **0.4071** | **0.5995** | 93.4% |
| **Claude 4.6 Sonnet (1-shot)** | Inline Tagged XML (`P2_TAG`) | **0.4667** | **0.6443** | 100.0% |

---

### Footnotes & Methodological Takeaways:
1. **Spurious Entity Suppression:** Formatting outputs as **Structured JSON suppresses non-overlapping spurious false positives ($S$) by 25.9%** (from 20,491 down to 15,178 spans), yielding higher Strict Precision (0.3785 vs. 0.3470) and higher Adapted ADE Precision (0.7019 vs. 0.6778).
2. **Narrative Grounding & Recall:** **Inline Tagged XML retains stronger narrative token alignment**, yielding fewer missed clinical entities ($N = 9,241$ in Tagged vs. $10,728$ in JSON) and higher Adapted ADE Recall (0.5796 vs. 0.5232).
3. **Boundary Alignment:** Inline tagging guarantees 100% token character alignment, whereas JSON character offset prediction suffers a 6.6% misalignment rate due to subword tokenization boundary shifts.
