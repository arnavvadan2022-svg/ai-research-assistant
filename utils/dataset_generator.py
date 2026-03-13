"""
Dataset Generator
=================
Converts knowledge-graph triples into supervised-training datasets
(JSON and CSV) for Student LLM fine-tuning via structured supervision loss.
"""

import csv
import io
import json
from typing import Dict, List


class DatasetGenerator:
    """
    Generates training datasets from knowledge graph data.

    Each record is an (instruction, input, output) triple suitable for
    instruction-following fine-tuning (e.g. LoRA, QLoRA).
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, kg: Dict, source_text: str = "") -> List[Dict]:
        """
        Build a list of training examples from a knowledge graph.

        Parameters
        ----------
        kg          : dict produced by KnowledgeGraphBuilder.build()
        source_text : original document text (used to enrich instructions)

        Returns
        -------
        List of dicts with keys: instruction, input, output, metadata
        """
        records = []

        # 1. Entity-recognition examples
        records.extend(self._entity_examples(kg, source_text))

        # 2. Relation-extraction examples
        records.extend(self._relation_examples(kg, source_text))

        # 3. QA / KG-retrieval examples
        records.extend(self._qa_examples(kg))

        return records

    def to_json(self, records: List[Dict]) -> str:
        """Serialise dataset to JSON string."""
        return json.dumps(records, indent=2, ensure_ascii=False)

    def to_csv(self, records: List[Dict]) -> str:
        """Serialise dataset to CSV string."""
        if not records:
            return ""

        fieldnames = list(records[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for record in records:
            # Flatten any dict/list values to JSON strings for CSV compatibility
            flat = {
                k: json.dumps(v) if isinstance(v, (dict, list)) else v
                for k, v in record.items()
            }
            writer.writerow(flat)

        return buf.getvalue()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _entity_examples(self, kg: Dict, source_text: str) -> List[Dict]:
        """Create NER-style training examples."""
        records = []
        for entity in kg.get("entities", []):
            records.append({
                "instruction": (
                    "Identify and classify the named entity in the following text excerpt."
                ),
                "input": source_text[:500] if source_text else f"Text containing: {entity['entity']}",
                "output": json.dumps({
                    "entity": entity["entity"],
                    "type": entity.get("type", "CONCEPT"),
                    "description": entity.get("description", ""),
                }),
                "metadata": {
                    "task": "named_entity_recognition",
                    "entity_type": entity.get("type", "CONCEPT"),
                },
            })
        return records

    def _relation_examples(self, kg: Dict, source_text: str) -> List[Dict]:
        """Create relation-extraction training examples."""
        records = []
        for relation in kg.get("relations", []):
            records.append({
                "instruction": (
                    "Extract the relation between the two entities from the following text."
                ),
                "input": (
                    f"Subject: {relation['subject']}\n"
                    f"Object: {relation['object']}\n"
                    f"Text: {source_text[:500] if source_text else 'See subject and object above.'}"
                ),
                "output": json.dumps({
                    "subject": relation["subject"],
                    "predicate": relation.get("predicate", "related-to"),
                    "object": relation["object"],
                    "confidence": relation.get("confidence", 1.0),
                }),
                "metadata": {
                    "task": "relation_extraction",
                    "confidence": relation.get("confidence", 1.0),
                },
            })
        return records

    def _qa_examples(self, kg: Dict) -> List[Dict]:
        """Create KG-grounded question-answering examples."""
        records = []
        entities = kg.get("entities", [])
        relations = kg.get("relations", [])

        # One QA example per relation
        for rel in relations[:20]:
            question = f"What is the relationship between {rel['subject']} and {rel['object']}?"
            answer = (
                f"{rel['subject']} {rel.get('predicate', 'is related to')} {rel['object']} "
                f"(confidence: {rel.get('confidence', 1.0):.2f})."
            )
            records.append({
                "instruction": "Answer the question using information from the knowledge graph.",
                "input": question,
                "output": answer,
                "metadata": {
                    "task": "knowledge_graph_qa",
                    "subject": rel["subject"],
                    "object": rel["object"],
                },
            })

        # Entity-description QA
        for ent in entities[:10]:
            records.append({
                "instruction": "Describe the following entity based on the knowledge graph.",
                "input": f"Entity: {ent['entity']}",
                "output": (
                    f"{ent['entity']} is a {ent.get('type', 'concept')}. "
                    f"{ent.get('description', 'No additional description available.')}"
                ),
                "metadata": {
                    "task": "entity_description",
                    "entity": ent["entity"],
                },
            })

        return records
