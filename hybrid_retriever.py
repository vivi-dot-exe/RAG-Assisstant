import os
import argparse
from typing import List, Dict, Any
from langchain_core.documents import Document
from hybrid_indexer import HybridIndexer

class HybridRetriever:
    """
    HybridRetriever executes hybrid search over ChromaDB dense vectors and rank_bm25 BM25Okapi sparse keywords.
    Retrieves top dense_k (20) and top sparse_k (20) results, fuses them via Reciprocal Rank Fusion (RRF),
    and returns top final_k (15) candidates with file_name, page_number, and chunk_id metadata.
    """
    def __init__(self, indexer: HybridIndexer = None, db_dir: str = "./chroma_db", rrf_k: int = 60):
        self.db_dir = db_dir
        self.rrf_k = rrf_k
        self.indexer = indexer or HybridIndexer(db_dir=self.db_dir)

    def retrieve(
        self,
        query: str,
        dense_k: int = 20,
        sparse_k: int = 20,
        final_k: int = 15
    ) -> List[Document]:
        """
        Retrieves top 20 dense results and top 20 sparse results, combines them with RRF,
        and returns the top 15 candidate documents with metadata.
        """
        print(f"Executing Hybrid Search (RRF) for query: {repr(query)}")
        print(f"  Fetching top {dense_k} dense candidates and top {sparse_k} sparse candidates...")
        
        dense_docs = self.indexer.search_dense(query, top_k=dense_k)
        sparse_docs = self.indexer.search_sparse(query, top_k=sparse_k)
        
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        # Check if query mentions a specific filename
        query_lower = query.lower()
        
        # 1. RRF Scoring for Dense Results
        for rank, doc in enumerate(dense_docs, start=1):
            chunk_id = doc.metadata.get("chunk_id", str(hash(doc.page_content)))
            doc_map[chunk_id] = doc
            score = 1.0 / (self.rrf_k + rank)
            
            # Boost if query explicitly mentions doc file_name
            fname = str(doc.metadata.get("file_name", "")).lower()
            fname_stem = fname.replace(".pdf", "")
            if fname and (fname in query_lower or fname_stem in query_lower):
                score += 1.0
                
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score

        # 2. RRF Scoring for Sparse Results
        for rank, doc in enumerate(sparse_docs, start=1):
            chunk_id = doc.metadata.get("chunk_id", str(hash(doc.page_content)))
            doc_map[chunk_id] = doc
            score = 1.0 / (self.rrf_k + rank)
            
            fname = str(doc.metadata.get("file_name", "")).lower()
            fname_stem = fname.replace(".pdf", "")
            if fname and (fname in query_lower or fname_stem in query_lower):
                score += 1.0
                
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + score

        # 3. Sort by RRF score descending and take top final_k (15)
        sorted_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)[:final_k]
        
        final_docs = []
        for cid in sorted_ids:
            doc = doc_map[cid]
            doc.metadata["rrf_score"] = round(rrf_scores[cid], 5)
            final_docs.append(doc)
            
        print(f"Reciprocal Rank Fusion complete: returned {len(final_docs)} candidate chunks.")
        return final_docs

def main():
    parser = argparse.ArgumentParser(description="HybridRetriever test CLI.")
    parser.add_argument("query", type=str, nargs="?", default="What is ChromaDB and how does it integrate with LangChain?", help="Search query")
    parser.add_argument("--source-dir", type=str, default="./source_documents", help="Source PDFs directory")
    parser.add_argument("--dense-k", type=int, default=20, help="Dense top K (default 20)")
    parser.add_argument("--sparse-k", type=int, default=20, help="Sparse top K (default 20)")
    parser.add_argument("--final-k", type=int, default=15, help="Final candidates count (default 15)")
    
    args = parser.parse_args()
    
    from pdf_processor import process_and_chunk_pdfs
    chunks = process_and_chunk_pdfs(args.source_dir, chunk_size=1000, chunk_overlap=150)
    
    if not chunks:
        print("No documents found to query.")
        return
        
    indexer = HybridIndexer(db_dir="./chroma_db")
    indexer.index_documents(chunks)
    
    retriever = HybridRetriever(indexer=indexer)
    results = retriever.retrieve(args.query, dense_k=args.dense_k, sparse_k=args.sparse_k, final_k=args.final_k)
    
    print("\n" + "=" * 80)
    print(f"TOP {len(results)} RRF HYBRID CANDIDATES:")
    print("=" * 80)
    for idx, doc in enumerate(results, 1):
        print(f"Rank {idx:02d} | RRF Score: {doc.metadata.get('rrf_score')}")
        print(f"  file_name:   {doc.metadata.get('file_name')}")
        print(f"  page_number: {doc.metadata.get('page_number')}")
        print(f"  chunk_id:    {doc.metadata.get('chunk_id')}")
        print(f"  Snippet:     {repr(doc.page_content[:70])}...")
        print("-" * 80)

if __name__ == "__main__":
    main()
