"""
Knowledge Graph Builder
=======================
Implements the full KG pipeline described in the architecture:

  LLM Document / Response
        |
  ----------------
  |       |      |
Entities Relations Confidence Scores
  \\       |       /
   KG Builder
        |
  ---------------
  |             |
KG Serializer  KG Retrieval
(RDF/JSON-LD/  (Improved Answers)
 GraphML)
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from config import Config


# ---------------------------------------------------------------------------
# KnowledgeGraphBuilder
# ---------------------------------------------------------------------------

class KnowledgeGraphBuilder:
    """
    Extracts entities, relations and confidence scores from a text document
    using the Groq LLM, then builds an in-memory knowledge graph.
    """

    # Maximum number of characters of input text sent to the LLM
    _MAX_TEXT_CHARS = 3000
    # Maximum entities passed to relation-extraction prompt
    _MAX_ENTITIES_FOR_RELATIONS = 20
    # Maximum entities returned by rule-based extraction
    _MAX_RULE_ENTITIES = 30

    def __init__(self):
        self.groq_api_key = Config.GROQ_API_KEY
        self.groq_model = Config.GROQ_MODEL
        self.serializer = KGSerializer()
        self.retrieval = KGRetrieval()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, text: str, context: str = "") -> Dict:
        """
        Full KG pipeline:
          1. Extract entities
          2. Extract relations (with confidence scores)
          3. Build graph structure
          4. Return rich result dict
        """
        if self.groq_api_key:
            entities = self._groq_extract_entities(text)
            relations = self._groq_extract_relations(text, entities)
        else:
            entities = self._rule_extract_entities(text)
            relations = self._rule_extract_relations(text, entities)

        graph = self._build_graph(entities, relations)
        return {
            "entities": entities,
            "relations": relations,
            "graph": graph,
            "stats": {
                "entity_count": len(entities),
                "relation_count": len(relations),
                "node_count": len(graph["nodes"]),
                "edge_count": len(graph["edges"]),
            },
        }

    def query(self, kg: Dict, question: str) -> str:
        """
        Use KG Retrieval Module to answer a question from the knowledge graph.
        """
        return self.retrieval.answer(kg, question, self.groq_api_key, self.groq_model)

    # ------------------------------------------------------------------
    # Groq-powered extraction
    # ------------------------------------------------------------------

    def _groq_chat(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        from groq import Groq
        client = Groq(api_key=self.groq_api_key)
        completion = client.chat.completions.create(
            model=self.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return completion.choices[0].message.content.strip()

    def _groq_extract_entities(self, text: str) -> List[Dict]:
        """Ask Groq to extract named entities and return a JSON list."""
        system = (
            "You are a knowledge extraction assistant. "
            "Your task is to extract named entities from academic text. "
            "Return ONLY a valid JSON array. Each item must have: "
            '{"entity": "<name>", "type": "<type>", "description": "<short description>"}. '
            "Entity types: CONCEPT, METHOD, DATASET, METRIC, AUTHOR, INSTITUTION, FIELD, OTHER."
        )
        user = (
            "Extract all important named entities from the following text.\n\n"
            f"TEXT:\n{text[:self._MAX_TEXT_CHARS]}\n\n"
            "Return only the JSON array, no other text."
        )
        raw = self._groq_chat(system, user, max_tokens=800)
        return self._parse_json_list(raw, fallback=self._rule_extract_entities(text))

    def _groq_extract_relations(self, text: str, entities: List[Dict]) -> List[Dict]:
        """Ask Groq to extract relations between entities with confidence scores."""
        entity_names = [e["entity"] for e in entities[:self._MAX_ENTITIES_FOR_RELATIONS]]
        system = (
            "You are a knowledge extraction assistant. "
            "Your task is to extract relations between entities in academic text. "
            "Return ONLY a valid JSON array. Each item must have: "
            '{"subject": "<entity>", "predicate": "<relation>", '
            '"object": "<entity>", "confidence": <0.0-1.0>}.'
        )
        user = (
            "Extract relations between the following entities from the text.\n\n"
            f"ENTITIES: {json.dumps(entity_names)}\n\n"
            f"TEXT:\n{text[:self._MAX_TEXT_CHARS]}\n\n"
            "Return only the JSON array, no other text."
        )
        raw = self._groq_chat(system, user, max_tokens=1000)
        return self._parse_json_list(raw, fallback=[])

    # ------------------------------------------------------------------
    # Rule-based fallback extraction
    # ------------------------------------------------------------------

    def _rule_extract_entities(self, text: str) -> List[Dict]:
        """Simple heuristic entity extraction when Groq is unavailable."""
        entities = []
        seen = set()

        # Capitalised noun phrases (simple heuristic)
        pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b')
        for match in pattern.finditer(text):
            name = match.group(1)
            if name not in seen and len(name) > 3:
                seen.add(name)
                entities.append({
                    "entity": name,
                    "type": "CONCEPT",
                    "description": f"Mentioned in document."
                })

        # Common academic keywords
        keywords = [
            "neural network", "deep learning", "transformer", "attention",
            "BERT", "GPT", "knowledge graph", "embedding", "classification",
            "regression", "accuracy", "precision", "recall", "F1"
        ]
        for kw in keywords:
            if kw.lower() in text.lower() and kw not in seen:
                seen.add(kw)
                entities.append({
                    "entity": kw,
                    "type": "CONCEPT",
                    "description": f"Key term: {kw}"
                })

        return entities[:self._MAX_RULE_ENTITIES]

    def _rule_extract_relations(self, text: str, entities: List[Dict]) -> List[Dict]:
        """Simple co-occurrence-based relation extraction fallback."""
        relations = []
        entity_names = [e["entity"] for e in entities]
        sentences = re.split(r'[.!?]', text)

        for sentence in sentences:
            found = [e for e in entity_names if e.lower() in sentence.lower()]
            for i in range(len(found) - 1):
                relations.append({
                    "subject": found[i],
                    "predicate": "co-occurs-with",
                    "object": found[i + 1],
                    "confidence": 0.5,
                })

        return relations[:50]

    # ------------------------------------------------------------------
    # Graph builder
    # ------------------------------------------------------------------

    def _build_graph(self, entities: List[Dict], relations: List[Dict]) -> Dict:
        """Build a simple node/edge graph structure."""
        nodes: Dict[str, Dict] = {}
        # Map from original entity label to its unique node ID
        label_to_id: Dict[str, str] = {}

        def _register_node(label: str, etype: str = "CONCEPT", desc: str = "") -> str:
            """Return a unique node ID for the given label, creating it if needed."""
            if label in label_to_id:
                return label_to_id[label]
            base_id = self._safe_id(label)
            node_id = base_id
            counter = 1
            while node_id in nodes:
                node_id = f"{base_id}_{counter}"
                counter += 1
            nodes[node_id] = {
                "id": node_id,
                "label": label,
                "type": etype,
                "description": desc,
            }
            label_to_id[label] = node_id
            return node_id

        for e in entities:
            _register_node(e["entity"], e.get("type", "CONCEPT"), e.get("description", ""))

        edges = []
        for r in relations:
            src = _register_node(r["subject"])
            dst = _register_node(r["object"])
            edges.append({
                "source": src,
                "target": dst,
                "label": r.get("predicate", "related-to"),
                "confidence": r.get("confidence", 1.0),
            })

        return {"nodes": list(nodes.values()), "edges": edges}

    @staticmethod
    def _safe_id(text: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_]', '_', text.strip()).lower()

    @staticmethod
    def _parse_json_list(raw: str, fallback: list) -> list:
        """Extract the first JSON array from a raw string."""
        # Strip markdown code fences if present
        raw = re.sub(r'```(?:json)?', '', raw).strip()
        # Find the JSON array
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return fallback


# ---------------------------------------------------------------------------
# KGSerializer
# ---------------------------------------------------------------------------

class KGSerializer:
    """
    Serialise a knowledge graph into RDF (Turtle), JSON-LD, or GraphML.
    """

    def to_json_ld(self, kg: Dict) -> str:
        """Serialise to JSON-LD format."""
        graph_entries = []
        for node in kg.get("graph", {}).get("nodes", []):
            graph_entries.append({
                "@id": f"http://research-assistant.local/entity/{node['id']}",
                "@type": f"http://research-assistant.local/type/{node['type']}",
                "http://www.w3.org/2000/01/rdf-schema#label": node["label"],
                "http://purl.org/dc/terms/description": node.get("description", ""),
            })

        for edge in kg.get("graph", {}).get("edges", []):
            graph_entries.append({
                "@type": "http://www.w3.org/1999/02/22-rdf-syntax-ns#Statement",
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#subject": {
                    "@id": f"http://research-assistant.local/entity/{edge['source']}"
                },
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate": edge["label"],
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#object": {
                    "@id": f"http://research-assistant.local/entity/{edge['target']}"
                },
                "http://research-assistant.local/confidence": edge.get("confidence", 1.0),
            })

        doc = {
            "@context": {
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "dc": "http://purl.org/dc/terms/",
                "ra": "http://research-assistant.local/",
            },
            "@graph": graph_entries,
        }
        return json.dumps(doc, indent=2)

    def to_rdf_turtle(self, kg: Dict) -> str:
        """Serialise to RDF Turtle format using rdflib."""
        try:
            import rdflib
            from rdflib import Graph, Literal, Namespace, URIRef
            from rdflib.namespace import RDF, RDFS, XSD

            RA = Namespace("http://research-assistant.local/")
            g = Graph()
            g.bind("ra", RA)

            for node in kg.get("graph", {}).get("nodes", []):
                subj = RA[f"entity/{node['id']}"]
                g.add((subj, RDF.type, RA[f"type/{node['type']}"]))
                g.add((subj, RDFS.label, Literal(node["label"])))
                if node.get("description"):
                    g.add((subj, RA.description, Literal(node["description"])))

            for i, edge in enumerate(kg.get("graph", {}).get("edges", [])):
                stmt = RA[f"statement/{i}"]
                g.add((stmt, RDF.type, RDF.Statement))
                g.add((stmt, RDF.subject, RA[f"entity/{edge['source']}"]))
                g.add((stmt, RDF.predicate, RA[edge["label"].replace(" ", "_")]))
                g.add((stmt, RDF.object, RA[f"entity/{edge['target']}"]))
                g.add((stmt, RA.confidence, Literal(edge.get("confidence", 1.0), datatype=XSD.float)))

            return g.serialize(format="turtle")
        except ImportError:
            return "# rdflib not available; install it with: pip install rdflib\n"

    def to_graphml(self, kg: Dict) -> str:
        """Serialise to GraphML format using networkx."""
        try:
            import networkx as nx
            import io

            G = nx.DiGraph()

            for node in kg.get("graph", {}).get("nodes", []):
                G.add_node(
                    node["id"],
                    label=node["label"],
                    type=node.get("type", "CONCEPT"),
                    description=node.get("description", ""),
                )

            for edge in kg.get("graph", {}).get("edges", []):
                G.add_edge(
                    edge["source"],
                    edge["target"],
                    label=edge.get("label", "related-to"),
                    confidence=edge.get("confidence", 1.0),
                )

            buf = io.BytesIO()
            nx.write_graphml(G, buf)
            return buf.getvalue().decode("utf-8")
        except ImportError:
            return "<!-- networkx not available; install it with: pip install networkx -->\n"

    def serialize(self, kg: Dict, fmt: str = "json-ld") -> Tuple[str, str]:
        """
        Serialise the KG.

        Parameters
        ----------
        kg  : dict returned by KnowledgeGraphBuilder.build()
        fmt : "json-ld" | "rdf" | "graphml"

        Returns
        -------
        (content: str, mime_type: str)
        """
        fmt = fmt.lower()
        if fmt == "rdf":
            return self.to_rdf_turtle(kg), "text/turtle"
        elif fmt == "graphml":
            return self.to_graphml(kg), "application/xml"
        else:
            return self.to_json_ld(kg), "application/ld+json"


# ---------------------------------------------------------------------------
# KGRetrieval
# ---------------------------------------------------------------------------

class KGRetrieval:
    """
    Knowledge Graph Retrieval Module – uses KG context to improve answers.
    """

    def answer(
        self,
        kg: Dict,
        question: str,
        groq_api_key: Optional[str] = None,
        groq_model: str = "llama3-8b-8192",
    ) -> str:
        """
        Answer a question using the knowledge graph as grounding context.
        """
        kg_context = self._build_context(kg)

        if groq_api_key:
            return self._groq_answer(question, kg_context, groq_api_key, groq_model)

        return self._rule_answer(question, kg)

    def _build_context(self, kg: Dict) -> str:
        """Build a compact textual representation of the KG for the LLM."""
        lines = []
        for e in kg.get("entities", [])[:20]:
            lines.append(f"- Entity: {e['entity']} ({e.get('type','?')}): {e.get('description','')}")
        for r in kg.get("relations", [])[:30]:
            conf = r.get("confidence", 1.0)
            lines.append(
                f"- Relation [{conf:.2f}]: {r['subject']} --[{r['predicate']}]--> {r['object']}"
            )
        return "\n".join(lines)

    def _groq_answer(
        self,
        question: str,
        kg_context: str,
        groq_api_key: str,
        groq_model: str,
    ) -> str:
        from groq import Groq
        client = Groq(api_key=groq_api_key)
        completion = client.chat.completions.create(
            model=groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant with access to a knowledge graph. "
                        "Use the provided graph context to give accurate, grounded answers. "
                        "Always cite which entities or relations support your answer."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Knowledge Graph Context:\n{kg_context}\n\n"
                        f"Question: {question}"
                    ),
                },
            ],
            max_tokens=600,
            temperature=0.3,
        )
        return completion.choices[0].message.content.strip()

    def _rule_answer(self, question: str, kg: Dict) -> str:
        """Simple keyword-matching fallback when no LLM is available."""
        q_lower = question.lower()
        relevant = []

        for e in kg.get("entities", []):
            if any(w in q_lower for w in e["entity"].lower().split()):
                relevant.append(f"Entity: {e['entity']} – {e.get('description', '')}")

        for r in kg.get("relations", []):
            if any(w in q_lower for w in (r["subject"] + " " + r["object"]).lower().split()):
                relevant.append(
                    f"Relation: {r['subject']} --[{r['predicate']}]--> {r['object']}"
                )

        if relevant:
            return "Based on the knowledge graph:\n" + "\n".join(relevant[:10])

        return (
            "No directly relevant information found in the knowledge graph for this question. "
            "Try adding a Groq API key for intelligent retrieval."
        )
