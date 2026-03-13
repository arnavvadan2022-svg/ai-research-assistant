import json
import csv
import io
import re
from typing import Dict, List, Optional


# Question templates keyed by relation predicate
_QUESTION_TEMPLATES: Dict[str, List[str]] = {
    'is-a':        ["What is {subject}?",
                    "How would you describe {subject}?"],
    'proposes':    ["What does {subject} propose?",
                    "What new approach is introduced by {subject}?"],
    'uses':        ["What does {subject} use?",
                    "Which method is employed by {subject}?"],
    'achieves':    ["What result does {subject} achieve?",
                    "What performance does {subject} reach?"],
    'outperforms': ["What does {subject} outperform?",
                    "Which baseline does {subject} beat?"],
    'based-on':    ["What is {subject} based on?",
                    "What prior work does {subject} build upon?"],
    'evaluated-on':["What benchmark is {subject} evaluated on?",
                    "On which dataset is {subject} tested?"],
    'improves':    ["What does {subject} improve?",
                    "Which metric does {subject} enhance?"],
    'compared-to': ["What is {subject} compared to?",
                    "Which system is {subject} benchmarked against?"],
    'contains':    ["What does {subject} contain?",
                    "What are the components of {subject}?"],
}

_DEFAULT_QUESTION = ["What is the relationship between {subject} and {object}?"]


class DatasetGenerator:
    """
    Converts KG triples (from KGBuilder.build_graph) into supervised
    training pairs for LLM distillation, exportable as JSON or CSV.

    Each training sample has the structure:
    {
        "id":           int,
        "prompt":       str,   # question / instruction
        "completion":   str,   # expected answer (generated from triple)
        "subject":      str,
        "predicate":    str,
        "object":       str,
        "confidence":   float,
        "source_sentence": str,
    }
    """

    # ─────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────

    def generate_training_pairs(
        self,
        graph_data: Dict,
        source_text: str = "",
        min_confidence: float = 0.60,
        max_samples: int = 500,
    ) -> List[Dict]:
        """
        Produce a list of training-pair dicts from *graph_data*.
        """
        relations: List[Dict] = graph_data.get('relations', [])
        entities:  List[Dict] = graph_data.get('entities',  [])
        entity_map = {e['text'].lower(): e for e in entities}

        pairs: List[Dict] = []
        idx = 0

        for rel in relations:
            if rel['confidence'] < min_confidence:
                continue
            if idx >= max_samples:
                break

            subj = rel['subject']
            pred = rel['predicate']
            obj  = rel['object']
            conf = rel['confidence']
            sent = rel.get('sentence', source_text[:200])

            templates = _QUESTION_TEMPLATES.get(pred, _DEFAULT_QUESTION)
            for template in templates:
                prompt = template.format(subject=subj, object=obj)
                completion = self._build_completion(
                    subj, pred, obj, conf, sent, entity_map
                )
                pairs.append({
                    'id':              idx,
                    'prompt':          prompt,
                    'completion':      completion,
                    'subject':         subj,
                    'predicate':       pred,
                    'object':          obj,
                    'confidence':      conf,
                    'source_sentence': sent,
                })
                idx += 1
                if idx >= max_samples:
                    break

        # Also add entity-description pairs
        for ent in entities:
            if idx >= max_samples:
                break
            if ent['confidence'] < min_confidence:
                continue
            prompt = f"What is {ent['text']}?"
            completion = (
                f"{ent['text']} is a {ent['type'].lower()} concept "
                f"identified with confidence {ent['confidence']}."
            )
            pairs.append({
                'id':              idx,
                'prompt':          prompt,
                'completion':      completion,
                'subject':         ent['text'],
                'predicate':       'is-type',
                'object':          ent['type'],
                'confidence':      ent['confidence'],
                'source_sentence': '',
            })
            idx += 1

        return pairs

    def to_json(self, pairs: List[Dict], indent: int = 2) -> str:
        """Serialise training pairs as a JSON array string."""
        return json.dumps(pairs, indent=indent, ensure_ascii=False)

    def to_jsonl(self, pairs: List[Dict]) -> str:
        """Serialise training pairs as newline-delimited JSON (JSONL)."""
        lines = []
        for pair in pairs:
            lines.append(json.dumps({
                'prompt':     pair['prompt'],
                'completion': pair['completion'],
            }, ensure_ascii=False))
        return "\n".join(lines)

    def to_csv(self, pairs: List[Dict]) -> str:
        """Serialise training pairs as CSV."""
        if not pairs:
            return ""
        buf = io.StringIO()
        fieldnames = [
            'id', 'prompt', 'completion', 'subject', 'predicate',
            'object', 'confidence', 'source_sentence',
        ]
        writer = csv.DictWriter(
            buf, fieldnames=fieldnames, extrasaction='ignore'
        )
        writer.writeheader()
        writer.writerows(pairs)
        return buf.getvalue()

    def get_stats(self, pairs: List[Dict]) -> Dict:
        """Return summary statistics for a generated dataset."""
        if not pairs:
            return {'total': 0}
        predicates = [p['predicate'] for p in pairs]
        pred_counts: Dict[str, int] = {}
        for p in predicates:
            pred_counts[p] = pred_counts.get(p, 0) + 1
        confs = [p['confidence'] for p in pairs]
        return {
            'total':               len(pairs),
            'unique_predicates':   len(set(predicates)),
            'predicate_distribution': pred_counts,
            'avg_confidence':      round(sum(confs) / len(confs), 3),
            'min_confidence':      min(confs),
            'max_confidence':      max(confs),
        }

    # ─────────────────────────────────────────
    #  Private helpers
    # ─────────────────────────────────────────

    def _build_completion(
        self,
        subj: str,
        pred: str,
        obj: str,
        conf: float,
        sentence: str,
        entity_map: Dict,
    ) -> str:
        """
        Build a natural-language answer from a triple and optional source
        sentence context.
        """
        pred_readable = pred.replace('-', ' ')
        base = f"{subj} {pred_readable} {obj}."

        obj_ent = entity_map.get(obj.lower())
        if obj_ent:
            type_hint = f" {obj} is a {obj_ent['type'].lower()} entity."
        else:
            type_hint = ""

        if sentence:
            clean_sent = sentence.strip()
            if not clean_sent.endswith('.'):
                clean_sent += '.'
            return f"{base}{type_hint} Source context: {clean_sent}"

        return f"{base}{type_hint}"
