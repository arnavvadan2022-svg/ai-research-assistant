import re
import json
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import networkx as nx


# ─────────────────────────────────────────────
#  Entity-type patterns (order matters: most
#  specific first)
# ─────────────────────────────────────────────
ENTITY_PATTERNS: List[Tuple[str, str, float]] = [
    # (regex pattern, entity_type, base_confidence)
    (r'\b(?:transformer|bert|gpt|llm|cnn|rnn|lstm|gan|vae|attention|'
     r'encoder|decoder|embedding|fine-tun\w+)\b',
     'MODEL', 0.90),
    (r'\b(?:neural network|deep learning|machine learning|'
     r'reinforcement learning|transfer learning|knowledge distillation|'
     r'knowledge graph|graph neural network|natural language processing|'
     r'computer vision|self-supervised|contrastive learning)\b',
     'TECHNIQUE', 0.85),
    (r'\b(?:accuracy|precision|recall|f1[\s-]?score|bleu|rouge|perplexity|'
     r'loss|auc|mse|mae|rmse|benchmark|baseline)\b',
     'METRIC', 0.88),
    (r'\b(?:dataset|corpus|benchmark|imagenet|glue|squad|coco|voc|'
     r'wikipedia|wikidata|freebase)\b',
     'DATASET', 0.87),
    (r'\b[A-Z][a-z]+ (?:et al\.?|and [A-Z][a-z]+)\b',
     'PERSON', 0.80),
    (r'\b(?:\d{4})\b',
     'YEAR', 0.75),
    (r'\b[A-Z][a-zA-Z]{2,}(?:\s[A-Z][a-zA-Z]{2,}){0,3}\b',
     'CONCEPT', 0.70),
]

# ─────────────────────────────────────────────
#  Relation patterns
#  Each entry: (sentence_regex, predicate_label, base_confidence)
# ─────────────────────────────────────────────
RELATION_PATTERNS: List[Tuple[str, str, float]] = [
    (r'{subj}\s+(?:is|are|was|were)\s+(?:a|an|the)?\s*{obj}',
     'is-a', 0.90),
    (r'{subj}\s+(?:proposes?|introduces?|presents?)\s+(?:a|an|the)?\s*{obj}',
     'proposes', 0.88),
    (r'{subj}\s+(?:uses?|utilizes?|employs?|leverages?)\s+(?:a|an|the)?\s*{obj}',
     'uses', 0.87),
    (r'{subj}\s+(?:achieves?|obtains?|reaches?)\s+(?:a|an|the)?\s*{obj}',
     'achieves', 0.85),
    (r'{subj}\s+(?:outperforms?|surpasses?|beats?|exceeds?)\s+(?:a|an|the)?\s*{obj}',
     'outperforms', 0.88),
    (r'{subj}\s+(?:is\s+based\s+on|builds?\s+on|extends?|builds?\s+upon)\s+(?:a|an|the)?\s*{obj}',
     'based-on', 0.85),
    (r'{subj}\s+(?:evaluates?\s+on|tests?\s+on|benchmarks?\s+on)\s+(?:a|an|the)?\s*{obj}',
     'evaluated-on', 0.87),
    (r'{subj}\s+(?:improves?|enhances?|boosts?)\s+(?:a|an|the)?\s*{obj}',
     'improves', 0.84),
    (r'{subj}\s+(?:compares?\s+(?:with|to)|compared\s+(?:with|to))\s+(?:a|an|the)?\s*{obj}',
     'compared-to', 0.82),
    (r'{subj}\s+(?:contains?|includes?|comprises?|consists?\s+of)\s+(?:a|an|the)?\s*{obj}',
     'contains', 0.83),
]


class KGBuilder:
    """
    Builds a Knowledge Graph from free text (e.g. LLM output or research paper
    abstract) by extracting entities, detecting relations, and assigning
    confidence scores to every element.
    """

    def __init__(self):
        self._entity_patterns = [
            (re.compile(pat, re.IGNORECASE), etype, conf)
            for pat, etype, conf in ENTITY_PATTERNS
        ]

    # ─────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────

    def extract_entities(self, text: str) -> List[Dict]:
        """
        Return a deduplicated list of entity dicts, each with:
        { text, type, confidence, occurrences }
        """
        found: Dict[str, Dict] = {}
        for pattern, etype, base_conf in self._entity_patterns:
            for m in pattern.finditer(text):
                token = m.group(0).strip()
                key = token.lower()
                if len(token) < 2:
                    continue
                if key in found:
                    found[key]['occurrences'] += 1
                    found[key]['confidence'] = min(
                        1.0, found[key]['confidence'] + 0.03)
                else:
                    conf = self._adjust_confidence(token, base_conf, text)
                    found[key] = {
                        'text': token,
                        'type': etype,
                        'confidence': round(conf, 3),
                        'occurrences': 1,
                    }

        entities = sorted(found.values(),
                          key=lambda e: e['confidence'], reverse=True)
        return entities

    def extract_relations(
        self, text: str, entities: List[Dict]
    ) -> List[Dict]:
        """
        Return a list of relation dicts:
        { subject, predicate, object, confidence }
        """
        relations: List[Dict] = []
        entity_texts = [e['text'] for e in entities]
        sentences = self._split_sentences(text)

        seen: set = set()
        for sentence in sentences:
            for i, subj_text in enumerate(entity_texts):
                for j, obj_text in enumerate(entity_texts):
                    if i == j:
                        continue
                    if subj_text.lower() not in sentence.lower():
                        continue
                    if obj_text.lower() not in sentence.lower():
                        continue
                    for _, predicate, base_conf in RELATION_PATTERNS:
                        key = (subj_text.lower(), predicate,
                               obj_text.lower())
                        if key in seen:
                            continue
                        conf = self._score_relation(
                            sentence, subj_text, obj_text, base_conf
                        )
                        if conf > 0.55:
                            seen.add(key)
                            subj_ent = next(
                                (e for e in entities
                                 if e['text'].lower() == subj_text.lower()),
                                None)
                            obj_ent = next(
                                (e for e in entities
                                 if e['text'].lower() == obj_text.lower()),
                                None)
                            relations.append({
                                'subject': subj_text,
                                'subject_type': subj_ent['type'] if subj_ent else 'UNKNOWN',
                                'predicate': predicate,
                                'object': obj_text,
                                'object_type': obj_ent['type'] if obj_ent else 'UNKNOWN',
                                'confidence': round(conf, 3),
                                'sentence': sentence.strip(),
                            })

        relations.sort(key=lambda r: r['confidence'], reverse=True)
        return relations

    def build_graph(self, text: str) -> Dict:
        """
        Full pipeline: text → entities → relations → NetworkX graph.
        Returns a serialisable dict with graph stats and the entity/relation
        lists (used downstream by serialiser, retrieval and dataset generator).
        """
        entities = self.extract_entities(text)
        relations = self.extract_relations(text, entities)

        g = nx.DiGraph()
        for ent in entities:
            g.add_node(
                ent['text'],
                entity_type=ent['type'],
                confidence=ent['confidence'],
                occurrences=ent['occurrences'],
            )
        for rel in relations:
            g.add_edge(
                rel['subject'],
                rel['object'],
                predicate=rel['predicate'],
                confidence=rel['confidence'],
                sentence=rel['sentence'],
            )

        graph_data = {
            'entities': entities,
            'relations': relations,
            'stats': {
                'entity_count': g.number_of_nodes(),
                'relation_count': g.number_of_edges(),
                'density': round(nx.density(g), 4) if g.number_of_nodes() > 1 else 0.0,
                'avg_confidence_entities': round(
                    sum(e['confidence'] for e in entities) / len(entities), 3
                ) if entities else 0.0,
                'avg_confidence_relations': round(
                    sum(r['confidence'] for r in relations) / len(relations), 3
                ) if relations else 0.0,
            },
        }
        return graph_data

    # ─────────────────────────────────────────
    #  Private helpers
    # ─────────────────────────────────────────

    def _adjust_confidence(
        self, token: str, base: float, text: str
    ) -> float:
        """Boost confidence based on term frequency and position."""
        freq = len(re.findall(re.escape(token), text, re.IGNORECASE))
        # small boost per additional occurrence (capped)
        freq_boost = min(0.10, (freq - 1) * 0.02)
        # slight boost if term appears near the start of the text
        pos = text.lower().find(token.lower())
        position_boost = 0.05 if pos < len(text) * 0.2 else 0.0
        return min(1.0, base + freq_boost + position_boost)

    def _score_relation(
        self, sentence: str, subj: str, obj: str, base: float
    ) -> float:
        """
        Give a score to a (subject, object) pair based on their proximity and
        the grammatical distance between them in the sentence.
        """
        sl = sentence.lower()
        si = sl.find(subj.lower())
        oi = sl.find(obj.lower())
        if si == -1 or oi == -1:
            return 0.0
        distance = abs(si - oi)
        # penalise long distances
        penalty = min(0.15, distance / 400)
        return max(0.0, base - penalty)

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Simple sentence splitter that handles common abbreviations."""
        text = re.sub(r'\n+', ' ', text)
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        return [p.strip() for p in parts if len(p.strip()) > 10]
