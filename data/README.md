# RAGOps Data Directory

This directory contains raw documents, processed chunks, and persistent storage artifacts for RAGOps.

## Directory Structure

```text
data/
├── raw/           # Source documents (PDF, Markdown, HTML)
├── processed/     # Processed and chunked intermediate files
├── chroma/        # ChromaDB persistent vector storage (auto-generated)
├── ragops.db      # SQLite relational database (auto-generated)
├── feedback.jsonl # User feedback records (auto-generated)
└── promotion.json # Current production RAG version metadata (auto-generated)
```

## Supported Ingestion Formats
- Markdown (`.md`, `.markdown`)
- PDF documents (`.pdf`)
- HTML files (`.html`, `.htm`)

## Ingestion CLI
```bash
ragops ingest data/raw --version v1
```
