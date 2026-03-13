from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from utils.database import Database
from utils.paper_search import PaperSearch
from utils.ai_processor import AIProcessor
from utils.knowledge_graph import KnowledgeGraphBuilder, KGSerializer
from utils.dataset_generator import DatasetGenerator
from utils.evaluation import EvaluationFramework
import jwt

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

db = Database()
paper_search = PaperSearch()
ai_processor = AIProcessor()
kg_builder = KnowledgeGraphBuilder()
kg_serializer = KGSerializer()
dataset_generator = DatasetGenerator()
evaluation_framework = EvaluationFramework()


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


# ---------------------------------------------------------------------------
# Knowledge Graph endpoints
# ---------------------------------------------------------------------------

@app.route('/api/knowledge-graph', methods=['POST'])
@token_required
def build_knowledge_graph(current_user):
    """Build a knowledge graph from document text using Groq."""
    try:
        data = request.get_json()
        text = data.get('text')
        context = data.get('context', '')

        if not text:
            return jsonify({'error': 'text is required'}), 400

        print(f"Building knowledge graph for user: {current_user['id']}")
        kg = kg_builder.build(text, context)

        return jsonify({
            'knowledge_graph': kg,
            'message': 'Knowledge graph built successfully',
        }), 200
    except Exception as e:
        print(f"KG build error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/knowledge-graph/export', methods=['POST'])
@token_required
def export_knowledge_graph(current_user):
    """Export a knowledge graph in RDF, JSON-LD, or GraphML format."""
    try:
        data = request.get_json()
        kg = data.get('knowledge_graph')
        fmt = data.get('format', 'json-ld').lower()

        if not kg:
            return jsonify({'error': 'knowledge_graph is required'}), 400

        allowed_formats = {'json-ld', 'rdf', 'graphml'}
        if fmt not in allowed_formats:
            return jsonify({
                'error': f'format must be one of: {", ".join(allowed_formats)}'
            }), 400

        content, mime_type = kg_serializer.serialize(kg, fmt)
        return jsonify({
            'content': content,
            'format': fmt,
            'mime_type': mime_type,
        }), 200
    except Exception as e:
        print(f"KG export error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/knowledge-graph/query', methods=['POST'])
@token_required
def query_knowledge_graph(current_user):
    """Query the knowledge graph to obtain improved, grounded answers."""
    try:
        data = request.get_json()
        kg = data.get('knowledge_graph')
        question = data.get('question')

        if not kg or not question:
            return jsonify({'error': 'knowledge_graph and question are required'}), 400

        print(f"KG query from user {current_user['id']}: {question}")
        answer = kg_builder.query(kg, question)

        return jsonify({
            'question': question,
            'answer': answer,
        }), 200
    except Exception as e:
        print(f"KG query error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Dataset generation endpoint
# ---------------------------------------------------------------------------

@app.route('/api/dataset', methods=['POST'])
@token_required
def generate_dataset(current_user):
    """Generate a training dataset from a knowledge graph."""
    try:
        data = request.get_json()
        kg = data.get('knowledge_graph')
        source_text = data.get('text', '')
        fmt = data.get('format', 'json').lower()

        if not kg:
            return jsonify({'error': 'knowledge_graph is required'}), 400

        allowed_formats = {'json', 'csv'}
        if fmt not in allowed_formats:
            return jsonify({
                'error': f'format must be one of: {", ".join(allowed_formats)}'
            }), 400

        records = dataset_generator.generate(kg, source_text)

        if fmt == 'csv':
            content = dataset_generator.to_csv(records)
        else:
            content = dataset_generator.to_json(records)

        return jsonify({
            'content': content,
            'format': fmt,
            'record_count': len(records),
            'message': 'Dataset generated successfully',
        }), 200
    except Exception as e:
        print(f"Dataset generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Evaluation endpoint
# ---------------------------------------------------------------------------

@app.route('/api/evaluate', methods=['POST'])
@token_required
def evaluate(current_user):
    """Evaluate a knowledge graph (optionally against a reference)."""
    try:
        data = request.get_json()
        kg = data.get('knowledge_graph')
        reference = data.get('reference_kg', None)

        if not kg:
            return jsonify({'error': 'knowledge_graph is required'}), 400

        metrics = evaluation_framework.evaluate_kg(kg, reference)

        return jsonify({
            'metrics': metrics,
            'message': 'Evaluation completed',
        }), 200
    except Exception as e:
        print(f"Evaluation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Starting AI Research Assistant")
    print("=" * 50)
    db.init_db()
    print("=" * 50)
    print("✅ Server ready!")
    print("🌐 Open: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=os.getenv('DEBUG', 'False') == 'True')