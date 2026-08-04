# Cortex RAG Assistant 🚀

A production-ready, modular **Retrieval-Augmented Generation (RAG)** intelligence platform built with **LangChain**, **ChromaDB**, **rank_bm25**, **Cross-Encoder Reranking**, **Streamlit**, and **Next.js (React) with Tailwind CSS**.

---

## ✨ Features & Architecture

```
PDFs (pdfplumber) ➔ Chunks + Page Metadata ➔ HybridIndexer (OpenAI text-embedding-3-small + BM25Okapi) 
➔ HybridRetriever (Reciprocal Rank Fusion 20+20 ➔ 15) ➔ Query Rewriter & Cross-Encoder Reranker (➔ Top 4) 
➔ RAGGenerator (Strict Context + [File: X, Page: Y] Inline Citations) ➔ Streamlit / Next.js React UI
```

1. **High-Fidelity PDF Ingestion (`pdf_processor.py`)**:
   - Page-by-page text extraction preserving 1-indexed page boundaries using `pdfplumber`.
   - Recursive character chunking (1000 token chunk size, 150 token overlap).
   - Generates unique metadata IDs: `file_name`, `page_number`, `chunk_id`.

2. **Hybrid Indexing (`hybrid_indexer.py`)**:
   - **Dense Store**: ChromaDB with `text-embedding-3-small` (with local `all-MiniLM-L6-v2` fallback).
   - **Sparse Store**: In-memory `BM25Okapi` index using `rank_bm25`.

3. **Reciprocal Rank Fusion Retriever (`hybrid_retriever.py`)**:
   - Retrieves top 20 dense vector candidates + top 20 sparse BM25 candidates.
   - Combines and re-scores candidates using the **Reciprocal Rank Fusion (RRF, k=60)** algorithm to yield the top 15 candidate chunks.

4. **Query Rewriting & Cross-Encoder Reranking (`query_reranker.py`)**:
   - **LLM Query Rewriter**: Expands raw user questions into keyword-rich search queries.
   - **Cross-Encoder Reranker**: Rescores `(query, passage)` pairs using `cross-encoder/ms-marco-MiniLM-L-6-v2` to select the definitive **top 4 chunks**.

5. **Strict Context Prompting & Token Streaming (`rag_generation.py`)**:
   - Context-stuffed prompt template strictly forbidding outside knowledge.
   - Mandates inline citations formatted as `[File: <file_name>, Page: <page_number>]`.
   - Returns a token-by-token streaming generator and structured citation metadata.

6. **Unified LLM Factory (`llm_factory.py`)**:
   - Seamlessly toggles between **OpenAI (`gpt-4o`)** and **Local Ollama (`llama3`)**.

7. **RAGAS Evaluation Framework (`eval_ragas.py`)**:
   - Evaluates **Faithfulness** and **Context Recall** metrics over benchmark QA test pairs.

8. **Modern User Interfaces**:
   - **Streamlit Web Application (`app.py`)**: Soft pastel lavender styling, zero dark boxes, typewriter token streaming, inline citation buttons, and expandable document viewer.
   - **Next.js React Dashboard (`components/RAGDashboard.jsx`)**: Glassmorphic UI with Tailwind CSS and Lucide React icons.

---

## 🛠️ Quick Start

### 1. Installation

```bash
# Clone repository
git clone <your-repo-url>
cd RAG-Assistant

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Set your OpenAI API key (optional if using local Ollama & local embeddings):

```bash
set OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run Web Application

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🧪 Testing & Modules

- **Run Full Pipeline CLI**:
  ```bash
  python rag_pipeline.py "What is Retrieval-Augmented Generation?"
  ```
- **Inspect Vector Database**:
  ```bash
  python view_database.py
  ```
- **Run RAGAS Evaluation Framework**:
  ```bash
  python eval_ragas.py
  ```

---

## 📄 License

MIT License
