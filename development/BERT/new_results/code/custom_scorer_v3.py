#custom_scorer_v3.py
import spacy
from spacy.training import Example
from spacy.scorer import Scorer
from spacy import registry
from collections.abc import Iterable
from collections import defaultdict

# Define the custom scorer function
@registry.scorers("ade_weighted_ner_scorer.v1")
def ade_weighted_ner_scorer():
    return spancat_char_score

def spancat_char_score(examples: Iterable[Example], **cfg):
    """
    Calculate NER task metrics: Exact Match (M), Partial Match (C), False Positive (S), False Negative (N)
    and compute revised P/R/F1 for each label type.
    """
    scorer = Scorer()
    results = scorer.score_spans(examples, attr="ents")

    M, C, S, N = 0, 0, 0, 0  # Initialize counts
    label_counts = defaultdict(lambda: {"M": 0, "C": 0, "S": 0, "N": 0})

    for example in examples:
        gold_ents = list({(ent.start_char, ent.end_char, ent.label_) for ent in example.reference.ents})
        pred_ents = list({(ent.start_char, ent.end_char, ent.label_) for ent in example.predicted.ents})
        pred_flag = [False] * len(pred_ents)
        sorted_pred_ents = sorted(pred_ents, key=lambda x: (int(x[0]), int(x[1])))
        sorted_gold_ents = sorted(gold_ents, key=lambda x: (int(x[0]), int(x[1])))

        M_temp = 0
        C_temp = 0

        # Calculate the number of exact matches, partial matches, false positives, and false negatives
        for gold_ent in sorted_gold_ents:
            totally_match_found = False
            partial_match_found = False
            for ind1 in range(len(sorted_pred_ents)):
                pred_ent = sorted_pred_ents[ind1]
                if pred_ent[0] == gold_ent[0] and pred_ent[1] == gold_ent[1] and pred_ent[2] == gold_ent[2]:
                    totally_match_found = True
                    pred_flag[ind1] = True
                    M += 1
                    M_temp += 1
                    label_counts[gold_ent[2]]["M"] += 1
                    break
                elif pred_ent[0] == gold_ent[0] or pred_ent[1] == gold_ent[1] or gold_ent[0] < pred_ent[0] < gold_ent[1] or gold_ent[0] < pred_ent[1] < gold_ent[1] or (pred_ent[0] < gold_ent[0] and pred_ent[1] > gold_ent[0]):
                    if not pred_flag[ind1]:
                        partial_match_found = True
                        pred_flag[ind1] = True
                        C += 1
                        C_temp += 1
                        label_counts[gold_ent[2]]["C"] += 1
                        break
            if not (totally_match_found or partial_match_found):
                N += 1
                label_counts[gold_ent[2]]["N"] += 1
        S += len(sorted_pred_ents) - M_temp - C_temp
        for ind1 in range(len(sorted_pred_ents)):
            if not pred_flag[ind1]:
                label_counts[sorted_pred_ents[ind1][2]]["S"] += 1

    # Revised M', C', S', N'
    M_ = M + (0.5 * C)
    C_ = 0.5 * C
    S_ = 0.25 * S
    N_ = N

    # Compute revised Precision / Recall / F1
    precision = M_ / (M_ + C_ + S_) if (M_ + C_ + S_) > 0 else 0
    recall = M_ / (M_ + C_ + N_) if (M_ + C_ + N_) > 0 else 0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    # Compute metrics for each label type
    label_metrics = {}
    for label, counts in label_counts.items():
        M_l = counts["M"]
        C_l = counts["C"]
        S_l = counts["S"]
        N_l = counts["N"]
        M_l_ = M_l + (0.5 * C_l)
        C_l_ = 0.5 * C_l
        S_l_ = 0.25 * S_l
        N_l_ = N_l
        precision_l = M_l_ / (M_l_ + C_l_ + S_l_) if (M_l_ + C_l_ + S_l_) > 0 else 0
        recall_l = M_l_ / (M_l_ + C_l_ + N_l_) if (M_l_ + C_l_ + N_l_) > 0 else 0
        f1_l = (2 * precision_l * recall_l) / (precision_l + recall_l) if (precision_l + recall_l) > 0 else 0
        label_metrics[label] = {
            "precision": precision_l,
            "recall": recall_l,
            "f1": f1_l
        }

    return {
        "ents_p": precision,
        "ents_r": recall,
        "ents_f": f1,
        "ents_per_type": label_metrics
    }
