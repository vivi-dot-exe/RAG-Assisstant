import argparse
import os
import sys

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pdf_processor import process_and_chunk_pdfs
from hybrid_indexer import HybridIndexer
from hybrid_retriever import HybridRetriever
from query_reranker import rewrite_query, CandidateReranker

def build_prompt_template():
    template = """You are a helpful and strict AI assistant. Answer the user's question using ONLY the provided context snippets below.
If the answer cannot be answered strictly based on the provided context, respond with "I cannot answer this question based on the provided context." Do not make up or infer information outside of the provided context.

Context:
{context}

Question:
{question}

Answer:"""
    return PromptTemplate.from_template(template)

def main():
    parser = argparse.ArgumentParser(description="Full RAG Pipeline with Query Rewriter, Hybrid RRF (20+20->15), CrossEncoder Reranker (->4), and GPT-4o.")
    parser.add_argument("query", type=str, help="Question/Query to process")
    parser.add_argument("--source-dir", type=str, default="./source_documents", help="Directory containing original PDF files")
    parser.add_argument("--db-dir", type=str, default="./chroma_db", help="Directory where Chroma DB is persisted")
    parser.add_argument("--top-n", type=int, default=4, help="Definitive top N chunks after reranking (default 4)")
    parser.add_argument("--openai-model", type=str, default="gpt-4o", help="OpenAI chat model name")
    
    args = parser.parse_args()

    if not os.path.exists(args.source_dir):
        print(f"Error: Source directory '{args.source_dir}' does not exist.")
        sys.exit(1)
        
    print(f"--- Step 1: Processing PDFs with pdfplumber from '{args.source_dir}' ---")
    chunks = process_and_chunk_pdfs(source_dir=args.source_dir, chunk_size=1000, chunk_overlap=150)
    if not chunks:
        print("Error: No text chunks produced.")
        sys.exit(1)

    print("\n--- Step 2: Indexing Chunks via HybridIndexer ---")
    indexer = HybridIndexer(db_dir=args.db_dir)
    indexer.index_documents(chunks)

    print("\n--- Step 3: LLM Query Rewriting ---")
    optimized_query = rewrite_query(args.query, model_name=args.openai_model)

    print("\n--- Step 4: Hybrid Candidate Retrieval (RRF Top 15 from 20 Dense + 20 Sparse) ---")
    retriever = HybridRetriever(indexer=indexer)
    top_15_candidates = retriever.retrieve(optimized_query, dense_k=20, sparse_k=20, final_k=15)

    print(f"\n--- Step 5: Cross-Encoder Reranking (Selecting Top {args.top_n} Definitive Chunks) ---")
    reranker = CandidateReranker()
    definitive_top_4 = reranker.rerank(optimized_query, top_15_candidates, top_n=args.top_n)

    if not definitive_top_4:
        print("No relevant chunks found after reranking.")
        sys.exit(0)

    context_chunks = []
    source_metadata_list = []

    print("\n" + "=" * 80)
    print(f"DEFINITIVE TOP {len(definitive_top_4)} RERANKED SOURCE CHUNKS & METADATA:")
    print("=" * 80)
    for idx, doc in enumerate(definitive_top_4, 1):
        file_name = doc.metadata.get("file_name", "Unknown")
        page_number = doc.metadata.get("page_number", 1)
        chunk_id = doc.metadata.get("chunk_id", "N/A")
        rerank_score = doc.metadata.get("rerank_score", "N/A")
        
        context_chunks.append(f"[Chunk {idx} - File: {file_name}, Page: {page_number}, ID: {chunk_id}]\n{doc.page_content}")
        
        source_metadata_list.append({
            "rank": idx,
            "file_name": file_name,
            "page_number": page_number,
            "chunk_id": chunk_id,
            "rerank_score": rerank_score,
            "snippet": doc.page_content
        })
        
        print(f"Chunk {idx} | File: {file_name} | Page: {page_number} | Chunk ID: {chunk_id} | Rerank Score: {rerank_score}")
        print(f"Content: {repr(doc.page_content[:120])}...")
        print("-" * 80)

    formatted_context = "\n\n".join(context_chunks)

    prompt_template = build_prompt_template()
    formatted_prompt = prompt_template.format(context=formatted_context, question=args.query)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\n[WARNING] OPENAI_API_KEY environment variable is not set.")
        print("Retrieved chunks and metadata are printed above.")
        return

    print(f"\nSending strict context prompt to OpenAI {args.openai_model}...")
    try:
        llm = ChatOpenAI(model=args.openai_model, temperature=0, openai_api_key=api_key)
        response = llm.invoke(formatted_prompt)
        answer = response.content

        print("\n" + "=" * 80)
        print("FINAL GPT-4o ANSWER:")
        print("=" * 80)
        print(answer)
        print("=" * 80)

        print("\nCITED SOURCES METADATA:")
        for meta in source_metadata_list:
            print(f" - [{meta['rank']}] File: {meta['file_name']} | Page: {meta['page_number']} | Chunk ID: {meta['chunk_id']} (Score: {meta['rerank_score']})")

    except Exception as e:
        print(f"\nError querying OpenAI API: {e}")

if __name__ == "__main__":
    main()
