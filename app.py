from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv
from utils.database import Database
from utils.paper_search import PaperSearch
from utils.ai_processor import AIProcessor
from utils.kg_builder import KGBuilder
from utils.kg_serializer import KGSerializer
from utils.kg_retrieval import KGRetrieval
from utils.dataset_generator import DatasetGenerator
from utils.distillation import DistillationPipeline
import jwt

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

db = Database()
paper_search = PaperSearch()
ai_processor = AIProcessor()
kg_builder = KGBuilder()
kg_serializer = KGSerializer()
dataset_generator = DatasetGenerator()
distillation_pipeline = DistillationPipeline(ai_processor=ai_processor)


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


# ─── Knowledge Graph Endpoints ───────────────────────────────────────────────

@app.route('/api/kg/build', methods=['POST'])
@token_required
def build_knowledge_graph(current_user):
    """
    POST { text, paper_id? }
    → Extract entities, relations, confidence scores and build a KG.
    Persists the KG in the database and returns the full graph data.
    """
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        paper_id = data.get('paper_id')

        if not text:
            return jsonify({'error': 'text is required'}), 400

        graph_data = kg_builder.build_graph(text)
        graph_json = json.dumps(graph_data)

        kg_id = db.save_knowledge_graph(
            user_id=current_user['id'],
            source_text=text[:2000],
            graph_data=graph_json,
            entity_count=graph_data['stats']['entity_count'],
            relation_count=graph_data['stats']['relation_count'],
            source_paper_id=paper_id,
        )

        return jsonify({
            'kg_id':      kg_id,
            'graph_data': graph_data,
            'message':    'Knowledge graph built successfully',
        }), 200
    except Exception as e:
        print(f"KG build error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/kg/<int:kg_id>', methods=['GET'])
@token_required
def get_knowledge_graph(current_user, kg_id):
    """Return a single stored KG."""
    try:
        row = db.get_knowledge_graph(current_user['id'], kg_id)
        if not row:
            return jsonify({'error': 'Knowledge graph not found'}), 404
        row['graph_data'] = json.loads(row['graph_data'])
        return jsonify(row), 200
    except Exception as e:
        print(f"KG get error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/kg', methods=['GET'])
@token_required
def list_knowledge_graphs(current_user):
    """List all KGs for the current user (without full graph_data)."""
    try:
        kgs = db.get_user_knowledge_graphs(current_user['id'])
        return jsonify({'knowledge_graphs': kgs, 'count': len(kgs)}), 200
    except Exception as e:
        print(f"KG list error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/kg/<int:kg_id>', methods=['DELETE'])
@token_required
def delete_knowledge_graph(current_user, kg_id):
    """Delete a KG."""
    try:
        db.delete_knowledge_graph(current_user['id'], kg_id)
        return jsonify({'message': 'Knowledge graph deleted'}), 200
    except Exception as e:
        print(f"KG delete error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/kg/<int:kg_id>/serialize', methods=['POST'])
@token_required
def serialize_knowledge_graph(current_user, kg_id):
    """
    POST { format: 'rdf' | 'json-ld' | 'graphml' }
    → Serialise a stored KG in the requested format.
    """
    try:
        data = request.get_json()
        fmt = data.get('format', 'json-ld').lower()

        row = db.get_knowledge_graph(current_user['id'], kg_id)
        if not row:
            return jsonify({'error': 'Knowledge graph not found'}), 404

        graph_data = json.loads(row['graph_data'])
        serialized = kg_serializer.serialize(graph_data, fmt)

        content_types = {
            'rdf':     'text/turtle',
            'json-ld': 'application/ld+json',
            'graphml': 'application/xml',
        }
        return jsonify({
            'kg_id':        kg_id,
            'format':       fmt,
            'content':      serialized,
            'content_type': content_types.get(fmt, 'text/plain'),
        }), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        print(f"KG serialize error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/kg/<int:kg_id>/retrieve', methods=['POST'])
@token_required
def retrieve_from_knowledge_graph(current_user, kg_id):
    """
    POST { question, base_answer? }
    → Query the KG for relevant triples; optionally improve a base_answer.
    """
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        base_answer = data.get('base_answer', '')

        if not question:
            return jsonify({'error': 'question is required'}), 400

        row = db.get_knowledge_graph(current_user['id'], kg_id)
        if not row:
            return jsonify({'error': 'Knowledge graph not found'}), 404

        graph_data = json.loads(row['graph_data'])
        retrieval = KGRetrieval(graph_data)
        result = retrieval.query(question)

        improved_answer = ''
        if base_answer:
            improved_answer = retrieval.get_improved_answer(question, base_answer)

        return jsonify({
            'kg_id':           kg_id,
            'question':        question,
            'matched_entities': result['matched_entities'],
            'relevant_triples': result['relevant_triples'],
            'context_summary':  result['context_summary'],
            'improved_answer':  improved_answer,
        }), 200
    except Exception as e:
        print(f"KG retrieve error: {e}")
        return jsonify({'error': str(e)}), 500


# ─── Distillation Endpoints ──────────────────────────────────────────────────

@app.route('/api/distill/dataset', methods=['POST'])
@token_required
def generate_distillation_dataset(current_user):
    """
    POST { kg_id, format: 'json'|'jsonl'|'csv', min_confidence?, max_samples? }
    → Generate a training dataset from a stored KG.
    Persists and returns the dataset.
    """
    try:
        data = request.get_json()
        kg_id = data.get('kg_id')
        fmt = data.get('format', 'json').lower()
        min_confidence = float(data.get('min_confidence', 0.60))
        max_samples = int(data.get('max_samples', 500))

        if not kg_id:
            return jsonify({'error': 'kg_id is required'}), 400
        if fmt not in ('json', 'jsonl', 'csv'):
            return jsonify({'error': "format must be 'json', 'jsonl', or 'csv'"}), 400

        row = db.get_knowledge_graph(current_user['id'], int(kg_id))
        if not row:
            return jsonify({'error': 'Knowledge graph not found'}), 404

        graph_data = json.loads(row['graph_data'])
        pairs = dataset_generator.generate_training_pairs(
            graph_data,
            source_text=row.get('source_text', ''),
            min_confidence=min_confidence,
            max_samples=max_samples,
        )

        if fmt == 'json':
            serialized = dataset_generator.to_json(pairs)
        elif fmt == 'jsonl':
            serialized = dataset_generator.to_jsonl(pairs)
        else:
            serialized = dataset_generator.to_csv(pairs)

        stats = dataset_generator.get_stats(pairs)

        ds_id = db.save_kg_dataset(
            user_id=current_user['id'],
            kg_id=int(kg_id),
            dataset_data=serialized,
            fmt=fmt,
            sample_count=len(pairs),
        )

        return jsonify({
            'dataset_id':   ds_id,
            'kg_id':        int(kg_id),
            'format':       fmt,
            'sample_count': len(pairs),
            'stats':        stats,
            'preview':      pairs[:5],
            'message':      'Dataset generated successfully',
        }), 200
    except Exception as e:
        print(f"Dataset generation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distill/dataset/<int:dataset_id>/download', methods=['GET'])
@token_required
def download_dataset(current_user, dataset_id):
    """Return the raw dataset content for download."""
    try:
        row = db.get_kg_dataset(current_user['id'], dataset_id)
        if not row:
            return jsonify({'error': 'Dataset not found'}), 404
        return jsonify({
            'dataset_id': dataset_id,
            'format':     row['format'],
            'content':    row['dataset_data'],
            'sample_count': row['sample_count'],
        }), 200
    except Exception as e:
        print(f"Dataset download error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distill/datasets', methods=['GET'])
@token_required
def list_datasets(current_user):
    """List all generated datasets for the current user."""
    try:
        datasets = db.get_user_datasets(current_user['id'])
        return jsonify({'datasets': datasets, 'count': len(datasets)}), 200
    except Exception as e:
        print(f"Dataset list error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distill/refine', methods=['POST'])
@token_required
def refine_kg_prompt(current_user):
    """
    POST { kg_id, prompt, min_confidence?, max_triples? }
    → Prune a KG and re-inject its top triples into the given prompt.
    """
    try:
        data = request.get_json()
        kg_id = data.get('kg_id')
        prompt = data.get('prompt', '').strip()
        min_confidence = float(data.get('min_confidence', 0.70))
        max_triples = int(data.get('max_triples', 15))

        if not kg_id or not prompt:
            return jsonify({'error': 'kg_id and prompt are required'}), 400

        row = db.get_knowledge_graph(current_user['id'], int(kg_id))
        if not row:
            return jsonify({'error': 'Knowledge graph not found'}), 404

        graph_data = json.loads(row['graph_data'])
        result = distillation_pipeline.refine(
            prompt, graph_data,
            min_confidence=min_confidence,
            max_triples=max_triples,
        )
        return jsonify(result), 200
    except Exception as e:
        print(f"Refine error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distill/student-inference', methods=['POST'])
@token_required
def student_inference(current_user):
    """
    POST { kg_id, prompt }
    → Run student LLM inference enriched with KG context.
    """
    try:
        data = request.get_json()
        kg_id = data.get('kg_id')
        prompt = data.get('prompt', '').strip()

        if not kg_id or not prompt:
            return jsonify({'error': 'kg_id and prompt are required'}), 400

        row = db.get_knowledge_graph(current_user['id'], int(kg_id))
        if not row:
            return jsonify({'error': 'Knowledge graph not found'}), 404

        graph_data = json.loads(row['graph_data'])
        result = distillation_pipeline.run_student_inference(prompt, graph_data)

        return jsonify({
            'kg_id':          int(kg_id),
            'prompt':         result['prompt'],
            'kg_context':     result['kg_context'],
            'response':       result['response'],
            'student_graph':  result['student_graph'],
        }), 200
    except Exception as e:
        print(f"Student inference error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distill/supervision-loss', methods=['POST'])
@token_required
def compute_supervision_loss(current_user):
    """
    POST { teacher_kg_id, student_text }
    → Compute the structured supervision loss between teacher KG and
      the KG extracted from student_text.
    """
    try:
        data = request.get_json()
        teacher_kg_id = data.get('teacher_kg_id')
        student_text = data.get('student_text', '').strip()

        if not teacher_kg_id or not student_text:
            return jsonify(
                {'error': 'teacher_kg_id and student_text are required'}
            ), 400

        row = db.get_knowledge_graph(current_user['id'], int(teacher_kg_id))
        if not row:
            return jsonify({'error': 'Teacher KG not found'}), 404

        teacher_graph = json.loads(row['graph_data'])
        loss = distillation_pipeline.compute_supervision_loss(
            teacher_graph, student_text
        )
        return jsonify({'teacher_kg_id': int(teacher_kg_id), **loss}), 200
    except Exception as e:
        print(f"Supervision loss error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/distill/evaluate', methods=['POST'])
@token_required
def evaluate_distillation(current_user):
    """
    POST { prediction_texts: [str, ...], ground_truth_texts: [str, ...] }
    → Extract KGs from both lists, then compute entity/relation-level
      precision, recall, F1 and an overall F1.
    """
    try:
        data = request.get_json()
        predictions = data.get('prediction_texts', [])
        ground_truths = data.get('ground_truth_texts', [])

        if not predictions or not ground_truths:
            return jsonify(
                {'error': 'prediction_texts and ground_truth_texts are required'}
            ), 400

        pred_graphs = [kg_builder.build_graph(t) for t in predictions]
        gt_graphs   = [kg_builder.build_graph(t) for t in ground_truths]

        metrics = distillation_pipeline.evaluate(pred_graphs, gt_graphs)
        return jsonify(metrics), 200
    except Exception as e:
        print(f"Evaluation error: {e}")
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