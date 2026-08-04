import os
import argparse
from pdf_processor import process_and_chunk_pdfs
from hybrid_indexer import HybridIndexer

def main():
    parser = argparse.ArgumentParser(description="Ingest PDFs into ChromaDB & BM25 using HybridIndexer.")
    parser.add_argument("--source-dir", type=str, default="./source_documents", help="Directory containing PDF files")
    parser.add_argument("--db-dir", type=str, default="./chroma_db", help="Directory to persist Chroma database")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Text chunk size")
    parser.add_argument("--chunk-overlap", type=int, default=150, help="Text chunk overlap")
    parser.add_argument("--embedding-model", type=str, default="text-embedding-3-small", help="OpenAI embedding model")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.source_dir):
        os.makedirs(args.source_dir)
        print(f"Created source directory at '{args.source_dir}'. Please place PDF files there and rerun.")
        return
        
    print(f"--- Extracting text and chunking PDFs from '{args.source_dir}' ---")
    chunks = process_and_chunk_pdfs(
        source_dir=args.source_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    if not chunks:
        print(f"No text chunks generated from '{args.source_dir}'.")
        return

    print("\n--- Indexing via HybridIndexer ---")
    indexer = HybridIndexer(db_dir=args.db_dir, embedding_model=args.embedding_model)
    doc_count, corpus_count = indexer.index_documents(chunks)
    
    print(f"Success! Indexed {doc_count} chunks with dense embeddings & rank_bm25 BM25Okapi.")

if __name__ == "__main__":
    main()
