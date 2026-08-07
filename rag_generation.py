import os
import argparse
from typing import List, Dict, Any, Tuple
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

STRICT_CONTEXT_PROMPT = PromptTemplate.from_template("""You are an intelligent, precise, and strict AI research assistant. Answer the user's question using ONLY the provided context snippets below.

STRICT INSTRUCTIONS:
1. Do NOT use outside knowledge, assumptions, or extrapolations.
2. If the question cannot be answered strictly using the provided context, respond with ONLY: "I cannot answer this question based on the provided context."
3. For EVERY fact, claim, or statement you write in your answer, you MUST append an inline citation in the exact bracketed format: [File: <file_name>, Page: <page_number>] matching the source document of that fact.

Context:
{context}

Question:
{question}

Answer (with mandatory inline citations like [File: X, Page: Y]):""")

class RAGGenerator:
    """
    RAGGenerator constructs context-stuffed prompts enforcing strict reliance on document context
    and mandatory inline citations formatted as [File: X, Page: Y].
    Returns a token-by-token streaming response generator and structured citation data.
    """
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.0):
        self.model_name = model_name
        self.temperature = temperature

    def build_context_and_citations(self, chunks: List[Document]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Formats text chunks into tagged context blocks and extracts structured citation objects.
        """
        context_blocks = []
        structured_citations = []
        
        for idx, doc in enumerate(chunks, 1):
            file_name = doc.metadata.get("file_name", "Unknown.pdf")
            page_number = doc.metadata.get("page_number", 1)
            chunk_id = doc.metadata.get("chunk_id", f"{file_name}_p{page_number}")
            
            tag = f"[File: {file_name}, Page: {page_number}]"
            context_blocks.append(f"{tag}\n{doc.page_content}")
            
            structured_citations.append({
                "citation_tag": tag,
                "file_name": file_name,
                "page_number": page_number,
                "chunk_id": chunk_id,
                "snippet": doc.page_content,
                "rerank_score": doc.metadata.get("rerank_score"),
                "rrf_score": doc.metadata.get("rrf_score")
            })
            
        formatted_context = "\n\n---\n\n".join(context_blocks)
        return formatted_context, structured_citations

    def generate(
        self,
        query: str,
        chunks: List[Document]
    ) -> Tuple[Any, List[Dict[str, Any]]]:
        """
        Builds the strict prompt and returns a streaming response generator alongside structured citations.
        """
        formatted_context, structured_citations = self.build_context_and_citations(chunks)
        
        formatted_prompt = STRICT_CONTEXT_PROMPT.format(
            context=formatted_context,
            question=query
        )
        
        api_key = os.environ.get("OPENAI_API_KEY")
        provider = (os.environ.get("LLM_PROVIDER") or "openai").lower()
        
        if (api_key and not api_key.startswith("sk-placeholder")) or provider in ["ollama", "local"]:
            try:
                from llm_factory import get_llm
                llm = get_llm(provider=provider, model_name=self.model_name, temperature=self.temperature, streaming=True)
                stream_generator = (chunk.content for chunk in llm.stream(formatted_prompt))
                return stream_generator, structured_citations
            except Exception as e:
                print(f"Notice: LLM generation issue ({e}). Using direct document context synthesis.")

        def offline_stream():
            if not chunks:
                yield "I cannot answer this question based on the provided context."
                return
                
            query_lower = query.lower()
            is_summary = any(kw in query_lower for kw in ["summarize", "summary", "overview", "explain", "about"])
            
            doc_sources = {}
            for d in chunks:
                fname = d.metadata.get("file_name", "Document.pdf")
                pnum = d.metadata.get("page_number", 1)
                if fname not in doc_sources:
                    doc_sources[fname] = []
                if pnum not in doc_sources[fname]:
                    doc_sources[fname].append(pnum)
                    
            files_str = ", ".join(doc_sources.keys())
            
            if is_summary:
                yield f"### 📘 Executive Summary: {files_str}\n\n"
                
                extracted_paragraphs = []
                for doc in chunks[:5]:
                    fname = doc.metadata.get("file_name", "Document.pdf")
                    pnum = doc.metadata.get("page_number", 1)
                    raw_text = doc.page_content.replace("•", "").strip()
                    lines = [l.strip() for l in raw_text.split('\n') if l.strip() and not l.strip().startswith(('Page ', 'Chapter ', 'http', 'www', 'Figure', 'Table')) and len(l.strip()) > 12]
                    if lines:
                        clean_text = " ".join(lines)
                        extracted_paragraphs.append((fname, pnum, clean_text))
                        
                if not extracted_paragraphs:
                    yield "No detailed text context found in the selected documents."
                    return

                # Executive overview section
                first_text = extracted_paragraphs[0][2]
                overview = first_text[:380] + ("..." if len(first_text) > 380 else "")
                yield f"**Overview:**\n{overview}\n\n"
                yield "**Core Concepts & Topics Covered:**\n\n"
                
                for idx, (fname, pnum, full_text) in enumerate(extracted_paragraphs[:4], 1):
                    # Clean snippet
                    snippet = full_text[:320] + ("..." if len(full_text) > 320 else "")
                    yield f"**{idx}. Core Topic [File: {fname}, Page {pnum}]**\n{snippet}\n\n"
            else:
                yield f"### 💡 Answer based on {files_str}\n\n"
                for doc in chunks[:4]:
                    fname = doc.metadata.get("file_name", "Document.pdf")
                    pnum = doc.metadata.get("page_number", 1)
                    raw_text = doc.page_content.replace("•", "").strip()
                    lines = [l.strip() for l in raw_text.split('\n') if l.strip() and len(l.strip()) > 12]
                    if lines:
                        clean_text = " ".join(lines)
                        yield f"• {clean_text[:350]}... `[File: {fname}, Page {pnum}]`\n\n"


        return offline_stream(), structured_citations

def main():
    parser = argparse.ArgumentParser(description="RAG Generation Chain CLI test.")
    parser.add_argument("query", type=str, nargs="?", default="What is Retrieval-Augmented Generation?", help="User query")
    args = parser.parse_args()
    
    from pdf_processor import process_and_chunk_pdfs
    from hybrid_indexer import HybridIndexer
    from hybrid_retriever import HybridRetriever
    from query_reranker import rewrite_query, CandidateReranker
    
    print("--- 1. Processing PDFs & RRF Retrieval & Reranking ---")
    chunks = process_and_chunk_pdfs("./source_documents", chunk_size=1000, chunk_overlap=150)
    if not chunks:
        print("No documents found.")
        return
        
    indexer = HybridIndexer()
    indexer.index_documents(chunks)
    
    opt_query = rewrite_query(args.query)
    retriever = HybridRetriever(indexer=indexer)
    candidates_15 = retriever.retrieve(opt_query, dense_k=20, sparse_k=20, final_k=15)
    
    reranker = CandidateReranker()
    definitive_top_4 = reranker.rerank(opt_query, candidates_15, top_n=4)
    
    print("\n--- 2. RAG Streaming Response Generation ---")
    generator = RAGGenerator(model_name="gpt-4o")
    stream, citations = generator.generate(args.query, definitive_top_4)
    
    print("\n" + "=" * 80)
    print("STREAMING ANSWER OUTPUT:")
    print("=" * 80)
    for token in stream:
        print(token, end="", flush=True)
    print("\n" + "=" * 80)
    
    print("\nSTRUCTURED CITATION DATA:")
    for cite in citations:
        print(f" - Tag: {cite['citation_tag']} | File: {cite['file_name']} | Page: {cite['page_number']} | Chunk ID: {cite['chunk_id']}")

if __name__ == "__main__":
    main()
