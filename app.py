from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from utils.database import Database
from utils.paper_search import PaperSearch
from utils.serp_search import SerpSearch
from utils.quantum_validator import QuantumValidator
from utils.quantum_ai_processor import QuantumAIProcessor
from utils.conversation_manager import ConversationManager
import jwt

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

db = Database()
paper_search = PaperSearch()
serp_search = SerpSearch()
quantum_validator = QuantumValidator()
ai_processor = QuantumAIProcessor()
conversation_manager = ConversationManager(db)


# Authentication decorator
def token_required(f):
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            token = token.split(' ')[1] if ' ' in token else token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = db.get_user_by_id(data['user_id'])
            if not current_user:
                return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'error': 'Invalid token', 'message': str(e)}), 401
        return f(current_user, *args, **kwargs)

    decorator.__name__ = f.__name__
    return decorator


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not all([username, email, password]):
            return jsonify({'error': 'All fields are required'}), 400

        # Check if user exists
        if db.get_user_by_email(email):
            return jsonify({'error': 'Email already registered'}), 400

        # Create user
        hashed_password = generate_password_hash(password)
        user_id = db.create_user(username, email, hashed_password)

        # Generate token
        token = jwt.encode({
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(days=30)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user': {'id': user_id, 'username': username, 'email': email}
        }), 201
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not all([email, password]):
            return jsonify({'error': 'Email and password required'}), 400

        user = db.get_user_by_email(email)
        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': 'Invalid credentials'}), 401

        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.utcnow() + timedelta(days=30)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {'id': user['id'], 'username': user['username'], 'email': user['email']}
        }), 200
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
@token_required
def quantum_chat(current_user):
    """
    Main quantum chatbot endpoint.
    Validates quantum query, fetches sources, generates answer.
    """
    try:
        data = request.get_json()
        question = data.get('question')
        session_id = data.get('session_id')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        if app.config.get('DEBUG'):
            print(f"💬 Quantum chat question from user {current_user['id']}")
        
        # Create new session if not provided
        if not session_id:
            session_id = conversation_manager.create_session(current_user['id'])
            print(f"📝 Created new session: {session_id}")
        
        # Save user message
        conversation_manager.add_message(session_id, current_user['id'], 'user', question)
        
        # Validate if question is quantum-related
        validation = quantum_validator.validate(question)
        
        if not validation['is_quantum']:
            # Not a quantum question - politely decline
            rejection_message = quantum_validator.get_rejection_message()
            conversation_manager.add_message(
                session_id, current_user['id'], 'assistant', rejection_message
            )
            
            return jsonify({
                'session_id': session_id,
                'answer': rejection_message,
                'is_quantum': False,
                'suggested_topics': validation['suggested_topics'],
                'sources': []
            }), 200
        
        print(f"✅ Quantum query validated (confidence: {validation['confidence']})")
        
        # Fetch sources in parallel
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        arxiv_papers = []
        web_results = []
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_arxiv = executor.submit(paper_search.search, question, 5)
            future_web = executor.submit(serp_search.search, question, 5)
            
            for future in as_completed([future_arxiv, future_web]):
                if future == future_arxiv:
                    arxiv_papers = future.result()
                else:
                    web_results = future.result()
        
        # Get conversation context
        conversation_context = conversation_manager.get_context_for_model(
            session_id, current_user['id'], max_messages=4
        )
        
        # Format sources for AI model
        arxiv_context = paper_search.format_papers_for_context(arxiv_papers)
        web_context = serp_search.format_results_for_context(web_results)
        
        # Generate answer
        answer = ai_processor.generate_answer(
            question, arxiv_context, web_context, conversation_context
        )
        
        # Format sources for response
        sources = conversation_manager.format_sources(arxiv_papers, web_results)
        
        # Add citations to answer
        final_answer = ai_processor.format_answer_with_citations(answer, sources)
        
        # Save assistant message
        conversation_manager.add_message(
            session_id, current_user['id'], 'assistant', final_answer, sources
        )
        
        print(f"✅ Generated answer with {len(sources)} sources")
        
        return jsonify({
            'session_id': session_id,
            'answer': final_answer,
            'is_quantum': True,
            'confidence': validation['confidence'],
            'sources': sources,
            'arxiv_papers': arxiv_papers,
            'web_results': web_results
        }), 200
        
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to process question: {str(e)}'}), 500


@app.route('/api/sessions', methods=['GET'])
@token_required
def get_sessions(current_user):
    """Get all conversation sessions for the user."""
    try:
        sessions = conversation_manager.get_user_sessions(current_user['id'])
        return jsonify({
            'sessions': sessions,
            'count': len(sessions)
        }), 200
    except Exception as e:
        print(f"❌ Get sessions error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>', methods=['GET'])
@token_required
def get_session_history(current_user, session_id):
    """Get conversation history for a specific session."""
    try:
        history = conversation_manager.get_conversation_history(
            session_id, current_user['id']
        )
        return jsonify({
            'session_id': session_id,
            'messages': history,
            'count': len(history)
        }), 200
    except Exception as e:
        print(f"❌ Get history error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
@token_required
def delete_session(current_user, session_id):
    """Delete a conversation session."""
    try:
        success = conversation_manager.delete_session(session_id, current_user['id'])
        if success:
            return jsonify({'message': 'Session deleted successfully'}), 200
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        print(f"❌ Delete session error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate-query', methods=['POST'])
@token_required
def validate_query(current_user):
    """Validate if a query is quantum-related."""
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        validation = quantum_validator.validate(query)
        
        return jsonify({
            'is_quantum': validation['is_quantum'],
            'confidence': validation['confidence'],
            'matched_keywords': validation['matched_keywords'],
            'suggested_topics': validation['suggested_topics']
        }), 200
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/search', methods=['POST'])
@token_required
def search_papers(current_user):
    try:
        data = request.get_json()
        query = data.get('query')
        max_results = data.get('max_results', 10)

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        print(f"Searching for: {query} (max: {max_results})")

        # Search papers
        papers = paper_search.search(query, max_results)

        # Save query history
        db.save_query(current_user['id'], query)

        print(f"Found {len(papers)} papers")

        return jsonify({
            'query': query,
            'results': papers,
            'count': len(papers)
        }), 200
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/summarize', methods=['POST'])
@token_required
def summarize_paper(current_user):
    try:
        data = request.get_json()
        paper_text = data.get('text')
        paper_id = data.get('paper_id')

        if not paper_text:
            return jsonify({'error': 'Text is required'}), 400

        print(f"Generating summary for paper: {paper_id}")

        # Generate summary
        summary = ai_processor.summarize(paper_text)

        print(f"Summary generated successfully")

        # Return the summary without saving to database
        return jsonify({
            'summary': summary,
            'message': 'Summary generated successfully'
        }), 200
    except Exception as e:
        print(f"Summarization error: {str(e)}")
        return jsonify({'error': f'Failed to generate summary: {str(e)}'}), 500


@app.route('/api/papers/save', methods=['POST'])
@token_required
def save_paper(current_user):
    try:
        data = request.get_json()
        paper_id = data.get('paper_id')
        title = data.get('title')
        authors = data.get('authors', [])
        abstract = data.get('abstract')
        url = data.get('url')
        published_date = data.get('published_date')
        summary = data.get('summary', None)

        if not all([paper_id, title, abstract]):
            return jsonify({'error': 'Paper ID, title, and abstract are required'}), 400

        print(f"Saving paper: {paper_id} for user: {current_user['id']}")

        # Save paper to database
        paper_data = {
            'title': title,
            'authors': authors,
            'abstract': abstract,
            'summary': summary,
            'url': url,
            'published_date': published_date
        }

        db_id = db.save_paper(current_user['id'], paper_id, paper_data)

        print(f"Paper saved with ID: {db_id}")

        return jsonify({
            'message': 'Paper saved successfully',
            'id': db_id
        }), 200
    except Exception as e:
        print(f"Save paper error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
@token_required
def analyze_paper(current_user):
    try:
        data = request.get_json()
        paper_text = data.get('text')
        analysis_type = data.get('type', 'general')

        if not paper_text:
            return jsonify({'error': 'Text is required'}), 400

        print(f"Analyzing paper: {analysis_type}")

        # Perform analysis
        analysis = ai_processor.analyze(paper_text, analysis_type)

        return jsonify({
            'analysis': analysis,
            'type': analysis_type
        }), 200
    except Exception as e:
        print(f"Analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/papers', methods=['GET'])
@token_required
def get_saved_papers(current_user):
    try:
        papers = db.get_user_papers(current_user['id'])
        return jsonify({
            'papers': papers,
            'count': len(papers)
        }), 200
    except Exception as e:
        print(f"Get papers error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/papers/<paper_id>', methods=['DELETE'])
@token_required
def delete_paper(current_user, paper_id):
    try:
        db.delete_paper(current_user['id'], paper_id)
        return jsonify({'message': 'Paper deleted successfully'}), 200
    except Exception as e:
        print(f"Delete paper error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
@token_required
def get_query_history(current_user):
    try:
        history = db.get_query_history(current_user['id'])
        return jsonify({
            'history': history,
            'count': len(history)
        }), 200
    except Exception as e:
        print(f"Get history error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }), 200


if __name__ == '__main__':
    print("=" * 50)
    print("🔬 Starting Quantum Computing Assistant")
    print("=" * 50)
    db.init_db()
    print("=" * 50)
    print("✅ Server ready!")
    print("🌐 Open: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=os.getenv('DEBUG', 'False') == 'True')