# Load Tests

This directory contains load testing scripts for the AI Product Research Assistant.

## Running Load Tests

### Prerequisites

1. Install locust:
   ```bash
   pip install locust
   ```

2. Ensure the API is running:
   ```bash
   # From project root
   uvicorn src.server:app --host 0.0.0.0 --port 8000
   ```

### Running with Web UI

```bash
cd load_tests
locust -f locustfile.py --host=http://localhost:8000
```

Then open http://localhost:8089 in your browser to configure:
- Number of users
- Spawn rate
- Duration

### Running Headless

```bash
# 10 users, spawn rate 1/second, run for 60 seconds
locust -f locustfile.py --host=http://localhost:8000 \
    --users 10 --spawn-rate 1 --run-time 60s --headless

# Generate HTML report
locust -f locustfile.py --host=http://localhost:8000 \
    --users 10 --spawn-rate 1 --run-time 60s --headless \
    --html=report.html
```

## Test Scenarios

### ProductResearchUser (Normal Load)
Simulates typical user behavior:
- 50% Product catalog searches
- 20% Web searches
- 20% Price analysis
- 10% Multi-tool queries
- Health checks and history queries

### HighLoadUser (Stress Test)
Simulates high-load scenarios with minimal wait times.

## Expected Results

Based on local testing with Ollama:

| Metric | Expected Value |
|--------|---------------|
| Requests/sec | 1-5 (limited by LLM) |
| P50 latency | 2-5 seconds |
| P95 latency | 5-15 seconds |
| P99 latency | 15-30 seconds |
| Error rate | < 5% |

### Bottlenecks Identified

1. **LLM Inference**: Primary bottleneck is Ollama response time
2. **Vector Search**: Secondary bottleneck for large queries
3. **Sequential Processing**: Queries processed one at a time

### Scaling Recommendations

1. **Horizontal Scaling**: Deploy multiple Ollama instances behind a load balancer
2. **Caching**: Implement response caching for common queries
3. **Async Processing**: Use message queues for long-running queries
4. **GPU Acceleration**: Use GPU-enabled Ollama for faster inference
