# Take-Home Assignment: AI Product Research Assistant

**Position:** Junior AI Engineer (Agentic AI & LLMs)  
**Timeline:** 7 days  
**Submission:** Public GitHub repository

---

## Scenario

You are building an AI-powered Product Research Assistant for an e-commerce product management team. The team needs to make data-driven decisions about product stocking, pricing, and market trends.

**Key Challenge:** The product catalog changes monthly (new products, price updates, stock changes). Your system must handle these updates efficiently.

---

## Objective

Build an AI assistant using LLMs + agentic AI that can:

1. **Answer product questions** using internal catalog data (RAG)
2. **Search the web** for market trends and competitor information
3. **Analyze pricing** and provide recommendations
4. **Route queries intelligently** via an LLM-powered agent
5. **Be deployed** as a clean, modular software system

---

## Tools to Build

### Tool 1: Product Catalog RAG

Retrieve information from product catalog to answer questions like:

- "What wireless headphones do we have in stock?"
- "Show me high-rated electronics under $100"
- "Which products from AudioMax brand are bestsellers?"

**Data source:** `products_catalog.csv` (provided - 105 products)

---

### Tool 2: Web Search

Search the web for current market information:

- "What is the current market price for noise-cancelling headphones?"
- "Latest reviews for Sony WH-1000XM5"
- "Trending products in home fitness equipment"

**Requirements:**

- Use a web search API or integration (Google Custom Search, Serper, Bing, Tavily, etc.)
- **Recommended:** Check LangChain's available search tools: https://docs.langchain.com/oss/python/integrations/tools
- If API access is limited, document your mock implementation clearly

---

### Tool 3: Price Analysis & Recommendation

Analyze pricing using deterministic calculations:

- "Which products have the lowest profit margins?"
- "Calculate average margin for Electronics category"
- "Show me products with margins below 40%"

**Requirements:**

- Write a **deterministic function** to calculate margins (price - cost) / price × 100
- **Important:** Use tool/function calling for calculations, not LLM generation
- LLM should format results and provide insights, not do the math

**Example calculation function:**

```python
def calculate_margin(price: float, cost: float) -> float:
    """Calculate profit margin percentage"""
    return ((price - cost) / price) * 100
```

Your tool should:

1. Query products from database/vector store
2. Calculate margins using your function
3. Use LLM to generate summary and insights

---

## Requirements

### 1. Data Ingestion & Vector Pipeline

- Load `products_catalog.csv` into a vector database of your choice
- Implement text chunking for product descriptions
- Generate embeddings (OpenAI, Sentence Transformers, etc.)
- Store metadata for filtering (category, price, stock, brand)
- **Design for monthly updates** - explain how you handle incremental updates without full re-indexing

**Deliverable:**

- Include your data pipeline design diagram (draw.io or similar) in the System Architecture section
- Show: CSV → Processing → Chunking → Embeddings → Vector DB

**Note:** Feel free to use open-source models and databases throughout your implementation.

---

### 2. Tool Development

- Each tool should be a **modular function or class**
- Write **effective prompts** for each tool
- Each tool should return **structured output** (JSON or dict)
- Include **error handling** for API failures and edge cases

**Example Tool Output:**

```python
{
  "answer": "We have 3 wireless headphones in stock...",
  "products": [...],
  "confidence": 0.92,
  "sources": [...]
}
```

---

### 3. AI Agent Development

Implement an AI Agent that:

- Receives a user query
- **Autonomously decides** which tool(s) to use
- **Explains its reasoning** for tool selection
- Routes query to appropriate tool(s)
- Returns structured output

**Example Agent Behavior:**

```
Query: "Should we lower AudioMax headphones price based on competitors?"

Reasoning: "This requires our internal pricing + external market data.
            Using Product Catalog RAG → Web Search → Price Analysis."

Tools used: ["product_catalog_rag", "web_search", "price_analysis"]
```

---

### 4. REST API Development

Build a FastAPI (or Flask) application with these endpoints:

**Required Endpoints:**

- `POST /query` - Main agent query endpoint
- `GET /queries` - Retrieve query history
- `POST /feedback` - Submit user feedback
- `GET /health` - Health check

**Database:** Store query history and feedback (SQLite, PostgreSQL, or similar)

---

### 5. Deployment

- **Docker:** Containerize your entire application
- **docker-compose.yml** (recommended) for easy deployment
- All components should work inside Docker

---

### 6. Load Testing

- Use `locust`, `k6`, or similar tool
- Test `/query` endpoint under load
- Document:
  - Requests per second
  - Response times (p50, p95, p99)
  - Bottlenecks identified
  - Recommendations for scaling

---

### 7. System Architecture

Create an architecture diagram showing:

- Data ingestion pipeline
- Vector database
- AI Agent service
- API layer
- Storage (databases)
- Monitoring/logging

**Write ARCHITECTURE.md explaining:**

- How monthly updates work
- Scaling strategy
- Production considerations (latency, cost, security)
- Trade-offs in your design

---

## Deliverables

Your repository should include:

```
product-research-assistant/
├── data/
├── src/
├── tests/
├── load_tests/
├── architecture/
│   ├── data_pipeline_diagram.png (or .drawio)
│   ├── system_architecture_diagram.png
│   └── ARCHITECTURE.md
├── Dockerfile
├── docker-compose.yml (optional)
├── requirements.txt
├── .env.example
└── README.md
```

**We evaluate:**

- Clean code structure and modularity
- Your design patterns and architectural choices
- Not a specific folder structure

---

## README Requirements

⚠️ **CRITICAL:** We will reproduce your project by following your README exactly as written. If we cannot run your code, your score will be significantly reduced.

**Your README.md must include:**

1. **Setup Instructions**

   - Dependencies installation
   - Environment variables setup

2. **Run the Application**

   - How to start the API
   - Docker commands (if applicable)

3. **Test the API**
   - Example curl commands or API requests
   - At least 3-4 test queries covering different tools

**That's it.** Clear, step-by-step, reproducible instructions.

---

## Evaluation Criteria

| Criteria                         | Weight |
| -------------------------------- | ------ |
| **Data Pipeline & Vector DB**    | 20%    |
| **AI Tools (3 tools)**           | 15%    |
| **Agent Logic & Routing**        | 15%    |
| **API & Database**               | 10%    |
| **Load Testing**                 | 5%     |
| **System Architecture**          | 15%    |
| **Code Quality & Documentation** | 20%    |

---

## Submission

1. **GitHub Repository:** Make it public
2. **Include:** All code, Dockerfile, architecture diagram, README
3. **Test:** Clone in fresh environment and verify it works
4. **Submit:** Repository URL via email
5. **Deadline:** 7 days from receipt

---

## Bonus Points

- Unit tests for tools/agent (+10%)
- CI/CD pipeline (+5%)
- Caching implementation (+5%)
- Multi-turn conversation support (+5%)
- Comprehensive evaluation metrics (+5%)

---

## Notes

- **Use AI tools freely** (ChatGPT, Claude, Copilot) - but understand your code
- **Don't clone others' solutions** - you must be able to explain everything
- **Open-source encouraged:** Feel free to use open-source LLMs (Llama, Mistral, etc.) and databases
- **Accuracy is not weighted:** We evaluate your system design and code quality, not LLM response accuracy
- **Ask questions** within 24 hours if assignment is unclear
- **Document assumptions** if requirements are ambiguous

---

## Important: This is a Junior Role

**We understand this is challenging!** You're not expected to complete everything perfectly. Here's what matters most:

### **Please Submit Even If:**

- You only completed 2 out of 3 tools
- Your agent routing isn't perfect
- Load testing shows performance issues
- You used mock data instead of real APIs
- Some features are basic implementations
- Your code has known limitations

### **What We Really Care About:**

1. **Your thinking process** - How you approached problems
2. **Code you understand** - Can you explain what you wrote?
3. **Honest documentation** - Tell us what works and what doesn't
4. **Learning ability** - Did you try new things?

### **In Your README, Please Include:**

**A "Limitations & Future Improvements" section:**

- What you didn't finish and why
- What you would improve with more time
- What you learned during this assignment
- What challenges you faced

**Example:**

```markdown
Limitations & Future Improvements

What's Not Implemented:

- Web search tool uses mock data (couldn't get API access in time)
- Agent sometimes selects wrong tool for ambiguous queries
- No caching layer implemented

What I Would Improve:

- Add better error handling in the data pipeline
- Implement proper retry logic for failed requests
- Add unit tests for each tool

What I Learned:

- How to structure a RAG pipeline with vector databases
- Tool calling patterns with LangChain
- Challenges of agent decision-making
```

### **Partial Credit Strategy:**

We evaluate each component separately. You can get full credit for:

- A well-implemented RAG tool even if web search is incomplete
- Good architecture design even if code isn't perfect
- Clear documentation even if features are missing
- Honest reflection about challenges faced

### ⚠️ **Don't Do This:**

- Submit broken code without explanation
- Copy code you don't understand
- Leave README incomplete
- Not submit at all because it's not "perfect"

**Remember:** We're hiring for potential and learning ability, not perfection. Show us your thinking, be honest about limitations, and submit what you have!

---

## Sample Test Queries

Test your agent with these queries:

```bash
# Product Catalog RAG
curl -X POST http://localhost:8000/query \
  -d '{"query": "What wireless headphones do we have in stock?"}'

# Web Search
curl -X POST http://localhost:8000/query \
  -d '{"query": "Current market price for noise-cancelling headphones?"}'

# Price Analysis
curl -X POST http://localhost:8000/query \
  -d '{"query": "Which products have lowest profit margins?"}'

# Multi-Tool
curl -X POST http://localhost:8000/query \
  -d '{"query": "Should we adjust AudioMax headphones pricing vs competitors?"}'
```

---

## Final Words

**We're excited to see what you build!**

This assignment is designed to be challenging, but remember - we're not looking for perfection. We want to see how you think, how you learn, and how you approach problems. Every senior engineer started as a junior, and we all remember what it felt like to face assignments like this.
Here's the truth:

- Your best effort is enough - Even if it's incomplete
- Your learning matters more than the result - Show us your growth
- Questions are encouraged - Asking shows you're thinking critically
- Partial solutions are valuable - They show your prioritization skills
- This is practice for the real job - Where things are rarely "perfect" either

**What happens next?**

If you submit, you'll get a chance to:

Walk us through your thinking in an interview
Explain your design choices
Share what you learned
Ask us questions about the role and team

We're rooting for you! Take your time, do your best, and don't forget to document what you learned along the way.
Looking forward to reviewing your work!

## Questions?

Email: [kiattiphum@quanxai.com](kiattiphum@quanxai.com)
**You've got this! 💪**

---
