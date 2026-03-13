import json
import re
import xml.etree.ElementTree as ET
from typing import Dict, List
from urllib.parse import quote


# RDF prefix used for all KG resources
_NS = "http://ai-research-assistant/kg/"


class KGSerializer:
    """
    Serialises a KG (as returned by KGBuilder.build_graph) into three
    standard formats:
      - RDF  (Turtle syntax)
      - JSON-LD
      - GraphML
    """

    # ─────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────

    def serialize(self, graph_data: Dict, fmt: str) -> str:
        """
        Dispatch to the right serialiser.
        fmt must be one of: 'rdf', 'json-ld', 'graphml'
        """
        fmt = fmt.lower().replace('_', '-')
        dispatch = {
            'rdf':     self.to_rdf,
            'json-ld': self.to_json_ld,
            'graphml': self.to_graphml,
        }
        if fmt not in dispatch:
            raise ValueError(
                f"Unsupported format '{fmt}'. Choose from: rdf, json-ld, graphml"
            )
        return dispatch[fmt](graph_data)

    # ── RDF / Turtle ──────────────────────────

    def to_rdf(self, graph_data: Dict) -> str:
        """
        Produce a Turtle-formatted RDF document.  No external library
        dependency required – we build the Turtle string directly so that
        the serialiser works even when rdflib is not installed.
        """
        entities: List[Dict] = graph_data.get('entities', [])
        relations: List[Dict] = graph_data.get('relations', [])

        lines: List[str] = [
            "@prefix kg: <{ns}> .".format(ns=_NS),
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "",
        ]

        # Entity declarations
        for ent in entities:
            uri = self._uri(ent['text'])
            lines += [
                f"kg:{uri}",
                f'    rdfs:label "{self._escape_ttl(ent["text"])}" ;',
                f'    kg:entityType "{ent["type"]}" ;',
                f'    kg:confidence "{ent["confidence"]}"^^xsd:decimal ;',
                f'    kg:occurrences "{ent["occurrences"]}"^^xsd:integer .',
                "",
            ]

        # Relation triples
        for rel in relations:
            subj = self._uri(rel['subject'])
            obj  = self._uri(rel['object'])
            pred = self._uri(rel['predicate'])
            lines += [
                f"kg:{subj}",
                f'    kg:{pred} kg:{obj} ;',
                f'    kg:relationConfidence "{rel["confidence"]}"^^xsd:decimal .',
                "",
            ]

        return "\n".join(lines)

    # ── JSON-LD ───────────────────────────────

    def to_json_ld(self, graph_data: Dict) -> str:
        """
        Produce a JSON-LD document.
        """
        entities: List[Dict] = graph_data.get('entities', [])
        relations: List[Dict] = graph_data.get('relations', [])

        context = {
            "@vocab": _NS,
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "label":      "rdfs:label",
            "entityType": {"@id": "entityType"},
            "confidence": {"@id": "confidence", "@type": "xsd:decimal"},
            "occurrences": {"@id": "occurrences", "@type": "xsd:integer"},
        }

        graph_nodes = []

        # Entity nodes
        for ent in entities:
            node: Dict = {
                "@id": _NS + self._uri(ent['text']),
                "@type": "Entity",
                "label":       ent['text'],
                "entityType":  ent['type'],
                "confidence":  ent['confidence'],
                "occurrences": ent['occurrences'],
            }
            graph_nodes.append(node)

        # Relation nodes (reified for richer representation)
        for idx, rel in enumerate(relations):
            node = {
                "@id": _NS + f"relation_{idx}",
                "@type": "Relation",
                "subject":    {"@id": _NS + self._uri(rel['subject'])},
                "predicate":  rel['predicate'],
                "object":     {"@id": _NS + self._uri(rel['object'])},
                "confidence": rel['confidence'],
                "sentence":   rel.get('sentence', ''),
            }
            graph_nodes.append(node)

        document = {
            "@context": context,
            "@graph": graph_nodes,
            "stats": graph_data.get('stats', {}),
        }
        return json.dumps(document, indent=2, ensure_ascii=False)

    # ── GraphML ───────────────────────────────

    def to_graphml(self, graph_data: Dict) -> str:
        """
        Produce a GraphML XML document compatible with Gephi / Cytoscape.
        """
        entities: List[Dict] = graph_data.get('entities', [])
        relations: List[Dict] = graph_data.get('relations', [])

        root = ET.Element('graphml', {
            'xmlns':              'http://graphml.graphdrawing.org/graphml',
            'xmlns:xsi':          'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation': (
                'http://graphml.graphdrawing.org/graphml '
                'http://graphml.graphdrawing.org/graphml/1.0/graphml.xsd'
            ),
        })

        # Key declarations
        def _key(id_, for_, name, typ):
            ET.SubElement(root, 'key', {
                'id': id_, 'for': for_,
                'attr.name': name, 'attr.type': typ,
            })

        _key('label',       'node', 'label',       'string')
        _key('entityType',  'node', 'entityType',  'string')
        _key('confidence',  'node', 'confidence',  'double')
        _key('occurrences', 'node', 'occurrences', 'int')
        _key('predicate',   'edge', 'predicate',   'string')
        _key('edgeConf',    'edge', 'confidence',  'double')

        graph_el = ET.SubElement(root, 'graph', {
            'id':          'G',
            'edgedefault': 'directed',
        })

        # Nodes
        entity_index = {e['text']: i for i, e in enumerate(entities)}
        for ent in entities:
            n = ET.SubElement(graph_el, 'node', {
                'id': f"n{entity_index[ent['text']]}",
            })
            self._data_el(n, 'label',       ent['text'])
            self._data_el(n, 'entityType',  ent['type'])
            self._data_el(n, 'confidence',  str(ent['confidence']))
            self._data_el(n, 'occurrences', str(ent['occurrences']))

        # Edges
        for idx, rel in enumerate(relations):
            src = entity_index.get(rel['subject'])
            tgt = entity_index.get(rel['object'])
            if src is None or tgt is None:
                continue
            e = ET.SubElement(graph_el, 'edge', {
                'id':     f"e{idx}",
                'source': f"n{src}",
                'target': f"n{tgt}",
            })
            self._data_el(e, 'predicate', rel['predicate'])
            self._data_el(e, 'edgeConf',  str(rel['confidence']))

        ET.indent(root, space='  ')
        return ET.tostring(root, encoding='unicode', xml_declaration=True)

    # ─────────────────────────────────────────
    #  Private helpers
    # ─────────────────────────────────────────

    @staticmethod
    def _uri(text: str) -> str:
        """Convert free text to a safe URI fragment."""
        safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', text)
        return safe.strip('_') or 'unknown'

    @staticmethod
    def _escape_ttl(text: str) -> str:
        return text.replace('\\', '\\\\').replace('"', '\\"')

    @staticmethod
    def _data_el(parent: ET.Element, key: str, value: str):
        d = ET.SubElement(parent, 'data', {'key': key})
        d.text = value
