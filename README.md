# 🔬 Quantum Computing & Quantum Mechanics Chatbot

An intelligent chatbot specialized in quantum computing and quantum mechanics, powered by AI and backed by research papers and web sources.

## ✨ Features

- 🔮 **Quantum Specialization**: Only answers quantum computing and quantum mechanics questions
- 📚 **Dual Source Intelligence**: Combines information from arXiv research papers and web search
- 🤖 **AI-Powered Answers**: Uses Hugging Face transformers for natural language understanding
- 💬 **Conversational Memory**: Maintains context across multiple queries in a session
- 📖 **Source Citations**: Provides clear references to arXiv papers and web sources
- 🎯 **Smart Query Validation**: Automatically detects non-quantum questions and suggests relevant topics
- 🔐 **User Authentication**: Secure login and session management
- 💾 **Chat History**: Save and revisit previous conversations
- 🐳 **Docker Support**: Easy deployment with Docker

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- API Keys:
  - SERP API key (free tier: https://serpapi.com/users/sign_up)
  - Hugging Face API key (optional, for better AI answers)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/arnavvadan2022-svg/ai-research-assistant.git
cd ai-research-assistant
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration:
# - SERP_API_KEY (required)
# - HUGGINGFACE_API_KEY (optional but recommended)
# - SECRET_KEY (required for sessions)
```

5. **Run the application**
```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

1. **Clone and configure**
```bash
git clone https://github.com/arnavvadan2022-svg/ai-research-assistant.git
cd ai-research-assistant
cp .env.example .env
# Edit .env with your API keys
```

2. **Start the application**
```bash
docker-compose up --build
```

The application will be available at `http://localhost:5000`

## 📖 Usage

### 1. Register/Login
- Create a new account or sign in with existing credentials
- Your session will be maintained with JWT tokens

### 2. Ask Quantum Questions
- Enter questions about quantum computing or quantum mechanics
- The system validates that questions are quantum-related
- Non-quantum questions receive polite suggestions for quantum topics

### 3. Get AI-Powered Answers
- Answers are generated from:
  - arXiv research papers (quantum physics categories)
  - Web search results (via SERP API)
  - Hugging Face AI models
- All sources are cited with clear references

### 4. Manage Conversations
- Start new chat sessions
- View chat history
- Continue previous conversations
- Delete old sessions

## 🎯 Supported Quantum Topics

The chatbot can help with:

- **Quantum Computing**: qubits, quantum gates, quantum circuits, quantum algorithms
- **Quantum Algorithms**: Shor's algorithm, Grover's algorithm, VQE, QAOA
- **Quantum Error Correction**: QEC, fault-tolerant quantum computing
- **Quantum Information**: quantum entanglement, quantum teleportation, quantum communication
- **Quantum Mechanics**: wave functions, quantum states, uncertainty principle, quantum measurement
- **Quantum Hardware**: superconducting qubits, ion traps, photonic quantum computers
- **Quantum Cryptography**: quantum key distribution, quantum security
- **Quantum Materials**: quantum dots, topological insulators, quantum hall effect
- **Advanced Topics**: quantum supremacy, NISQ devices, quantum simulation

## 🛠️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DEBUG=False

# API Keys
HUGGINGFACE_API_KEY=your-huggingface-api-key
SERP_API_KEY=your-serpapi-key

# Application Settings
MAX_ARXIV_PAPERS=5
MAX_WEB_RESULTS=5
CONVERSATION_HISTORY_LIMIT=10
HF_MODEL=google/flan-t5-large
```

### Hugging Face Models

Supported models (configurable via `HF_MODEL`):
- `google/flan-t5-large` (default, recommended)
- `meta-llama/Llama-2-7b-chat-hf`
- `mistralai/Mistral-7B-Instruct-v0.2`

## 🏗️ Project Structure

```
ai-research-assistant/
├── app.py                          # Main Flask application
├── config.py                       # Configuration management
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker configuration
├── docker-compose.yml              # Docker Compose setup
├── .env.example                    # Environment variables template
├── utils/
│   ├── database.py                 # Database operations
│   ├── paper_search.py             # ArXiv API integration
│   ├── serp_search.py              # SERP API integration
│   ├── quantum_validator.py        # Query validation
│   ├── quantum_ai_processor.py     # AI answer generation
│   └── conversation_manager.py     # Chat session management
├── templates/
│   └── index.html                  # Frontend HTML
└── static/
    ├── css/
    │   └── style.css               # Styling
    └── js/
        └── main.js                 # Frontend JavaScript
```

## 🔌 API Endpoints

### Authentication
- `POST /api/register` - Register new user
- `POST /api/login` - User login

### Quantum Chat
- `POST /api/chat` - Send quantum question and get AI answer
- `POST /api/validate-query` - Validate if query is quantum-related

### Conversation Management
- `GET /api/sessions` - Get all chat sessions
- `GET /api/sessions/<session_id>` - Get specific session history
- `DELETE /api/sessions/<session_id>` - Delete a session

### Utility
- `GET /api/health` - Health check

## 🧪 Example Queries

### Valid Quantum Questions:
- "What is quantum entanglement and how does it work?"
- "Explain Shor's algorithm for integer factorization"
- "How does quantum error correction work?"
- "What are the differences between gate-based and annealing quantum computers?"
- "Explain the concept of quantum supremacy"

### Non-Quantum Questions:
If you ask about non-quantum topics, the chatbot will:
1. Politely decline to answer
2. Suggest relevant quantum topics
3. Guide you to ask quantum-related questions

## 🔍 How It Works

1. **Query Validation**: Checks if question is quantum-related using keyword matching
2. **Source Retrieval**: 
   - Searches arXiv for relevant quantum physics papers
   - Searches web using SERP API for additional context
3. **Context Building**: Combines paper abstracts and web snippets
4. **AI Generation**: Uses Hugging Face models to generate comprehensive answers
5. **Citation**: Adds references to all sources used

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## 👤 Author

**arnavvadan2022-svg**
- GitHub: [@arnavvadan2022-svg](https://github.com/arnavvadan2022-svg)

## 🙏 Acknowledgments

- [arXiv](https://arxiv.org/) for providing open access to research papers
- [SERP API](https://serpapi.com/) for web search capabilities
- [Hugging Face](https://huggingface.co/) for AI models
- [Flask](https://flask.palletsprojects.com/) for the web framework

## 📧 Support

For support, email arnav.vadan2022@vitstudent.ac.in or open an issue on GitHub.

## 🔒 Security

- No API keys are stored in the repository
- All user passwords are hashed
- JWT tokens for secure authentication
- SQL injection protection via parameterized queries

---

Made with ❤️ by arnavvadan2022-svg

**Note**: This is a specialized quantum computing assistant. For general AI research assistance, please use the original version.
