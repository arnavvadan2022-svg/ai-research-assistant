#!/usr/bin/env python3
"""
Example script demonstrating how to use the Quantum Chatbot API.

This script shows how to:
1. Register a user
2. Login and get an authentication token
3. Query the quantum chatbot
4. Handle responses

Note: Run the Flask server (python app.py) before running this script.
"""

import requests
import json
import sys

# API base URL (adjust if server runs on a different host/port)
BASE_URL = "http://localhost:5000/api"


def register_user(username, email, password):
    """Register a new user."""
    url = f"{BASE_URL}/register"
    data = {
        "username": username,
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 400:
            # User might already exist, try logging in
            return None
        else:
            print(f"Registration failed: {response.json()}")
            return None
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to server. Make sure the Flask app is running.")
        sys.exit(1)


def login_user(email, password):
    """Login and get authentication token."""
    url = f"{BASE_URL}/login"
    data = {
        "email": email,
        "password": password
    }
    
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Login failed: {response.json()}")
        return None


def query_quantum_chatbot(token, query, max_papers=10, max_web_results=5):
    """Query the quantum chatbot."""
    url = f"{BASE_URL}/quantum/chat"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    data = {
        "query": query,
        "max_papers": max_papers,
        "max_web_results": max_web_results
    }
    
    response = requests.post(url, json=data, headers=headers)
    return response.json()


def print_response(response):
    """Pretty print the chatbot response."""
    print("\n" + "=" * 70)
    if response.get('success'):
        print("✓ Query successful!")
        print("=" * 70)
        print(f"\nQuery: {response['query']}")
        print(f"\nSources:")
        print(f"  - Papers found: {response['sources_count']['papers']}")
        print(f"  - Web results found: {response['sources_count']['web_results']}")
        print(f"\nAnswer:\n")
        print(response['answer'])
    else:
        print("✗ Query failed!")
        print("=" * 70)
        print(f"\nError: {response.get('error', 'Unknown error')}")
    print("=" * 70 + "\n")


def main():
    """Main function demonstrating the quantum chatbot API."""
    print("\n" + "=" * 70)
    print("QUANTUM CHATBOT API EXAMPLE")
    print("=" * 70 + "\n")
    
    # Step 1: Register or login
    email = "quantum_user@example.com"
    password = "secure_password_123"
    username = "quantum_researcher"
    
    print("Step 1: Authenticating...")
    
    # Try to register (will fail if user exists)
    result = register_user(username, email, password)
    
    if result:
        print(f"✓ User registered: {username}")
        token = result['token']
    else:
        # If registration failed, try login
        print("User already exists, logging in...")
        result = login_user(email, password)
        if result:
            print(f"✓ Logged in: {username}")
            token = result['token']
        else:
            print("✗ Authentication failed")
            return
    
    # Step 2: Query the quantum chatbot with valid queries
    print("\n" + "-" * 70)
    print("Step 2: Querying the Quantum Chatbot")
    print("-" * 70)
    
    # Valid quantum queries
    quantum_queries = [
        "What is quantum entanglement?",
        "Explain Shor's algorithm for integer factorization",
        "How do superconducting qubits work?",
    ]
    
    for query in quantum_queries:
        print(f"\nQuerying: '{query}'")
        response = query_quantum_chatbot(token, query, max_papers=3, max_web_results=2)
        print_response(response)
    
    # Step 3: Test with an invalid (non-quantum) query
    print("\n" + "-" * 70)
    print("Step 3: Testing with non-quantum query (should be rejected)")
    print("-" * 70)
    
    invalid_query = "What is machine learning?"
    print(f"\nQuerying: '{invalid_query}'")
    response = query_quantum_chatbot(token, invalid_query)
    print_response(response)
    
    print("✓ Example completed!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
