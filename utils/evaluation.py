"""
Evaluation Framework
====================
Computes performance metrics for the Knowledge Graph pipeline and the
Student LLM inference output, covering:

  - Entity extraction quality  (precision, recall, F1)
  - Relation extraction quality (precision, recall, F1)
  - Confidence score distribution
  - Graph connectivity metrics
  - KG-grounded QA quality (BLEU-1, exact-match)
"""

import math
import re
from typing import Dict, List, Optional


class EvaluationFramework:
    """
    Performance metrics and evaluation for the KG pipeline.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_kg(self, kg: Dict, reference: Optional[Dict] = None) -> Dict:
        """
        Evaluate a built knowledge graph.

        Parameters
        ----------
        kg        : dict produced by KnowledgeGraphBuilder.build()
        reference : optional gold-standard KG with the same schema

        Returns
        -------
        Dict of metric groups
        """
        metrics = {}

        metrics["graph_stats"] = self._graph_stats(kg)
        metrics["confidence_distribution"] = self._confidence_distribution(
            kg.get("relations", [])
        )

        if reference:
            metrics["entity_metrics"] = self._extraction_metrics(
                predicted=[e["entity"] for e in kg.get("entities", [])],
                gold=[e["entity"] for e in reference.get("entities", [])],
            )
            metrics["relation_metrics"] = self._relation_metrics(
                predicted=kg.get("relations", []),
                gold=reference.get("relations", []),
            )
        else:
            metrics["note"] = (
                "No reference KG provided; skipping precision/recall/F1. "
                "Pass a reference dict to enable comparative evaluation."
            )

        return metrics

    def evaluate_qa(self, predictions: List[Dict], references: List[Dict]) -> Dict:
        """
        Evaluate KG-grounded QA outputs.

        Parameters
        ----------
        predictions : list of {"question": str, "answer": str}
        references  : list of {"question": str, "answer": str}

        Returns
        -------
        Dict of aggregate QA metrics
        """
        if not predictions or not references:
            return {"error": "predictions and references must be non-empty lists"}

        exact_matches = 0
        bleu_scores = []

        ref_map = {r["question"].strip().lower(): r["answer"] for r in references}

        for pred in predictions:
            q = pred.get("question", "").strip().lower()
            predicted_ans = pred.get("answer", "")
            gold_ans = ref_map.get(q, "")

            if not gold_ans:
                continue

            if predicted_ans.strip().lower() == gold_ans.strip().lower():
                exact_matches += 1

            bleu_scores.append(self._bleu1(predicted_ans, gold_ans))

        n = len(predictions)
        return {
            "exact_match": round(exact_matches / n, 4) if n else 0.0,
            "avg_bleu1": round(sum(bleu_scores) / len(bleu_scores), 4) if bleu_scores else 0.0,
            "sample_count": n,
        }

    # ------------------------------------------------------------------
    # Internal metric helpers
    # ------------------------------------------------------------------

    def _graph_stats(self, kg: Dict) -> Dict:
        """Compute basic graph topology metrics."""
        graph = kg.get("graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        n = len(nodes)
        e = len(edges)

        # Average degree
        degree: Dict[str, int] = {}
        for edge in edges:
            degree[edge["source"]] = degree.get(edge["source"], 0) + 1
            degree[edge["target"]] = degree.get(edge["target"], 0) + 1

        avg_degree = sum(degree.values()) / n if n else 0.0

        # Density
        max_edges = n * (n - 1) if n > 1 else 1
        density = e / max_edges

        # Type distribution
        type_dist: Dict[str, int] = {}
        for node in nodes:
            t = node.get("type", "UNKNOWN")
            type_dist[t] = type_dist.get(t, 0) + 1

        return {
            "node_count": n,
            "edge_count": e,
            "avg_degree": round(avg_degree, 4),
            "density": round(density, 6),
            "entity_type_distribution": type_dist,
        }

    def _confidence_distribution(self, relations: List[Dict]) -> Dict:
        """Summarise confidence score distribution."""
        if not relations:
            return {"count": 0}

        scores = [r.get("confidence", 1.0) for r in relations]
        n = len(scores)

        buckets = {"high (≥0.8)": 0, "medium (0.5-0.8)": 0, "low (<0.5)": 0}
        for s in scores:
            if s >= 0.8:
                buckets["high (≥0.8)"] += 1
            elif s >= 0.5:
                buckets["medium (0.5-0.8)"] += 1
            else:
                buckets["low (<0.5)"] += 1

        mean = sum(scores) / n
        variance = sum((s - mean) ** 2 for s in scores) / n

        return {
            "count": n,
            "mean": round(mean, 4),
            "std_dev": round(math.sqrt(variance), 4),
            "min": round(min(scores), 4),
            "max": round(max(scores), 4),
            "buckets": buckets,
        }

    def _extraction_metrics(
        self, predicted: List[str], gold: List[str]
    ) -> Dict:
        """Compute precision, recall, F1 for entity/token sets."""
        pred_set = {self._normalise(p) for p in predicted}
        gold_set = {self._normalise(g) for g in gold}

        tp = len(pred_set & gold_set)
        fp = len(pred_set - gold_set)
        fn = len(gold_set - pred_set)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )

        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    def _relation_metrics(
        self, predicted: List[Dict], gold: List[Dict]
    ) -> Dict:
        """Compute relation-triple-level precision, recall, F1."""
        pred_set = {self._triple_key(r) for r in predicted}
        gold_set = {self._triple_key(r) for r in gold}

        tp = len(pred_set & gold_set)
        fp = len(pred_set - gold_set)
        fn = len(gold_set - pred_set)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )

        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    def _bleu1(self, hypothesis: str, reference: str) -> float:
        """Compute unigram BLEU score between two strings."""
        hyp_tokens = self._tokenise(hypothesis)
        ref_tokens = self._tokenise(reference)

        if not hyp_tokens:
            return 0.0

        ref_counts: Dict[str, int] = {}
        for t in ref_tokens:
            ref_counts[t] = ref_counts.get(t, 0) + 1

        matches = 0
        for t in hyp_tokens:
            if ref_counts.get(t, 0) > 0:
                matches += 1
                ref_counts[t] -= 1

        precision = matches / len(hyp_tokens)

        # Brevity penalty
        bp = 1.0
        if len(hyp_tokens) < len(ref_tokens):
            bp = math.exp(1 - len(ref_tokens) / len(hyp_tokens))

        return bp * precision

    @staticmethod
    def _normalise(text: str) -> str:
        return re.sub(r'\s+', ' ', text.strip().lower())

    @staticmethod
    def _triple_key(relation: Dict) -> str:
        subj = relation.get("subject", "").strip().lower()
        pred = relation.get("predicate", "").strip().lower()
        obj = relation.get("object", "").strip().lower()
        return f"{subj}|{pred}|{obj}"

    @staticmethod
    def _tokenise(text: str) -> List[str]:
        return re.findall(r'\b\w+\b', text.lower())
