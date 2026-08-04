import os
import glob
import argparse
import pdfplumber
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def extract_pages_with_pdfplumber(pdf_path: str) -> List[Document]:
    """Loads a single PDF using pdfplumber, preserving page boundaries and page metadata."""
    file_name = os.path.basename(pdf_path)
    page_documents = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    doc = Document(
                        page_content=text,
                        metadata={
                            "file_name": file_name,
                            "page_number": page_idx,
                            "source": pdf_path
                        }
                    )
                    page_documents.append(doc)
    except Exception as e:
        print(f"Error reading '{pdf_path}' with pdfplumber: {e}")
        
    return page_documents

def load_directory_pdfs(source_dir: str) -> List[Document]:
    """Scans directory recursively for PDFs and extracts text page by page using pdfplumber."""
    all_page_docs = []
    pdf_files = glob.glob(os.path.join(source_dir, "**/*.pdf"), recursive=True)
    
    for pdf_path in pdf_files:
        docs = extract_pages_with_pdfplumber(pdf_path)
        all_page_docs.extend(docs)
        
    return all_page_docs

def process_and_chunk_pdfs(
    source_dir: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150
) -> List[Document]:
    """
    Loads all PDFs in source_dir with pdfplumber, splits text recursively with specified
    chunk_size and chunk_overlap, and assigns a unique chunk_id to every chunk's metadata.
    """
    # 1. Load pages with pdfplumber
    page_documents = load_directory_pdfs(source_dir)
    if not page_documents:
        print(f"No valid PDF text extracted from '{source_dir}'.")
        return []
        
    print(f"Loaded {len(page_documents)} pages across PDFs using pdfplumber.")
    
    # 2. Split text recursively with 1000 size / 150 overlap
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True
    )
    
    raw_chunks = text_splitter.split_documents(page_documents)
    
    # 3. Attach unique chunk_id and enforce required metadata
    final_chunks = []
    page_chunk_counters = {} # tracks chunk index per (file_name, page_number)
    
    for chunk in raw_chunks:
        file_name = chunk.metadata.get("file_name", "unknown.pdf")
        page_number = chunk.metadata.get("page_number", 1)
        
        # Track unique chunk index per page
        key = (file_name, page_number)
        chunk_idx = page_chunk_counters.get(key, 0)
        page_chunk_counters[key] = chunk_idx + 1
        
        # Unique chunk ID format: <file_name>_p<page_number>_c<chunk_idx>
        unique_chunk_id = f"{file_name}_p{page_number}_c{chunk_idx}"
        
        # Enforce exact metadata schema
        chunk.metadata["file_name"] = file_name
        chunk.metadata["page_number"] = page_number
        chunk.metadata["chunk_id"] = unique_chunk_id
        # Retain standard compatibility keys
        chunk.metadata["page"] = page_number - 1 # 0-indexed for legacy compatibility
        
        final_chunks.append(chunk)
        
    print(f"Created {len(final_chunks)} chunks with unique chunk_ids.")
    return final_chunks

def main():
    parser = argparse.ArgumentParser(description="Modular pdfplumber text extractor and chunk processor.")
    parser.add_argument("--source-dir", type=str, default="./source_documents", help="Path to PDF directory")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size (default 1000)")
    parser.add_argument("--chunk-overlap", type=int, default=150, help="Chunk overlap (default 150)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.source_dir):
        print(f"Directory '{args.source_dir}' does not exist.")
        return
        
    chunks = process_and_chunk_pdfs(args.source_dir, args.chunk_size, args.chunk_overlap)
    
    if chunks:
        print("\n--- SAMPLE EXTRACTED CHUNKS & METADATA ---")
        for idx, chunk in enumerate(chunks[:3], 1):
            print(f"Chunk {idx}:")
            print(f"  file_name:   {chunk.metadata['file_name']}")
            print(f"  page_number: {chunk.metadata['page_number']}")
            print(f"  chunk_id:    {chunk.metadata['chunk_id']}")
            print(f"  Snippet:     {repr(chunk.page_content[:60])}...")
            print("-" * 60)

if __name__ == "__main__":
    main()
