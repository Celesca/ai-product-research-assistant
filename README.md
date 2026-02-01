# AI Product Research Assistant

An AI-powered product research assistant built with FastAPI, LangGraph, Qdrant, and Ollama. The system helps e-commerce teams make data-driven decisions about products through intelligent query routing and multi-tool orchestration.

## 🚀 Features

- **Product Catalog RAG**: Semantic search over product catalog with metadata filtering
- **Web Search**: Market trends and competitor research (with mock fallback)
- **Price Analysis**: Deterministic margin calculations and pricing recommendations
- **Intelligent Routing**: LangGraph-based agent automatically selects appropriate tools
- **Query History**: Track all queries with feedback support
- **Load Testing**: Locust-based performance testing

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- 8GB+ RAM recommended (for Ollama)
- GPU recommended but not required (Ollama can run on CPU)

## 🛠️ Setup Instructions

### Option 1: Docker (Recommended)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ai-product-research-assistant
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Pull the Ollama model (first time only):**
   ```bash
   docker exec -it ollama ollama pull qwen3:4b
   ```

5. **Run data ingestion:**
   ```bash
   docker exec -it product-research-assistant python -m src.ingestion.pipeline
   ```

6. **Verify the setup:**
   ```bash
   curl http://localhost:8000/health
   ```

### Option 2: Local Development

1. **Clone and setup environment:**
   ```bash
   git clone <repository-url>
   cd ai-product-research-assistant
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Start Qdrant (Docker):**
   ```bash
   docker run -d -p 6333:6333 -p 6334:6334 \
       -v qdrant_storage:/qdrant/storage \
       qdrant/qdrant
   ```

4. **Start Ollama (local install or Docker):**
   ```bash
   # Option A: If Ollama is installed locally
   ollama serve
   ollama pull llama3.2
   
   # Option B: Using Docker
   docker run -d -p 11434:11434 -v ollama_data:/root/.ollama ollama/ollama
   docker exec -it <container-id> ollama pull llama3.2
   ```

5. **Run data ingestion:**
   ```bash
   python -m src.ingestion.pipeline
   ```

6. **Start the API:**
   ```bash
   uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
   ```

## 🧪 Test the API

### Health Check

```bash
curl http://localhost:8000/health
```

### Product Catalog Search (RAG)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What wireless headphones do we have in stock?"}'
```

### Web Search (Market Research)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Current market price for noise-cancelling headphones?"}'
```

### Price Analysis (Margin Calculations)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Which products have lowest profit margins?"}'
```

### Multi-Tool Query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Should we adjust AudioMax headphones pricing vs competitors?"}'
```

### Query History

```bash
curl http://localhost:8000/queries
```

### Submit Feedback

```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"query_id": 1, "rating": 5, "helpful": true, "comment": "Very helpful!"}'
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /query | Main agent query endpoint |
| GET | /queries | Retrieve query history |
| POST | /feedback | Submit user feedback |
| GET | /health | Health check |
| GET | /tools | List available tools |

## 🏗️ Architecture

See [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) for detailed system architecture.

### Components

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    FastAPI      │────▶│   LangGraph     │────▶│     Tools       │
│    Server       │     │     Agent       │     │                 │
└─────────────────┘     └─────────────────┘     │ ┌─────────────┐ │
                                                │ │ Product RAG │ │
                                                │ ├─────────────┤ │
┌─────────────────┐     ┌─────────────────┐     │ │ Web Search  │ │
│    Qdrant       │◀────│    Ollama       │     │ ├─────────────┤ │
│  Vector Store   │     │      LLM        │     │ │Price Analyze│ │
└─────────────────┘     └─────────────────┘     └─┴─────────────┴─┘
```

## 📊 Load Testing

```bash
# Install locust
pip install locust

# Run load test (with API running)
cd load_tests
locust -f locustfile.py --host=http://localhost:8000

# Open http://localhost:8089 to configure and run tests
```

See [load_tests/README.md](load_tests/README.md) for detailed instructions.

## 🧪 Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_price_analysis.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## 📁 Project Structure

```
ai-product-research-assistant/
├── architecture/
│   └── ARCHITECTURE.md      # System architecture documentation
├── data/
│   └── products_catalog.csv # Product catalog data
├── load_tests/
│   ├── locustfile.py        # Load test definitions
│   └── README.md            # Load testing guide
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   └── research_agent.py # LangGraph agent
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── pipeline.py       # Data ingestion pipeline
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── price_analysis.py # Price analysis tool
│   │   ├── product_catalog_rag.py # RAG tool
│   │   └── web_search.py     # Web search tool
│   ├── __init__.py
│   ├── config.py             # Configuration
│   ├── database.py           # Database models
│   ├── embeddings.py         # Embedding service
│   └── server.py             # FastAPI server
├── tests/
│   ├── __init__.py
│   ├── test_api.py           # API tests
│   ├── test_price_analysis.py # Price analysis tests
│   └── test_web_search.py    # Web search tests
├── .env.example              # Environment template
├── docker-compose.yml        # Docker Compose config
├── Dockerfile                # Application Dockerfile
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| QDRANT_HOST | localhost | Qdrant server host |
| QDRANT_PORT | 6333 | Qdrant server port |
| COLLECTION_NAME | products | Qdrant collection name |
| OLLAMA_BASE_URL | http://localhost:11434 | Ollama API URL |
| OLLAMA_MODEL | llama3.2 | Ollama model to use |
| DATABASE_URL | sqlite:///./data/app.db | Database connection URL |
| TAVILY_API_KEY | (optional) | Tavily API key for web search |
| SERPER_API_KEY | (optional) | Serper API key for web search |

## ⚠️ Limitations & Future Improvements

### What's Not Implemented

- **Real Web Search**: Uses mock data by default (configure `TAVILY_API_KEY` or `SERPER_API_KEY` for real search)
- **Multi-turn Conversation**: Each query is independent (no conversation memory)
- **Caching**: No response caching implemented
- **Authentication**: No API authentication

### What I Would Improve

- Add Redis caching for frequently asked queries
- Implement conversation memory for follow-up questions
- Add API key authentication
- Implement proper rate limiting
- Add more comprehensive error handling
- Create a web UI dashboard

### Challenges Faced

- **LangGraph Tool Binding**: Required careful schema definition for Ollama compatibility
- **Async/Sync Mixing**: Balancing async FastAPI with sync LangGraph operations
- **Docker Networking**: Ensuring services can communicate in Docker network

### What I Learned

- How to structure a RAG pipeline with Qdrant vector database
- LangGraph patterns for agent orchestration
- Tool calling with local LLMs (Ollama)
- Importance of deterministic calculations vs LLM generation

## 🔧 Troubleshooting

### Common Issues

1. **Ollama not responding:**
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # Pull the model if missing
   ollama pull llama3.2
   ```

2. **Qdrant connection error:**
   ```bash
   # Check if Qdrant is running
   curl http://localhost:6333/health
   
   # Restart Qdrant
   docker restart qdrant
   ```

3. **No products in search results:**
   ```bash
   # Run data ingestion
   python -m src.ingestion.pipeline
   ```

4. **GPU not being used:**
   - Ensure NVIDIA drivers are installed
   - Check docker-compose.yml has GPU resources configured
   - For CPU-only: comment out the deploy section in docker-compose.yml

## 📄 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 Support

For questions or issues, please open a GitHub issue.
