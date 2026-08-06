import os
import shutil
import json
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

from pdf_processor import process_and_chunk_pdfs
from hybrid_indexer import HybridIndexer
from hybrid_retriever import HybridRetriever
from query_reranker import rewrite_query, CandidateReranker
from rag_generation import RAGGenerator

app = FastAPI(
    title="Cortex RAG Assistant API",
    description="FastAPI backend connecting React UI to Hybrid RAG Pipeline and Ingestion Engine",
    version="1.0.0"
)

# CORS setup for React frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SOURCE_DIR = "./source_documents"
DB_DIR = "./chroma_db"
os.makedirs(SOURCE_DIR, exist_ok=True)

# Global lazy instances
_indexer: Optional[HybridIndexer] = None
_reranker: Optional[CandidateReranker] = None

def get_indexer() -> HybridIndexer:
    global _indexer
    if _indexer is None:
        _indexer = HybridIndexer(db_dir=DB_DIR)
    return _indexer

def get_reranker() -> CandidateReranker:
    global _reranker
    if _reranker is None:
        _reranker = CandidateReranker()
    return _reranker

def format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"

def get_pdf_page_count(filepath: str) -> int:
    try:
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        return len(reader.pages)
    except Exception:
        return 1

# Request Schemas
class ChatRequest(BaseModel):
    query: str
    provider: Optional[str] = "openai"
    model: Optional[str] = "gpt-4o"
    top_n: Optional[int] = 4
    stream: Optional[bool] = False
    attached_files: Optional[List[str]] = None

class ConfigRequest(BaseModel):
    provider: Optional[str] = "openai"
    apiKey: Optional[str] = None
    model: Optional[str] = None
    ollamaUrl: Optional[str] = "http://localhost:11434"

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Cortex RAG Assistant FastAPI Backend",
        "docs": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/config")
def update_config(config: ConfigRequest):
    if config.provider:
        os.environ["LLM_PROVIDER"] = config.provider.lower()
    if config.model:
        os.environ["LLM_MODEL"] = config.model
    if config.apiKey:
        os.environ["OPENAI_API_KEY"] = config.apiKey
    if config.ollamaUrl:
        os.environ["OLLAMA_BASE_URL"] = config.ollamaUrl
        
    return {
        "status": "success",
        "provider": os.environ.get("LLM_PROVIDER", "openai"),
        "model": os.environ.get("LLM_MODEL", "gpt-4o"),
        "ollamaUrl": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        "has_openai_key": bool(os.environ.get("OPENAI_API_KEY"))
    }

@app.get("/api/documents")
def list_documents():
    if not os.path.exists(SOURCE_DIR):
        return {"documents": []}
        
    files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(".pdf")]
    docs = []
    for idx, filename in enumerate(files, 1):
        filepath = os.path.join(SOURCE_DIR, filename)
        size_bytes = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        pages = get_pdf_page_count(filepath)
        docs.append({
            "id": str(idx),
            "name": filename,
            "pages": pages,
            "size": format_file_size(size_bytes)
        })
    return {"documents": docs}

@app.delete("/api/documents/{filename}")
def delete_document(filename: str):
    filepath = os.path.join(SOURCE_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Document not found")
        
    os.remove(filepath)
    
    # Re-index remaining files
    chunks = process_and_chunk_pdfs(SOURCE_DIR, chunk_size=1000, chunk_overlap=150)
    indexer = get_indexer()
    doc_count, corpus_count = indexer.index_documents(chunks)
    
    return {
        "status": "success",
        "message": f"Deleted {filename} and re-indexed knowledge base.",
        "indexed_chunks": doc_count
    }

@app.post("/api/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
        
    saved_files = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            continue
        file_path = os.path.join(SOURCE_DIR, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved_files.append(file.filename)
        
    if not saved_files:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    # Run ingestion / indexer pipeline directly
    chunks = process_and_chunk_pdfs(SOURCE_DIR, chunk_size=1000, chunk_overlap=150)
    if not chunks:
        return {
            "status": "warning",
            "message": "Uploaded files saved, but no text content could be extracted.",
            "files": saved_files,
            "indexed_chunks": 0
        }
        
    indexer = get_indexer()
    doc_count, corpus_count = indexer.index_documents(chunks)
    
    # Return refreshed document list
    doc_list_res = list_documents()
    
    return {
        "status": "success",
        "message": f"Successfully indexed {doc_count} chunks from {len(saved_files)} PDF file(s).",
        "saved_files": saved_files,
        "indexed_chunks": doc_count,
        "documents": doc_list_res["documents"]
    }

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    existing_pdfs = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(".pdf")] if os.path.exists(SOURCE_DIR) else []
    if not existing_pdfs:
        return {
            "role": "assistant",
            "content": "No PDF documents found in your knowledge base. Please upload PDF files first.",
            "citations": []
        }
        
    chunks = process_and_chunk_pdfs(SOURCE_DIR, chunk_size=1000, chunk_overlap=150)
    if not chunks:
        return {
            "role": "assistant",
            "content": "No valid text content found in your uploaded PDFs. Please check your uploaded files.",
            "citations": []
        }
        
    # If explicit attached files provided in request, filter chunks to ONLY attached files
    if req.attached_files and len(req.attached_files) > 0:
        target_names = [f.lower().strip() for f in req.attached_files]
        filtered = [c for c in chunks if c.metadata.get("file_name", "").lower().strip() in target_names]
        if filtered:
            chunks = filtered
        
    indexer = get_indexer()
    indexer.index_documents(chunks)
    
    # 1. Query Rewrite
    model_name = req.model or os.environ.get("LLM_MODEL", "gpt-4o")
    opt_query = rewrite_query(req.query, model_name=model_name)
    
    # 2. Hybrid Candidate Retrieval (RRF Top 15)
    retriever = HybridRetriever(indexer=indexer)
    candidates_15 = retriever.retrieve(opt_query, dense_k=20, sparse_k=20, final_k=15)
    
    if not candidates_15:
        return {
            "role": "assistant",
            "content": "No relevant context found in your documents for this question.",
            "citations": []
        }
        
    # 3. Cross-Encoder Rerank (Top 4)
    top_n = req.top_n or 4
    reranker = get_reranker()
    definitive_top_chunks = reranker.rerank(opt_query, candidates_15, top_n=top_n)
    
    # 4. RAG Generation
    generator = RAGGenerator(model_name=model_name)
    stream_gen, structured_citations = generator.generate(req.query, definitive_top_chunks)
    
    if req.stream:
        async def event_generator():
            for token in stream_gen:
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            yield f"data: {json.dumps({'type': 'citations', 'citations': structured_citations})}\n\n"
            yield "data: [DONE]\n\n"
            
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        full_response = "".join(list(stream_gen))
        return {
            "role": "assistant",
            "content": full_response,
            "citations": structured_citations,
            "optimized_query": opt_query
        }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
