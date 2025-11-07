#!/usr/bin/env python3
"""
Test script for the Quantum Computing Chatbot

This script demonstrates the functionality of the quantum chatbot including:
- Query validation
- Paper search (mocked if arXiv unavailable)
- Response synthesis
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.quantum_chatbot import QuantumChatbot


def test_query_validation():
    """Test the query validation functionality."""
    print("=" * 60)
    print("TEST 1: Query Validation")
    print("=" * 60)
    
    bot = QuantumChatbot()
    
    test_cases = [
        # Valid quantum queries
        ("What is quantum entanglement?", True),
        ("Explain Shor's algorithm for factoring", True),
        ("How do superconducting qubits work?", True),
        ("What is quantum teleportation?", True),
        ("Describe the uncertainty principle", True),
        ("What are quantum computers?", True),
        
        # Invalid non-quantum queries
        ("What is machine learning?", False),
        ("Tell me about deep learning", False),
        ("How does a classical computer work?", False),
        ("What is blockchain?", False),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_valid in test_cases:
        is_valid, reason = bot.validate_query(query)
        
        if is_valid == expected_valid:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1
        
        valid_str = "VALID" if is_valid else "INVALID"
        expected_str = "VALID" if expected_valid else "INVALID"
        
        print(f"{status}: '{query[:50]}...' => {valid_str} (expected {expected_str})")
    
    print(f"\nResults: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    return failed == 0


def test_synthesis():
    """Test the response synthesis functionality."""
    print("\n" + "=" * 60)
    print("TEST 2: Response Synthesis")
    print("=" * 60)
    
    bot = QuantumChatbot()
    
    # Mock papers data
    mock_papers = [
        {
            'id': '2401.12345',
            'title': 'Quantum Entanglement in Multi-Qubit Systems',
            'authors': ['Alice Smith', 'Bob Johnson', 'Carol Williams'],
            'abstract': 'We study quantum entanglement properties in multi-qubit systems. Our results show that entanglement can be maintained over longer distances using novel error correction techniques. This has implications for quantum communication and quantum computing applications.',
            'url': 'https://arxiv.org/abs/2401.12345',
            'published': '2024-01-15',
        },
        {
            'id': '2401.67890',
            'title': 'Efficient Quantum Algorithms for Optimization Problems',
            'authors': ['David Lee', 'Emma Davis'],
            'abstract': 'We present new quantum algorithms for solving combinatorial optimization problems. The algorithms demonstrate quadratic speedup over classical approaches.',
            'url': 'https://arxiv.org/abs/2401.67890',
            'published': '2024-01-20',
        }
    ]
    
    # Mock web results
    mock_web = [
        {
            'title': 'Understanding Quantum Entanglement - Physics Today',
            'link': 'https://example.com/quantum-entanglement',
            'snippet': 'Quantum entanglement is a phenomenon where particles become correlated in such a way that the state of one particle cannot be described independently of the others.',
            'source': 'Physics Today'
        }
    ]
    
    query = "quantum entanglement"
    response = bot.synthesize_response(query, mock_papers, mock_web)
    
    print(f"Query: {response['query']}")
    print(f"Papers found: {response['sources_count']['papers']}")
    print(f"Web results found: {response['sources_count']['web_results']}")
    print(f"\nSynthesized answer length: {len(response['answer'])} characters")
    print(f"\nFirst 300 characters of answer:")
    print(response['answer'][:300] + "...")
    
    # Verify response structure
    assert 'query' in response, "Response missing 'query' field"
    assert 'answer' in response, "Response missing 'answer' field"
    assert 'papers' in response, "Response missing 'papers' field"
    assert 'web_results' in response, "Response missing 'web_results' field"
    assert 'sources_count' in response, "Response missing 'sources_count' field"
    
    print("\n✓ Response synthesis test passed!")
    return True


def test_process_query():
    """Test the complete query processing pipeline."""
    print("\n" + "=" * 60)
    print("TEST 3: Complete Query Processing")
    print("=" * 60)
    
    bot = QuantumChatbot()
    
    # Test with valid quantum query
    print("\nTest 3a: Valid quantum query")
    query = "quantum computing algorithms"
    result = bot.process_query(query, max_papers=3, max_web_results=2)
    
    print(f"Query: {query}")
    print(f"Success: {result.get('success')}")
    
    if result.get('success'):
        print(f"Papers retrieved: {result['sources_count']['papers']}")
        print(f"Web results retrieved: {result['sources_count']['web_results']}")
        print("✓ Valid query processed successfully")
    else:
        print(f"Note: {result.get('error', 'No results (external APIs may be unavailable)')}")
    
    # Test with invalid non-quantum query
    print("\nTest 3b: Invalid non-quantum query")
    invalid_query = "machine learning algorithms"
    result = bot.process_query(invalid_query, max_papers=3, max_web_results=2)
    
    print(f"Query: {invalid_query}")
    print(f"Success: {result.get('success')}")
    
    if not result.get('success'):
        print(f"Error (as expected): {result.get('error', '')[:100]}...")
        print("✓ Invalid query correctly rejected")
    else:
        print("✗ Invalid query was not rejected!")
        return False
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("QUANTUM CHATBOT TEST SUITE")
    print("=" * 60 + "\n")
    
    all_passed = True
    
    try:
        # Run tests
        all_passed &= test_query_validation()
        all_passed &= test_synthesis()
        all_passed &= test_process_query()
        
        # Summary
        print("\n" + "=" * 60)
        if all_passed:
            print("✓ ALL TESTS PASSED!")
        else:
            print("✗ SOME TESTS FAILED")
        print("=" * 60 + "\n")
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n✗ TEST SUITE FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
