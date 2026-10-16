# RAGOps Security and Governance Handbook

## Authentication and Authorization
1. **API Security**:
   - All production HTTP API traffic must terminate over TLS 1.3.
   - API keys and tokens must be passed via standard `Authorization: Bearer <token>` headers.
   - Groq API credentials must reside solely in environment configurations or secret management vaults.

2. **Access Control & Permissions**:
   - Role-Based Access Control (RBAC) separates administrative ingestion endpoints from public query endpoints.
   - Ingestion endpoints (`/api/v1/ingest`) require administrative privileges.
   - User feedback endpoints (`/api/v1/feedback`) validate payload schemas and sanitize text commentary.

3. **Data Protection & Compliance**:
   - Documents processed through the ingestion pipeline undergo metadata tagging including provenance, author, and classification levels.
   - Chunk contents stored in vector stores must not contain unmasked Personally Identifiable Information (PII).
   - In-flight database interactions utilize SQLAlchemy ORM with parameterized queries to prevent SQL injection.

4. **Rate Limiting and Abuse Prevention**:
   - Rate limiting is enforced at 100 requests per minute per IP address on query endpoints.
   - Maximum query string length is capped at 1000 characters to prevent denial-of-service via excessive token usage.
