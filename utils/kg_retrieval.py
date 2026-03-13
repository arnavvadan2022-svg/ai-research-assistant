import re
from typing import Dict, List, Tuple


class KGRetrieval:
    """
    Retrieves relevant triples from a Knowledge Graph and optionally uses
    them to improve a baseline answer.

    The graph_data dict is the output of KGBuilder.build_graph().
    """

    def __init__(self, graph_data: Dict):
        self.entities: List[Dict]   = graph_data.get('entities', [])
        self.relations: List[Dict]  = graph_data.get('relations', [])
        self._entity_index: Dict[str, Dict] = {
            e['text'].lower(): e for e in self.entities
        }

    # ─────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────

    def query(self, question: str, top_k: int = 10) -> Dict:
        """
        Find the triples most relevant to *question* and return:
        {
            matched_entities: [...],
            relevant_triples: [...],
            context_summary:  str,
        }
        """
        keywords = self._extract_keywords(question)

        # 1. Find directly mentioned entities
        matched_entities = self._match_entities(keywords)

        # 2. Gather triples that involve at least one matched entity,
        #    scored by combined entity & relation confidence.
        scored_triples = self._score_triples(matched_entities)
        scored_triples.sort(key=lambda x: x[1], reverse=True)
        top_triples = [t for t, _ in scored_triples[:top_k]]

        # 3. Build a short natural-language context summary
        context_summary = self._build_context(matched_entities, top_triples)

        return {
            'matched_entities': matched_entities,
            'relevant_triples': top_triples,
            'context_summary':  context_summary,
        }

    def get_improved_answer(
        self, question: str, base_answer: str
    ) -> str:
        """
        Prepend KG-derived context to *base_answer*, giving the model
        (or caller) structured background knowledge.
        """
        result = self.query(question)
        ctx = result['context_summary']
        if not ctx:
            return base_answer

        improved = (
            "📊 Knowledge Graph Context:\n"
            f"{ctx}\n\n"
            "💡 Answer:\n"
            f"{base_answer}"
        )
        return improved

    def get_entity_neighbourhood(
        self, entity_text: str, depth: int = 1
    ) -> Dict:
        """
        Return all triples within *depth* hops of *entity_text*.
        """
        found: List[Dict] = []
        frontier = {entity_text.lower()}

        for _ in range(depth):
            next_frontier: set = set()
            for rel in self.relations:
                if (rel['subject'].lower() in frontier or
                        rel['object'].lower() in frontier):
                    found.append(rel)
                    next_frontier.add(rel['subject'].lower())
                    next_frontier.add(rel['object'].lower())
            frontier = next_frontier - frontier

        return {
            'center': entity_text,
            'triples': found,
            'hop_depth': depth,
        }

    # ─────────────────────────────────────────
    #  Private helpers
    # ─────────────────────────────────────────

    def _extract_keywords(self, text: str) -> List[str]:
        stop = {
            'what', 'which', 'who', 'how', 'when', 'where', 'is', 'are',
            'does', 'do', 'the', 'a', 'an', 'of', 'in', 'on', 'for',
            'with', 'about', 'tell', 'me', 'explain', 'describe',
        }
        words = re.findall(r'\b\w{3,}\b', text.lower())
        return [w for w in words if w not in stop]

    def _match_entities(self, keywords: List[str]) -> List[Dict]:
        matched: List[Dict] = []
        for ent in self.entities:
            name_l = ent['text'].lower()
            if any(kw in name_l or name_l in kw for kw in keywords):
                matched.append(ent)
        return matched

    def _score_triples(
        self, matched_entities: List[Dict]
    ) -> List[Tuple[Dict, float]]:
        entity_names = {e['text'].lower() for e in matched_entities}
        scored: List[Tuple[Dict, float]] = []
        for rel in self.relations:
            subj_l = rel['subject'].lower()
            obj_l  = rel['object'].lower()
            in_subj = subj_l in entity_names
            in_obj  = obj_l  in entity_names
            if not (in_subj or in_obj):
                continue
            # Higher score when both endpoints are matched
            match_bonus = 0.2 if (in_subj and in_obj) else 0.0
            score = rel['confidence'] + match_bonus
            scored.append((rel, score))
        return scored

    def _build_context(
        self, entities: List[Dict], triples: List[Dict]
    ) -> str:
        if not entities and not triples:
            return ""

        lines: List[str] = []
        if entities:
            ent_str = ", ".join(
                f"{e['text']} ({e['type']})" for e in entities[:5]
            )
            lines.append(f"Relevant entities: {ent_str}.")

        if triples:
            lines.append("Key relationships:")
            for rel in triples[:8]:
                lines.append(
                    f"  • {rel['subject']} —[{rel['predicate']}]→ {rel['object']}"
                    f"  (conf: {rel['confidence']})"
                )
        return "\n".join(lines)
