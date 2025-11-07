# 🧠 AI Research Assistant

A powerful web application that helps researchers discover, analyze, and manage academic papers using AI-powered tools.

## ✨ Features

- 🔍 **Paper Search**: Search academic papers from arXiv database
- 🤖 **AI Summarization**: Automatically generate summaries of research papers
- 📊 **Smart Analysis**: Analyze papers for methodology, findings, and implications
- ⚛️ **Quantum Chatbot**: Specialized chatbot for quantum computing and quantum mechanics queries
- 💾 **Save Papers**: Bookmark and organize your favorite papers
- 📜 **Search History**: Track your research queries
- 🔐 **User Authentication**: Secure login and registration system
- 🐳 **Docker Support**: Easy deployment with Docker

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or SQLite for development)
- OpenAI API Key (optional, for AI features)
- SerpAPI Key (optional, for quantum chatbot web search)

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

4. **Set up PostgreSQL database**
```bash
createdb research_assistant
```

5. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. **Run the application**
```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

1. **Clone the repository**
```bash
git clone https://github.com/arnavvadan2022-svg/ai-research-assistant.git
cd ai-research-assistant
```

2. **Start the application**
```bash
docker-compose up --build
```

The application will be available at `http://localhost:5000`

### Manual Docker Setup

1. **Build the image**
```bash
docker build -t ai-research-assistant .
```

2. **Run the container**
```bash
docker run -p 5000:5000 \
  -e DB_HOST=your-db-host \
  -e DB_PASSWORD=your-db-password \
  -e SECRET_KEY=your-secret-key \
  -e OPENAI_API_KEY=your-openai-key \
  ai-research-assistant
```

## 📖 Usage

### 1. Register/Login
- Create a new account or sign in with existing credentials
- Your session will be maintained with JWT tokens

### 2. Search Papers
- Enter keywords, topics, or paper titles in the search bar
- Select the maximum number of results
- Click "Search" to find relevant papers from arXiv

### 3. View and Analyze
- View paper details including abstract, authors, and publication date
- Click "Summarize" to generate AI-powered summaries
- Download PDFs directly from arXiv

### 4. Manage Papers
- Save papers to your personal library
- View your saved papers anytime
- Track your search history

### 5. Quantum Computing Chatbot
- Ask questions specifically about quantum computing and quantum mechanics
- The chatbot validates queries to ensure they're quantum-related
- Get comprehensive answers combining:
  - Quantum physics research papers from arXiv (quant-ph category)
  - Current web information via SerpAPI (when API key is configured)
- Example queries:
  - "What is quantum entanglement?"
  - "Explain Shor's algorithm"
  - "How do superconducting qubits work?"
  - "What is quantum error correction?"

## 🛠️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DEBUG=False

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=research_assistant
DB_USER=postgres
DB_PASSWORD=your-password

# OpenAI API Key (optional)
OPENAI_API_KEY=your-openai-api-key

# SerpAPI Key (optional, for quantum chatbot web search)
SERPAPI_API_KEY=your-serpapi-api-key

# Application Settings
MAX_SEARCH_RESULTS=50
SUMMARY_MAX_LENGTH=500
```

## 🏗️ Project Structure

```
ai-research-assistant/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose setup
├── .env.example          # Environment variables template
├── .gitignore           # Git ignore rules
├── README.md            # Documentation
├── utils/
│   ├── database.py          # Database operations
│   ├── paper_search.py      # ArXiv API integration
│   ├── ai_processor.py      # AI summarization & analysis
│   └── quantum_chatbot.py   # Quantum computing chatbot
├── templates/
│   └── index.html           # Frontend HTML
└── static/
    ├── css/
    │   └── style.css        # Styling
    └── js/
        └── main.js          # Frontend JavaScript
```

## 🔌 API Endpoints

### Authentication
- `POST /api/register` - Register new user
- `POST /api/login` - User login

### Papers
- `POST /api/search` - Search papers
- `POST /api/summarize` - Summarize paper
- `POST /api/analyze` - Analyze paper
- `GET /api/papers` - Get saved papers
- `DELETE /api/papers/<id>` - Delete paper

### Quantum Chatbot
- `POST /api/quantum/chat` - Query the quantum computing chatbot

### User
- `GET /api/history` - Get search history
- `GET /api/health` - Health check

## ⚛️ Quantum Chatbot Feature

The Quantum Computing Chatbot is a specialized feature designed to help researchers and enthusiasts explore quantum computing and quantum mechanics topics.

### Key Features

1. **Domain Validation**: Automatically validates queries to ensure they're related to quantum computing or quantum mechanics
2. **Multi-Source Information**: Combines research papers from arXiv and web results from SerpAPI
3. **Intelligent Synthesis**: Provides comprehensive answers by synthesizing information from multiple sources
4. **Quantum-Specific Search**: Targets the `quant-ph` (quantum physics) category on arXiv for relevant research papers

### API Usage

**Endpoint**: `POST /api/quantum/chat`

**Request Body**:
```json
{
  "query": "What is quantum entanglement?",
  "max_papers": 10,
  "max_web_results": 5
}
```

**Response** (Success):
```json
{
  "success": true,
  "query": "What is quantum entanglement?",
  "answer": "Comprehensive synthesized answer...",
  "papers": [...],
  "web_results": [...],
  "sources_count": {
    "papers": 5,
    "web_results": 3
  }
}
```

**Response** (Invalid Query):
```json
{
  "success": false,
  "error": "This chatbot specializes in quantum computing and quantum mechanics topics...",
  "query": "What is machine learning?"
}
```

### Supported Topics

The chatbot accepts queries about:
- Quantum computing (qubits, quantum gates, quantum circuits, quantum algorithms)
- Quantum mechanics (wave functions, uncertainty principle, quantum states)
- Quantum algorithms (Shor's algorithm, Grover's algorithm, VQE, QAOA)
- Quantum hardware (superconducting qubits, ion traps, quantum dots)
- Quantum cryptography and communication
- Quantum error correction
- And many more quantum-related topics

### Configuration

To enable web search functionality, add your SerpAPI key to the `.env` file:
```bash
SERPAPI_API_KEY=your-serpapi-api-key-here
```

Get a free SerpAPI key at: https://serpapi.com/

**Note**: The chatbot works without a SerpAPI key, but web search results will not be included.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## 👤 Author

**arnavvadan2022-svg**
- GitHub: [@arnavvadan2022-svg](https://github.com/arnavvadan2022-svg)

## 🙏 Acknowledgments

- [arXiv](https://arxiv.org/) for providing open access to research papers
- [OpenAI](https://openai.com/) for AI-powered features
- [Flask](https://flask.palletsprojects.com/) for the web framework

## 📧 Support

For support, email arnav.vadan2022@vitstudent.ac.in or open an issue on GitHub.

---

Made with ❤️ by arnavvadan2022-svg