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
        if not api_key:
            print("OPENAI_API_KEY missing. Returning offline context fallback generator.")
            def mock_stream():
                yield f"OPENAI_API_KEY is missing. Here is the strict context prepared for query '{query}':\n\n{formatted_context}"
            return mock_stream(), structured_citations

        llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            openai_api_key=api_key,
            streaming=True
        )
        
        stream_generator = (chunk.content for chunk in llm.stream(formatted_prompt))
        return stream_generator, structured_citations

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
