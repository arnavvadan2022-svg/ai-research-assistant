import re
import math
from typing import Dict, List, Optional

from utils.kg_builder import KGBuilder
from utils.kg_retrieval import KGRetrieval


class DistillationPipeline:
    """
    Implements the LLM-distillation pipeline described in the architecture:

        Teacher LLM output
            ↓
        KGBuilder  →  entities / relations / confidence scores
            ↓
        KG Retrieval  →  improved context
            ↓
        Structured Supervision Loss  (compare teacher KG vs student KG)
            ↓
        Student LLM Inference  (prompt + KG context)
            ↓
        Prompt / KG Refinement
            ↓
        Evaluation Framework  (entity-level, relation-level metrics)
    """

    def __init__(self, ai_processor=None):
        self.kg_builder = KGBuilder()
        # Optional: pass an AIProcessor for student inference
        self._ai_processor = ai_processor

    # ─────────────────────────────────────────
    #  1. Structured Supervision Loss
    # ─────────────────────────────────────────

    def compute_supervision_loss(
        self,
        teacher_graph: Dict,
        student_output: str,
    ) -> Dict:
        """
        Measures how well *student_output* reproduces the knowledge
        present in *teacher_graph*.

        Returns a dict with scalar loss components and a total loss in [0, 1]
        (lower = better alignment with teacher KG).
        """
        student_graph = self.kg_builder.build_graph(student_output)

        entity_loss    = self._entity_coverage_loss(teacher_graph, student_graph)
        relation_loss  = self._relation_coverage_loss(teacher_graph, student_graph)
        confidence_loss = self._confidence_alignment_loss(teacher_graph, student_graph)

        # Weighted combination (weights can be tuned)
        total = 0.40 * entity_loss + 0.40 * relation_loss + 0.20 * confidence_loss

        return {
            'entity_coverage_loss':    round(entity_loss,    4),
            'relation_coverage_loss':  round(relation_loss,  4),
            'confidence_alignment_loss': round(confidence_loss, 4),
            'total_loss':              round(total, 4),
            'student_entity_count':    student_graph['stats']['entity_count'],
            'teacher_entity_count':    teacher_graph['stats']['entity_count'],
            'student_relation_count':  student_graph['stats']['relation_count'],
            'teacher_relation_count':  teacher_graph['stats']['relation_count'],
        }

    # ─────────────────────────────────────────
    #  2. Student LLM Inference
    # ─────────────────────────────────────────

    def run_student_inference(
        self,
        prompt: str,
        kg_data: Dict,
        max_length: int = 500,
    ) -> Dict:
        """
        Runs inference with the student LLM, providing KG context as a
        structured prefix to the prompt.

        If an AIProcessor is attached, it is used for generation;
        otherwise the method returns a KG-enriched prompt that can be
        sent to any external LLM.
        """
        kg_context = self._build_kg_prompt_context(kg_data)
        enriched_prompt = f"{kg_context}\n\nQuestion: {prompt}"

        if self._ai_processor is not None:
            response = self._ai_processor.summarize(enriched_prompt, max_length)
        else:
            response = (
                "[Student LLM not configured – attach an AIProcessor "
                "to enable on-device inference]\n\n"
                f"KG-enriched prompt:\n{enriched_prompt}"
            )

        student_graph = self.kg_builder.build_graph(response)

        return {
            'prompt':          prompt,
            'kg_context':      kg_context,
            'enriched_prompt': enriched_prompt,
            'response':        response,
            'student_graph':   student_graph,
        }

    # ─────────────────────────────────────────
    #  3. Prompt / KG Refinement
    # ─────────────────────────────────────────

    def refine(
        self,
        prompt: str,
        kg_data: Dict,
        min_confidence: float = 0.70,
        max_triples: int = 15,
    ) -> Dict:
        """
        Produces a refined prompt and a pruned KG by:
        1. Filtering low-confidence entities and relations.
        2. Re-ranking triples by relevance to the prompt.
        3. Injecting the top-k triples back into the prompt.
        """
        # Prune low-confidence elements
        pruned_entities  = [
            e for e in kg_data.get('entities', [])
            if e['confidence'] >= min_confidence
        ]
        pruned_relations = [
            r for r in kg_data.get('relations', [])
            if r['confidence'] >= min_confidence
        ]

        # Re-rank relations by query relevance
        keywords = set(re.findall(r'\b\w{3,}\b', prompt.lower()))
        def _relevance(rel: Dict) -> float:
            text = (rel['subject'] + ' ' + rel['object']).lower()
            hits = sum(1 for kw in keywords if kw in text)
            return rel['confidence'] + 0.05 * hits

        pruned_relations.sort(key=_relevance, reverse=True)
        top_relations = pruned_relations[:max_triples]

        # Build refined KG dict
        refined_kg = {
            'entities':  pruned_entities,
            'relations': top_relations,
            'stats': {
                'entity_count':    len(pruned_entities),
                'relation_count':  len(top_relations),
                'min_confidence':  min_confidence,
            },
        }

        # Build refined prompt
        context = self._build_kg_prompt_context(refined_kg)
        refined_prompt = f"{context}\n\nQuestion: {prompt}"

        return {
            'refined_prompt':    refined_prompt,
            'refined_kg':        refined_kg,
            'pruned_entity_count':   len(pruned_entities),
            'pruned_relation_count': len(top_relations),
            'original_entity_count':   len(kg_data.get('entities', [])),
            'original_relation_count': len(kg_data.get('relations', [])),
        }

    # ─────────────────────────────────────────
    #  4. Evaluation Framework
    # ─────────────────────────────────────────

    def evaluate(
        self,
        predictions: List[Dict],
        ground_truth: List[Dict],
    ) -> Dict:
        """
        Compute entity-level and relation-level metrics.

        Both *predictions* and *ground_truth* are lists of graph_data dicts
        (as returned by KGBuilder.build_graph).

        Returns:
        {
            entity_metrics:   { precision, recall, f1 },
            relation_metrics: { precision, recall, f1 },
            overall_f1:       float,
            sample_count:     int,
        }
        """
        if not predictions or not ground_truth:
            return self._empty_metrics()

        entity_p  = entity_r  = entity_f1  = 0.0
        relation_p = relation_r = relation_f1 = 0.0
        n = min(len(predictions), len(ground_truth))

        for pred, gt in zip(predictions[:n], ground_truth[:n]):
            em = self._entity_metrics(pred, gt)
            rm = self._relation_metrics(pred, gt)
            entity_p   += em['precision']
            entity_r   += em['recall']
            entity_f1  += em['f1']
            relation_p  += rm['precision']
            relation_r  += rm['recall']
            relation_f1 += rm['f1']

        def avg(x):
            return round(x / n, 4) if n else 0.0

        overall_f1 = avg((entity_f1 + relation_f1) / 2)

        return {
            'entity_metrics': {
                'precision': avg(entity_p),
                'recall':    avg(entity_r),
                'f1':        avg(entity_f1),
            },
            'relation_metrics': {
                'precision': avg(relation_p),
                'recall':    avg(relation_r),
                'f1':        avg(relation_f1),
            },
            'overall_f1':  overall_f1,
            'sample_count': n,
        }

    # ─────────────────────────────────────────
    #  Private helpers
    # ─────────────────────────────────────────

    # -- Supervision loss helpers --

    def _entity_coverage_loss(
        self, teacher: Dict, student: Dict
    ) -> float:
        t_ents = {e['text'].lower() for e in teacher.get('entities', [])}
        s_ents = {e['text'].lower() for e in student.get('entities', [])}
        if not t_ents:
            return 0.0
        coverage = len(t_ents & s_ents) / len(t_ents)
        return 1.0 - coverage

    def _relation_coverage_loss(
        self, teacher: Dict, student: Dict
    ) -> float:
        def triple_set(graph: Dict):
            return {
                (r['subject'].lower(), r['predicate'], r['object'].lower())
                for r in graph.get('relations', [])
            }
        t_rels = triple_set(teacher)
        s_rels = triple_set(student)
        if not t_rels:
            return 0.0
        coverage = len(t_rels & s_rels) / len(t_rels)
        return 1.0 - coverage

    def _confidence_alignment_loss(
        self, teacher: Dict, student: Dict
    ) -> float:
        t_avg = teacher.get('stats', {}).get('avg_confidence_entities', 0.5)
        s_avg = student.get('stats', {}).get('avg_confidence_entities', 0.5)
        return abs(t_avg - s_avg)

    # -- Evaluation metric helpers --

    def _entity_metrics(self, pred: Dict, gt: Dict) -> Dict:
        p_set = {e['text'].lower() for e in pred.get('entities', [])}
        g_set = {e['text'].lower() for e in gt.get('entities', [])}
        return self._prec_rec_f1(p_set, g_set)

    def _relation_metrics(self, pred: Dict, gt: Dict) -> Dict:
        def rel_set(g: Dict):
            return {
                (r['subject'].lower(), r['predicate'], r['object'].lower())
                for r in g.get('relations', [])
            }
        return self._prec_rec_f1(rel_set(pred), rel_set(gt))

    @staticmethod
    def _prec_rec_f1(predicted: set, actual: set) -> Dict:
        if not predicted and not actual:
            return {'precision': 1.0, 'recall': 1.0, 'f1': 1.0}
        if not predicted:
            return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
        if not actual:
            return {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
        tp = len(predicted & actual)
        precision = tp / len(predicted)
        recall    = tp / len(actual)
        f1 = (2 * precision * recall / (precision + recall)
              if (precision + recall) > 0 else 0.0)
        return {
            'precision': round(precision, 4),
            'recall':    round(recall, 4),
            'f1':        round(f1, 4),
        }

    @staticmethod
    def _empty_metrics() -> Dict:
        zero = {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
        return {
            'entity_metrics':   zero.copy(),
            'relation_metrics': zero.copy(),
            'overall_f1':  0.0,
            'sample_count': 0,
        }

    # -- KG → prompt context --

    def _build_kg_prompt_context(self, kg_data: Dict) -> str:
        entities  = kg_data.get('entities', [])[:10]
        relations = kg_data.get('relations', [])[:15]

        lines: List[str] = ["[Knowledge Graph Context]"]

        if entities:
            ent_strs = [
                f"{e['text']} ({e['type']}, conf={e['confidence']})"
                for e in entities
            ]
            lines.append("Entities: " + "; ".join(ent_strs))

        if relations:
            lines.append("Relationships:")
            for r in relations:
                lines.append(
                    f"  {r['subject']} --[{r['predicate']}]--> {r['object']}"
                    f" (conf={r['confidence']})"
                )

        return "\n".join(lines)
