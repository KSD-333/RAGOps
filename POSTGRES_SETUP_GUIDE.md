# RAGOps PostgreSQL Integration & Observability Operations Guide

This guide explains how to connect and run **PostgreSQL** with RAGOps, how the authentication and telemetry persistence works, and how to query the stored chat history, tokens, chunk provenance, and ML risk signals.

---

## 1. Architectural Overview

RAGOps uses a production-grade dual storage model:
1. **Vector Store (ChromaDB / Qdrant):** Stores document chunk embeddings and performs Approximate Nearest Neighbor (ANN) semantic search.
2. **Relational Database (PostgreSQL with SQLite failover):** Stores:
   - User authentication and roles (`admin`, `test1`, `test2`) with SHA-256 salted hashes.
   - Comprehensive chat messages telemetry:
     - Accurate timestamp (`created_at` in UTC)
     - Input tokens, output tokens, total tokens, and USD cost per query
     - Hop-by-hop latency (Embedding $\rightarrow$ Vector Search $\rightarrow$ Cross-Encoder Rerank $\rightarrow$ LLM Generation)
     - Complete chunk provenance (`chunks_sent` JSON with chunk IDs, document names, page numbers, similarity scores, and text snippets)
     - Grounded citations and user feedback ratings (👍 / 👎)
     - **Future ML signals:** Churn risk flags, POSH/compliance policy risk flags, intent categories, and training readiness.

---

## 2. Default Test Credentials

The system seeds three test accounts automatically into the database on startup:

| Username | Email | Default Password | Role | Description |
|---|---|---|---|---|
| **`admin`** | `admin@ragops.io` | `admin123` | **ADMIN** | Full administrative visibility across all users, trace logs, spend metrics, and risk monitors. |
| **`test1`** | `test1@ragops.io` | `test123` | **USER** | Standard enterprise employee user (HR & general knowledge questions). |
| **`test2`** | `test2@ragops.io` | `test223` | **USER** | Standard developer user (cluster, TLS, and technical documentation questions). |

> **Security Note:** Passwords are never stored in plaintext. They are hashed using `SHA-256` with a unique 32-character random cryptographic salt (`hashlib.sha256(salt + password)`).

---

## 3. How to Connect PostgreSQL (Step-by-Step)

### Option A: Using Docker (Recommended — 30 Seconds)
Run a PostgreSQL 16 container with a single command:
```bash
docker run --name ragops-postgres \
  -e POSTGRES_USER=ragops \
  -e POSTGRES_PASSWORD=ragops \
  -e POSTGRES_DB=ragops \
  -p 5432:5432 \
  -d postgres:16-alpine
```

### Option B: Using Docker Compose
In your project root, launch the `postgres` service from `compose/docker-compose.yml`:
```bash
docker compose -f compose/docker-compose.yml up -d postgres
```

### Step 2: Set the Connection String in `.env`
Open your `.env` file and set:
```ini
# --- PostgreSQL Database ---
DATABASE_URL=postgresql://ragops:ragops@localhost:5432/ragops
```
*(If you have a remote PostgreSQL or cloud managed database like Supabase, Neon, RDS, or Cloud SQL, just replace the URL with your cloud connection string).*

### Step 3: Start the Backend Server
```bash
ragops serve
# Or: uvicorn ragops.api.app:app --host 0.0.0.0 --port 8000 --reload
```
On startup, RAGOps will automatically:
1. Connect to PostgreSQL via connection pool (`pool_size=10, max_overflow=20, pool_pre_ping=True`).
2. Run `Base.metadata.create_all()` to create all tables and indexes.
3. Seed the default dummy users (`admin`, `test1`, `test2`).
4. **Resilient Failover:** If PostgreSQL is unreachable or not started, RAGOps automatically logs a warning and falls back to local SQLite (`./data/ragops.db`) so the application never crashes!

---

## 4. Database Schema Details

### 1. `users` Table
Stores registered accounts and authentication hashes.
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    salt VARCHAR(64) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2. `chat_messages` Table (Telemetry & Provenance Engine)
Stores every user question, generated answer, and diagnostic telemetry.
```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(100) UNIQUE NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    trace_id VARCHAR(100) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50) NOT NULL,
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    model VARCHAR(100) NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    embed_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    search_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    rerank_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    generation_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    total_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    chunks_sent JSONB NOT NULL DEFAULT '[]',
    citations JSONB NOT NULL DEFAULT '[]',
    feedback_rating VARCHAR(20),
    feedback_comment TEXT DEFAULT '',
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    intent VARCHAR(100) NOT NULL DEFAULT 'information_retrieval',
    sentiment_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    churn_risk_flag BOOLEAN NOT NULL DEFAULT FALSE,
    policy_risk_flag BOOLEAN NOT NULL DEFAULT FALSE,
    training_ready BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Performance Indexes
CREATE INDEX idx_chat_username_created ON chat_messages(username, created_at DESC);
CREATE INDEX idx_chat_user_id_created ON chat_messages(user_id, created_at DESC);
CREATE INDEX idx_chat_risk_created ON chat_messages(policy_risk_flag, churn_risk_flag, created_at DESC);
```

---

## 5. Useful SQL Queries for Admins

Connect via `psql` or DBeaver:
```bash
docker exec -it ragops-postgres psql -U ragops -d ragops
```

### Query 1: View User Consumption & Token Spend
```sql
SELECT 
    username, 
    COUNT(*) AS total_queries, 
    SUM(total_tokens) AS total_tokens, 
    ROUND(SUM(cost_usd)::numeric, 5) AS total_spend_usd,
    ROUND(AVG(total_latency_ms)::numeric, 1) AS avg_latency_ms,
    MAX(created_at) AS last_active
FROM chat_messages
GROUP BY username
ORDER BY total_tokens DESC;
```

### Query 2: Frequently Asked Questions (FAQ Grouping)
```sql
SELECT 
    LOWER(TRIM(query)) AS question, 
    COUNT(*) AS occurrences,
    ROUND(AVG(total_latency_ms)::numeric, 1) AS avg_latency_ms
FROM chat_messages
GROUP BY question
ORDER BY occurrences DESC
LIMIT 10;
```

### Query 3: Inspect Churn & POSH / Policy Compliance Risk Queries
```sql
SELECT 
    created_at,
    username,
    query,
    CASE 
        WHEN policy_risk_flag = TRUE THEN 'POSH / HR COMPLIANCE'
        WHEN churn_risk_flag = TRUE THEN 'USER CHURN / LEAVING'
        ELSE 'NORMAL'
    END AS risk_category,
    answer
FROM chat_messages
WHERE policy_risk_flag = TRUE OR churn_risk_flag = TRUE
ORDER BY created_at DESC;
```

### Query 4: Inspect What Chunks Were Sent for a Specific Query
```sql
SELECT 
    trace_id, 
    query, 
    chunks_sent
FROM chat_messages 
WHERE username = 'test1'
ORDER BY created_at DESC 
LIMIT 1;
```

---

## 6. Future Machine Learning & AI Training Readiness

The schema was designed with specific columns for future machine learning and analytical pipelines:
1. **Direct Preference Optimization (DPO / RLHF):** Queries where `feedback_rating = 'positive'` are flagged as `training_ready = TRUE`. You can export them via:
   `GET /api/v1/admin/training-export`
2. **Intent Classification & Churn Prediction:**
   - User churn queries (e.g. asking how to cancel or expressing frustration) are tagged with `churn_risk_flag = TRUE`.
   - Sensitive workplace queries (e.g. POSH, harassment, whistleblower complaints) are tagged with `policy_risk_flag = TRUE`.
   - This provides labeled training datasets to train custom classifiers or trigger automated Slack/Email alerts to HR/Security.
