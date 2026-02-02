# AI Product Research Assistant

An AI-powered product research assistant built with FastAPI, LangGraph, Qdrant, and Ollama. The system helps e-commerce teams make data-driven decisions about products through intelligent query routing and multi-tool orchestration.

## 🚀 Features

- **Product Catalog RAG**: Semantic search over product catalog with metadata filtering
- **Web Search**: Market trends and competitor research (with mock fallback)
- **Price Analysis**: Deterministic margin calculations and pricing recommendations
- **Intelligent Routing**: LangGraph-based agent automatically selects appropriate tools
- **Chat Interface**: Modern React-based frontend for interactive research
- **Query History**: Track all queries with feedback support

## 📋 Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for Frontend)
- Python 3.11+ (for local development/evaluation)
- 8GB+ RAM recommended (for Ollama)
- GPU recommended but not required (Ollama can run on CPU)

## 🛠️ Setup Instructions

### 1. Backend & AI Services (Docker)

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd ai-product-research-assistant
   ```

2. **Create environment file:**

   ```bash
   cp .env.example .env
   ```

3. **Start backend services:**

   ```bash
   docker-compose up -d
   ```

4. **Pull the Ollama model (first time only):**

   ```bash
   docker exec -it ollama ollama pull qwen3:0.6b
   ```

   _Note: You can use larger models like `llama3.2` or `mistral` by updating `.env` if your hardware permits._

5. **Run data ingestion:**

   ```bash
   docker exec -it product-research-assistant python -m src.ingestion.pipeline
   ```

6. **Verify backend:**
   ```bash
   curl http://localhost:8000/health
   ```

### 2. Frontend Application

1. **Navigate to frontend directory:**

   ```bash
   cd frontend
   ```

2. **Install dependencies:**

   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```
   Access the UI at: http://localhost:5173

## 🧪 Test the API

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

### Price Analysis

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Which products have lowest profit margins?"}'
```

### Query History

```bash
curl http://localhost:8000/queries
```

## 📊 Evaluation & Testing

### Run Evaluation Framework

Run the automated test suite to measure agent performance (accuracy, tool selection, goal completion):

```bash
# From root directory (ensure python environment is set up)
pip install -r requirements.txt
python src/evaluation/evaluator.py
```

Reports will be saved to `evaluation_reports/`.

### Run Load Tests

```bash
pip install locust
cd load_tests
locust -f locustfile.py --host=http://localhost:8000
```

## 🏗️ Short Architecture

```
┌──────────────┐      ┌─────────────┐      ┌────────────────┐
│   Frontend   │      │   FastAPI   │      │   LangGraph    │
│    (React)   │ ───▶ │   Server    │ ───▶ │     Agent      │
└──────────────┘      └─────────────┘      └───────┬────────┘
                                                   │
          ┌───────────────┬────────────────────────┴─────────────────┐
          ▼               ▼                                          ▼
  ┌──────────────┐  ┌──────────────┐                        ┌────────────────┐
  │ Product RAG  │  │  Web Search  │                        │ Price Analysis │
  │   (Qdrant)   │  │ (Tavily/API) │                        │ (Deterministic)│
  └──────────────┘  └──────────────┘                        └────────────────┘
```

See [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) for detailed documentation.

## 📁 Project Structure

```
ai-product-research-assistant/
├── architecture/         # System design docs
├── data/                 # Raw data (catalog.csv)
├── frontend/             # React application
│   ├── src/
│   │   ├── api/          # API client
│   │   └── components/   # Chat UI components
├── src/
│   ├── agent/            # LangGraph agent logic
│   ├── evaluation/       # Evaluation metrics & scripts
│   ├── ingestion/        # Data pipeline
│   ├── tools/            # RAG, Search, Analysis tools
│   ├── models/           # Pydantic schemas
│   └── server.py         # FastAPI main app
├── tests/                # Unit tests
├── docker-compose.yml    # Service orchestration
└── requirements.txt      # Python dependencies
```

## ⚠️ Limitations & Future Improvements

### Current Limitations

- **Memory**: Running Qdrant, Ollama, and API services simultaneously requires significant RAM (8GB+ recommended).
- **Model Size**: The optimization to use `qwen3:0.6b` (for speed/memory) trades off some reasoning capability compared to larger models like Llama 3.
- **No Auth**: API currently has no authentication mechanism.
- **Product List**: The product list is not included in the response body of catalog search requests in the current API schema.

### Future Roadmap

1. **Caching Layer**: Implement Redis for frequent query caching.
2. **Conversation Memory**: Enhance agent with long-term memory across sessions.
3. **Advanced Auth**: API Key/OAuth integration.
4. **Rate Limiting**: Protect endpoints from abuse.
5. **Dashboard**: Expand frontend to include admin/metrics view.
6. **Monitoring**: Add monitoring for agent performance and system health.
7. **Logging**: Add logging for agent performance and system health.
8. **Error Handling**: Add error handling for agent performance and system health.
9. **Evaluation Framework**: Automated metric collection for RAG and agent performance

### Challenges Learned

- **Resource Management**: Balancing Docker resource limits for local LLM inference.
- **Tool Selection**: Tuning prompts to ensure the small model selects the correct tool (Search vs RAG).
- **Architecture**: Designing clean boundaries between Agent logic and API layer.

What I learned can refers to [walkthrough.md](walkthrough.md)
