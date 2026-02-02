# System Architecture

## Overview

The AI Product Research Assistant is a modular, containerized application that combines RAG (Retrieval Augmented Generation), web search, and deterministic price analysis to help product teams make data-driven decisions.

## Data Flow

### Query Processing Flow

```
1. User submits query via POST /query
                ↓
2. FastAPI validates request
                ↓
3. LangGraph agent receives query
                ↓
4. Agent analyzes query intent
                ↓
5. Agent selects appropriate tool(s)
                ↓
6. Tool(s) execute:
   - Product RAG → Qdrant search
   - Web Search → External API/Mock
   - Price Analysis → Deterministic calc
                ↓
7. Results returned to agent
                ↓
8. Agent generates final response
                ↓
9. Response saved to SQLite
                ↓
10. Response returned to user
```

### Data Ingestion Flow

```
1. CSV file loaded (products_catalog.csv)
                ↓
2. Text prepared for embedding
   (name + brand + category + description)
                ↓
3. Embeddings generated
   (Sentence Transformers)
                ↓
4. Points upserted to Qdrant
   (ID from product_id for updates)
                ↓
5. Payload indexes created
   (category, brand, price, etc.)
```

## Monthly Update Strategy

### Incremental Updates

The system handles monthly catalog updates efficiently:

1. **Upsert Pattern**: Products are upserted by `product_id`
   - New products are added
   - Existing products are updated
   - No full re-indexing required

2. **Change Detection**:

   ```python
   # Product ID is converted to numeric point ID
   # Same product_id always maps to same point_id
   point_id = hash(product_id) % (2**63)

   # Upsert handles both insert and update
   client.upsert(collection_name, points)
   ```

3. **Update Process**:

   ```bash
   # Run ingestion with new CSV
   python -m src.ingestion.pipeline --csv new_catalog.csv

   # Or via API (future enhancement)
   POST /admin/ingest
   ```

### Recommended Update Schedule

| Update Type          | Frequency | Method          |
| -------------------- | --------- | --------------- |
| Full catalog refresh | Monthly   | Full ingestion  |
| Price updates        | Weekly    | Partial upsert  |
| New products         | As needed | Incremental add |
| Removed products     | Monthly   | Mark as deleted |

## Scaling Strategy

### Current Architecture (Single Node)

- Handles 1-5 requests/second
- Suitable for development and small teams
- All services on single machine

### Horizontal Scaling

For higher load:

```
                    ┌──────────────┐
                    │ Load Balancer│
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  App 1   │    │  App 2   │    │  App 3   │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
              ┌─────────────────────┐
              │   Shared Services   │
              │                     │
              │  - Qdrant Cluster   │
              │  - PostgreSQL       │
              │  - Ollama Pool      │
              │  - Redis Cache      │
              └─────────────────────┘
```

### Scaling Recommendations

1. **API Layer**: Horizontal scaling with load balancer
2. **Qdrant**: Cluster mode for larger datasets
3. **Ollama**: Multiple instances with request routing
4. **Database**: PostgreSQL for production
5. **Caching**: Redis for frequent queries

## Production Considerations

### Latency

| Component     | Typical Latency |
| ------------- | --------------- |
| Vector search | 10-50ms         |
| LLM inference | 2-10 seconds    |
| Web search    | 200-500ms       |
| Database      | 1-10ms          |

You can see that LLM inference is took the longest time, so we need to optimize it.

**Optimization strategies:**

- Response caching for common queries
- Streaming responses
- Async processing for non-critical paths

### Cost

| Component       | Cost Type                       |
| --------------- | ------------------------------- |
| Ollama          | Infrastructure (CPU/GPU)        |
| Qdrant          | Infrastructure + Storage        |
| Web Search API  | Per-request (if using real API) |
| Embedding Model | One-time download               |

**Cost optimization:**

- Use smaller models for simple queries (or using API provider)
- Cache embeddings and responses
- Batch similar queries

### Security

1. **API Security**:
   - Rate limiting
   - API key authentication
   - Input validation

2. **Data Security**:
   - No sensitive data in logs
   - Encrypted storage
   - Secure environment variables

3. **Network Security**:
   - Internal service communication only
   - HTTPS in production
   - Firewall rules

## Trade-offs

### Chosen Approach: Local LLM (Ollama)

**Pros:**

- No API costs
- Data stays local
- No rate limits
- Full control

**Cons:**

- Higher infrastructure requirements
- Slower than cloud APIs
- Limited to local hardware

### Alternative: Cloud LLM (OpenAI/Anthropic)

**Pros:**

- Faster responses
- Better model quality
- No infrastructure management

**Cons:**

- Per-request costs
- Data leaves your infrastructure !!
- Rate limits and quotas

### Vector Database Choice: Qdrant

**Why Qdrant:**

- Easy Docker deployment
- Good filtering support
- Active development
- Free and open source

**Alternatives considered:**

- Pinecone: Better scalability but paid
- Weaviate: More features but heavier
- Chroma: Simpler but less production-ready

## Monitoring & Observability

### In the future

```
┌────────────────────────────────────────────────┐
│                  Grafana                        │
│         (Dashboards & Alerting)                │
└─────────────────────┬──────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│Prometheus │  │   Loki    │  │  Jaeger   │
│ (Metrics) │  │  (Logs)   │  │ (Traces)  │
└───────────┘  └───────────┘  └───────────┘
```

### Key Metrics to Monitor

- Request latency (p50, p95, p99)
- Error rate
- Tool usage distribution
- LLM token usage
- Vector search latency
- Memory and CPU usage
- What did they think?

## Future Enhancements

1. **Caching Layer**: Redis for response caching
2. **Admin Dashboard**: UI for monitoring and management
3. **A/B Testing**: Compare different models/prompts
4. **Real-time Updates**: WebSocket for live catalog changes
5. **Advanced Analytics**: Query pattern analysis
