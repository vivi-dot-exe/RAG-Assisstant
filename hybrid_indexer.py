import os
import shutil
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

class HybridIndexer:
    """
    HybridIndexer stores dense embeddings in ChromaDB using OpenAI text-embedding-3-small
    (with HuggingFace fallback if OPENAI_API_KEY is not set) and builds an in-memory BM25Okapi
    index using rank_bm25 for sparse keyword search.
    """
    def __init__(
        self,
        db_dir: str = "./chroma_db",
        embedding_model: str = "text-embedding-3-small",
        fallback_model: str = "all-MiniLM-L6-v2"
    ):
        self.db_dir = db_dir
        self.embedding_model_name = embedding_model
        self.fallback_model_name = fallback_model
        
        # Initialize Embeddings Engine
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            print(f"Initializing OpenAI Embeddings ({self.embedding_model_name})...")
            self.embeddings = OpenAIEmbeddings(
                model=self.embedding_model_name,
                openai_api_key=api_key
            )
        else:
            print(f"OPENAI_API_KEY missing. Falling back to local Hugging Face Embeddings ({self.fallback_model_name})...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.fallback_model_name,
                model_kwargs={'device': 'cpu'}
            )
            
        self.vector_store = None
        self.bm25_index = None
        self.chunks: List[Document] = []
        
    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace and lowercasing tokenizer for BM25Okapi."""
        return text.lower().split()

    def index_documents(self, chunks: List[Document]) -> Tuple[int, int]:
        """
        Stores dense embeddings in ChromaDB and builds an in-memory BM25Okapi index.
        Preserves metadata: file_name, page_number, chunk_id.
        """
        if not chunks:
            print("No chunks provided for indexing.")
            return 0, 0
            
        self.chunks = chunks
        print(f"Indexing {len(chunks)} chunks into ChromaDB & BM25Okapi...")

        # 1. Dense Storage (ChromaDB)
        if os.path.exists(self.db_dir):
            try:
                shutil.rmtree(self.db_dir)
            except Exception as e:
                print(f"Notice: Using existing directory '{self.db_dir}' ({e}). Updating vector collection...")

        try:
            self.vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=self.db_dir
            )
        except Exception as e:
            print(f"Embedding error with primary model ({e}). Falling back to local Hugging Face Embeddings...")
            from langchain_huggingface import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            self.vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=self.db_dir
            )

        # 2. Sparse Indexing (rank_bm25 BM25Okapi)
        tokenized_corpus = [self._tokenize(doc.page_content) for doc in chunks]
        self.bm25_index = BM25Okapi(tokenized_corpus)
        
        print(f"Successfully created dense vector store at '{self.db_dir}' and in-memory BM25Okapi index.")
        return len(chunks), len(tokenized_corpus)

    def search_dense(self, query: str, top_k: int = 5) -> List[Document]:
        """Performs dense vector similarity search in ChromaDB."""
        if not self.vector_store:
            if os.path.exists(self.db_dir):
                self.vector_store = Chroma(
                    persist_directory=self.db_dir,
                    embedding_function=self.embeddings
                )
            else:
                print("Vector store not initialized.")
                return []
                
        return self.vector_store.similarity_search(query, k=top_k)

    def search_sparse(self, query: str, top_k: int = 5) -> List[Document]:
        """Performs sparse keyword search using rank_bm25 BM25Okapi."""
        if not self.bm25_index or not self.chunks:
            print("BM25 index not built.")
            return []
            
        tokenized_query = self._tokenize(query)
        scores = self.bm25_index.get_scores(tokenized_query)
        
        # Sort indices by score descending
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self.chunks[i] for i in top_indices if scores[i] > 0]

    def search_hybrid(self, query: str, top_k: int = 5, rrf_k: int = 60) -> List[Document]:
        """
        Combines dense vector search and sparse BM25 search using Reciprocal Rank Fusion (RRF).
        Returns top_k documents with metadata file_name, page_number, and chunk_id.
        """
        dense_results = self.search_dense(query, top_k=top_k * 2)
        sparse_results = self.search_sparse(query, top_k=top_k * 2)
        
        if not dense_results and not sparse_results:
            return []
            
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}
        
        # Dense ranking
        for rank, doc in enumerate(dense_results, start=1):
            chunk_id = doc.metadata.get("chunk_id", str(hash(doc.page_content)))
            doc_map[chunk_id] = doc
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (rrf_k + rank))
            
        # Sparse ranking
        for rank, doc in enumerate(sparse_results, start=1):
            chunk_id = doc.metadata.get("chunk_id", str(hash(doc.page_content)))
            doc_map[chunk_id] = doc
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (rrf_k + rank))
            
        # Sort by RRF score descending
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]
        return [doc_map[cid] for cid in sorted_chunk_ids]

def main():
    from pdf_processor import process_and_chunk_pdfs
    
    print("Testing HybridIndexer with pdf_processor chunks...")
    chunks = process_and_chunk_pdfs("./source_documents", chunk_size=1000, chunk_overlap=150)
    
    if not chunks:
        print("No chunks found for testing.")
        return
        
    indexer = HybridIndexer(db_dir="./chroma_db", embedding_model="text-embedding-3-small")
    indexer.index_documents(chunks)
    
    query = "What is ChromaDB and how does it integrate with LangChain?"
    print(f"\nSearching hybrid for: {repr(query)}")
    results = indexer.search_hybrid(query, top_k=3)
    
    print("\n--- HYBRID SEARCH RESULTS ---")
    for idx, doc in enumerate(results, 1):
        print(f"Result {idx}:")
        print(f"  file_name:   {doc.metadata.get('file_name')}")
        print(f"  page_number: {doc.metadata.get('page_number')}")
        print(f"  chunk_id:    {doc.metadata.get('chunk_id')}")
        print(f"  Snippet:     {repr(doc.page_content[:60])}...")
        print("-" * 60)

if __name__ == "__main__":
    main()
