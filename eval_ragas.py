import os
import json
import argparse
from typing import List, Dict, Any
from datasets import Dataset

# Sample Evaluation QA Pairs for the Knowledge Base
SAMPLE_EVAL_DATASET = [
    {
        "question": "What is Retrieval-Augmented Generation (RAG)?",
        "ground_truth": "Retrieval-Augmented Generation (RAG) is a technique that combines retrieval models with generative LLMs, allowing the model to reference external, authoritative knowledge bases before formulating a response.",
        "contexts": [
            "Introduction to Retrieval-Augmented Generation (RAG)\nRetrieval-Augmented Generation (RAG) is a technique that combines retrieval models with generative LLMs. This allows the model to reference external, authoritative knowledge bases before formulating a response."
        ],
        "answer": "Retrieval-Augmented Generation (RAG) is a method combining retrieval models with generative LLMs so the model can reference external authoritative knowledge bases before answering. [File: sample_doc.pdf, Page: 1]"
    },
    {
        "question": "What is ChromaDB and what are its features?",
        "ground_truth": "ChromaDB is an open-source vector database designed for AI developers that stores embeddings, documents, and metadata, making them searchable by similarity.",
        "contexts": [
            "Vector Databases and ChromaDB\nChromaDB is an open-source vector database designed for AI developers. It stores embeddings, documents, and metadata, making them searchable by similarity. ChromaDB provides a simple interface and integrates seamlessly with LangChain."
        ],
        "answer": "ChromaDB is an open-source vector database built for AI developers. It stores document embeddings, texts, and metadata to enable similarity search and integrates with LangChain. [File: sample_doc.pdf, Page: 2]"
    },
    {
        "question": "How does pdfplumber assist in PDF processing?",
        "ground_truth": "pdfplumber extracts text page by page while preserving page boundaries and metadata.",
        "contexts": [
            "pdfplumber is used for high-fidelity text extraction. It preserves page boundaries and page metadata."
        ],
        "answer": "pdfplumber extracts text page by page, preserving page boundaries and original page metadata. [File: pdf_processor.py, Page: 1]"
    }
]

def run_ragas_evaluation(eval_samples: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes RAGAS evaluation measuring Faithfulness and Context Recall metrics over QA pairs.
    """
    samples = eval_samples or SAMPLE_EVAL_DATASET
    print(f"--- Running RAGAS Evaluation on {len(samples)} QA Pairs ---")
    
    # Format data for RAGAS Dataset
    data_dict = {
        "question": [s["question"] for s in samples],
        "contexts": [s["contexts"] for s in samples],
        "answer": [s["answer"] for s in samples],
        "ground_truth": [s["ground_truth"] for s in samples]
    }
    
    dataset = Dataset.from_dict(data_dict)
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\n[WARNING] OPENAI_API_KEY missing. RAGAS requires an LLM judge to evaluate scores.")
        print("Displaying evaluation sample dataset structure:")
        for idx, item in enumerate(samples, 1):
            print(f"\nQA Pair {idx}:")
            print(f"  Question:    {item['question']}")
            print(f"  Answer:      {item['answer']}")
            print(f"  GroundTruth: {item['ground_truth']}")
            print(f"  Contexts:    {repr(item['contexts'][0][:60])}...")
        return {"status": "skipped_missing_api_key", "sample_count": len(samples)}

    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, context_recall
        
        print("Evaluating RAGAS Metrics: 'faithfulness' & 'context_recall'...")
        results = evaluate(
            dataset=dataset,
            metrics=[faithfulness, context_recall]
        )
        
        print("\n" + "=" * 80)
        print("RAGAS EVALUATION SCORES SUMMARY:")
        print("=" * 80)
        scores = dict(results)
        for metric_name, score_val in scores.items():
            print(f"  - {metric_name.capitalize()}: {score_val:.4f}")
        print("=" * 80)
        
        # Save output JSON
        output_file = "ragas_eval_results.json"
        with open(output_file, "w") as f:
            json.dump(scores, f, indent=2)
        print(f"Saved evaluation results to '{output_file}'.")
        
        return scores

    except Exception as e:
        print(f"Error during RAGAS evaluation execution: {e}")
        return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="RAGAS Framework Evaluation Script.")
    args = parser.parse_args()
    
    run_ragas_evaluation()

if __name__ == "__main__":
    main()
