import os
import argparse
from typing import List
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from sentence_transformers import CrossEncoder

def rewrite_query(query: str, model_name: str = "gpt-4o") -> str:
    """
    Uses ChatOpenAI to rewrite and optimize the user's raw query for improved vector and keyword retrieval.
    If OPENAI_API_KEY is not set, returns the original query cleanly.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set for query rewriting. Using raw query.")
        return query

    prompt_template = PromptTemplate.from_template(
        "You are an expert search query optimizer. Given the following user question, "
        "reformulate it into a clear, concise, and keyword-rich search query designed "
        "to retrieve highly relevant documents. Output ONLY the rewritten query text.\n\n"
        "User Question: {question}\n\n"
        "Rewritten Query:"
    )
    
    try:
        llm = ChatOpenAI(model=model_name, temperature=0, openai_api_key=api_key)
        formatted_prompt = prompt_template.format(question=query)
        response = llm.invoke(formatted_prompt)
        rewritten = response.content.strip()
        print(f"Original Query:  {repr(query)}")
        print(f"Rewritten Query: {repr(rewritten)}")
        return rewritten if rewritten else query
    except Exception as e:
        print(f"Error rewriting query: {e}. Falling back to raw query.")
        return query

class CandidateReranker:
    """
    CandidateReranker takes candidate document chunks (e.g. top 15 RRF candidates),
    scores them against the query using a Cross-Encoder / Reranker model,
    and returns the top_n (4) definitive most relevant chunks preserving all metadata.
    """
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        print(f"Loading Cross-Encoder Reranker ({self.model_name})...")
        self.encoder = CrossEncoder(self.model_name)

    def rerank(self, query: str, candidate_chunks: List[Document], top_n: int = 4) -> List[Document]:
        """
        Reranks top candidate chunks using Cross-Encoder pair scoring (query, passage).
        Returns top_n (4) candidates preserving file_name, page_number, and chunk_id metadata.
        """
        if not candidate_chunks:
            print("No candidate chunks provided to rerank.")
            return []
            
        print(f"Reranking {len(candidate_chunks)} candidate chunks using Cross-Encoder...")
        
        # Prepare pairs for Cross-Encoder (query, passage_text)
        pairs = [[query, doc.page_content] for doc in candidate_chunks]
        
        # Predict relevance scores
        scores = self.encoder.predict(pairs)
        
        # Zip documents with scores
        scored_docs = []
        for doc, score in zip(candidate_chunks, scores):
            doc.metadata["rerank_score"] = float(round(score, 5))
            scored_docs.append((doc, score))
            
        # Sort by relevance score descending
        scored_docs.sort(key=lambda item: item[1], reverse=True)
        
        top_reranked = [doc for doc, score in scored_docs[:top_n]]
        print(f"Reranking complete: selected top {len(top_reranked)} definitive chunks.")
        return top_reranked

def main():
    parser = argparse.ArgumentParser(description="Query Rewriter and Candidate Reranker CLI.")
    parser.add_argument("query", type=str, nargs="?", default="How does ChromaDB work and integrate with LangChain?", help="User query")
    parser.add_argument("--top-n", type=int, default=4, help="Definitive top N candidates to return (default 4)")
    
    args = parser.parse_args()
    
    from pdf_processor import process_and_chunk_pdfs
    from hybrid_retriever import HybridRetriever
    
    print("--- 1. Chunking PDFs ---")
    chunks = process_and_chunk_pdfs("./source_documents", chunk_size=1000, chunk_overlap=150)
    if not chunks:
        print("No documents found for testing.")
        return

    print("\n--- 2. Rewriting User Query ---")
    optimized_query = rewrite_query(args.query)

    print("\n--- 3. Hybrid RRF Candidate Retrieval (Top 15) ---")
    retriever = HybridRetriever()
    retriever.indexer.index_documents(chunks)
    candidate_15 = retriever.retrieve(optimized_query, dense_k=20, sparse_k=20, final_k=15)

    print(f"\n--- 4. Cross-Encoder Reranking (Selecting Top {args.top_n}) ---")
    reranker = CandidateReranker()
    definitive_top_4 = reranker.rerank(optimized_query, candidate_15, top_n=args.top_n)

    print("\n" + "=" * 80)
    print(f"DEFINITIVE TOP {len(definitive_top_4)} RERANKED CHUNKS & METADATA:")
    print("=" * 80)
    for idx, doc in enumerate(definitive_top_4, 1):
        print(f"Top {idx} | Rerank Score: {doc.metadata.get('rerank_score')} | RRF Score: {doc.metadata.get('rrf_score')}")
        print(f"  file_name:   {doc.metadata.get('file_name')}")
        print(f"  page_number: {doc.metadata.get('page_number')}")
        print(f"  chunk_id:    {doc.metadata.get('chunk_id')}")
        print(f"  Snippet:     {repr(doc.page_content[:70])}...")
        print("-" * 80)

if __name__ == "__main__":
    main()
