"""
Quantum Query Validator
Validates if user queries are related to quantum computing or quantum mechanics.
"""

from typing import Dict, List
import re


class QuantumValidator:
    def __init__(self):
        # Core quantum computing and quantum mechanics keywords
        self.quantum_keywords = {
            # Quantum Computing
            'quantum', 'qubit', 'qubits', 'superposition', 'entanglement', 
            'quantum computing', 'quantum computer', 'quantum algorithm', 
            'quantum gate', 'quantum gates', 'quantum circuit', 'quantum circuits',
            'quantum supremacy', 'quantum advantage', 'quantum error correction',
            'quantum cryptography', 'qec', 'nisq',
            
            # Quantum Algorithms
            'shor', "shor's algorithm", 'grover', "grover's algorithm",
            'quantum fourier transform', 'qft', 'vqe', 'qaoa',
            'variational quantum eigensolver', 'quantum approximate optimization',
            
            # Quantum Hardware
            'quantum processor', 'quantum chip', 'superconducting qubit',
            'ion trap', 'photonic quantum', 'topological qubit',
            'quantum annealing', 'quantum simulator',
            
            # Quantum Mechanics
            'quantum mechanics', 'quantum physics', 'wave function', 'wavefunction',
            'quantum state', 'quantum states', 'quantum system', 'quantum systems',
            'quantum theory', 'quantum field theory', 'qft', 
            'schrodinger', 'heisenberg', 'uncertainty principle',
            'quantum measurement', 'quantum observable', 'quantum operator',
            'quantum tunneling', 'quantum coherence', 'decoherence',
            
            # Quantum Information
            'quantum information', 'quantum communication', 'quantum teleportation',
            'quantum key distribution', 'qkd', 'quantum channel',
            'quantum entropy', 'von neumann entropy',
            
            # Quantum Materials
            'quantum material', 'quantum materials', 'quantum dot', 'quantum dots',
            'quantum well', 'quantum wire', 'topological insulator',
            'majorana fermion', 'quantum hall effect',
            
            # Specific quantum phenomena
            'bell state', 'bell inequality', 'epr paradox', 'no-cloning theorem',
            'quantum interference', 'quantum phase', 'bloch sphere',
            'pauli matrices', 'clifford gates', 'hadamard gate',
            'cnot gate', 't gate', 'toffoli gate'
        }
        
        # Suggested topics for non-quantum queries
        self.suggested_topics = [
            "quantum entanglement and Bell's theorem",
            "quantum algorithms (Shor's, Grover's, VQE, QAOA)",
            "quantum error correction and fault-tolerant quantum computing",
            "quantum supremacy and quantum advantage",
            "qubits and quantum gates",
            "superposition and quantum measurement",
            "quantum cryptography and quantum key distribution",
            "quantum computing hardware (superconducting, ion trap, photonic)",
            "quantum mechanics fundamentals",
            "quantum field theory",
            "topological quantum computing",
            "quantum annealing and optimization",
            "NISQ (Noisy Intermediate-Scale Quantum) devices",
            "quantum simulation and quantum chemistry"
        ]
    
    def validate(self, query: str) -> Dict:
        """
        Validate if the query is quantum-related.
        
        Args:
            query: User's question/query
            
        Returns:
            Dictionary with validation results
        """
        query_lower = query.lower()
        
        # Check for quantum keywords
        matched_keywords = []
        for keyword in self.quantum_keywords:
            if keyword in query_lower:
                matched_keywords.append(keyword)
        
        is_quantum = len(matched_keywords) > 0
        confidence = min(len(matched_keywords) * 0.3, 1.0)  # Confidence score
        
        return {
            'is_quantum': is_quantum,
            'confidence': confidence,
            'matched_keywords': matched_keywords,
            'suggested_topics': [] if is_quantum else self.get_suggested_topics()
        }
    
    def get_suggested_topics(self, count: int = 8) -> List[str]:
        """
        Get suggested quantum topics.
        
        Args:
            count: Number of topics to return
            
        Returns:
            List of suggested topic strings
        """
        return self.suggested_topics[:count]
    
    def get_rejection_message(self) -> str:
        """
        Get a polite rejection message for non-quantum queries.
        
        Returns:
            Rejection message string
        """
        topics = self.get_suggested_topics(6)
        topics_list = "\n".join([f"  • {topic}" for topic in topics])
        
        return f"""I'm a specialized Quantum Computing & Quantum Mechanics Assistant. I can only help with questions related to quantum topics.

Your question doesn't appear to be related to quantum computing or quantum mechanics.

Here are some quantum topics I can help you with:
{topics_list}

Please ask a question related to quantum computing or quantum mechanics!"""
