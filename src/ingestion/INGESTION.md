# Data Ingestion & Vector Pipeline

This document describes the data ingestion pipeline for the AI Product Research Assistant.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│              │    │              │    │              │    │              │
│  CSV File    │───▶│  Processing  │───▶│   Chunking   │───▶│  Embeddings  │
│              │    │              │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                   │
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│products_     │    │• Load CSV    │    │• Split long  │    │• Sentence    │
│catalog.csv   │    │• Validate    │    │  descriptions│    │  Transformers│
│              │    │• Clean data  │    │• Chunk size: │    │• Model:      │
│              │    │              │    │  512 chars   │    │  MiniLM-L6   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                   │
                                                                   ▼
                                              ┌──────────────────────────────┐
                                              │                              │
                                              │         Vector DB            │
                                              │          (Qdrant)            │
                                              │                              │
                                              │  ┌────────────────────────┐  │
                                              │  │ Collection: products   │  │
                                              │  │ • Vectors (384-dim)    │  │
                                              │  │ • Metadata/Payloads    │  │
                                              │  │ • Payload Indexes      │  │
                                              │  └────────────────────────┘  │
                                              │                              │
                                              └──────────────────────────────┘
```

## Pipeline Components

### 1. CSV Loading
- Reads `products_catalog.csv` using pandas
- Validates required fields: `product_id`, `product_name`, `category`, `brand`, `description`

### 2. Text Processing
Combines fields for semantic search:
```
"{product_name} - {brand} - {category}: {description}"
```

### 3. Text Chunking
For long descriptions, splits into chunks:
- **Chunk size**: 512 characters
- **Overlap**: 50 characters
- Maintains context across chunks

### 4. Embedding Generation
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimension**: 384
- **Batch size**: 32 (configurable)

### 5. Vector Storage (Qdrant)
Stores vectors with full metadata:

| Field | Type | Indexed |
|-------|------|---------|
| product_id | keyword | ✅ |
| product_name | text | ❌ |
| category | keyword | ✅ |
| brand | keyword | ✅ |
| description | text | ❌ |
| current_price | float | ✅ |
| cost | float | ✅ |
| stock_quantity | integer | ✅ |
| average_rating | float | ✅ |

## Incremental Update Strategy

### How Monthly Updates Work (Without Full Re-indexing)

```
┌─────────────────────────────────────────────────────────────────┐
│                    INCREMENTAL UPDATE FLOW                      │
└─────────────────────────────────────────────────────────────────┘

              ┌─────────────┐
              │ New CSV     │
              │ (Monthly)   │
              └──────┬──────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ For each product:     │
         │ Check last_updated    │
         └───────────┬───────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   ┌─────────────┐       ┌─────────────┐
   │ Changed?    │       │ Unchanged?  │
   │ (new/mod)   │       │             │
   └──────┬──────┘       └──────┬──────┘
          │                     │
          ▼                     ▼
   ┌─────────────┐       ┌─────────────┐
   │ Re-embed &  │       │   SKIP      │
   │ Upsert      │       │ (no action) │
   └─────────────┘       └─────────────┘
```

### Key Mechanisms

1. **Product ID as Unique Key**
   - Each product has a unique `product_id` (e.g., `PROD-001`)
   - Converted to numeric point ID via consistent hashing
   - Enables Qdrant's `upsert` operation

2. **Timestamp Tracking**
   - `last_updated` field tracks modification time
   - Compare with stored timestamp to detect changes

3. **Upsert Operation**
   - If product exists: updates vector and payload
   - If product is new: inserts as new point
   - No need to delete existing collection

### Running Incremental Updates

```bash
# First run (full ingest)
python src/ingestion/pipeline.py

# Monthly update (incremental)
python src/ingestion/pipeline.py --csv data/products_catalog_updated.csv

# Force full re-index
python src/ingestion/pipeline.py --recreate
```

## Usage

```python
from src.ingestion.pipeline import ProductIngestionPipeline

# Initialize
pipeline = ProductIngestionPipeline()

# Full ingestion
result = pipeline.ingest(
    csv_path="data/products_catalog.csv",
    recreate_collection=False,  # Keep existing data
    batch_size=32
)

# Search
results = pipeline.search("wireless headphones", limit=5)
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| QDRANT_HOST | localhost | Qdrant server host |
| QDRANT_PORT | 6333 | Qdrant server port |
| COLLECTION_NAME | products | Vector collection name |
| EMBEDDING_MODEL | all-MiniLM-L6-v2 | Sentence Transformer model |
