import os
import argparse
from typing import Optional, Any
from langchain_core.language_models.chat_models import BaseChatModel

def get_llm(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    base_url: Optional[str] = None,
    streaming: bool = False
) -> BaseChatModel:
    """
    Unified LLM Factory interface. Seamlessly toggles between ChatOpenAI and ChatOllama
    based on configuration parameters or environment variables (LLM_PROVIDER, LLM_MODEL).
    """
    resolved_provider = (provider or os.environ.get("LLM_PROVIDER") or "openai").lower().strip()
    
    if resolved_provider in ["ollama", "local"]:
        resolved_model = model_name or os.environ.get("LLM_MODEL") or "llama3"
        resolved_url = base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        print(f"--- Loading LLM via Ollama (Model: '{resolved_model}', URL: '{resolved_url}') ---")
        
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=resolved_model,
                base_url=resolved_url,
                temperature=temperature
            )
        except ImportError:
            try:
                from langchain_community.chat_models import ChatOllama
                return ChatOllama(
                    model=resolved_model,
                    base_url=resolved_url,
                    temperature=temperature
                )
            except Exception as e:
                print(f"Error initializing ChatOllama: {e}. Falling back to ChatOpenAI.")
                resolved_provider = "openai"

    # Default / OpenAI Provider
    resolved_model = model_name or os.environ.get("LLM_MODEL") or "gpt-4o"
    api_key = os.environ.get("OPENAI_API_KEY") or "sk-placeholder-key-set-in-sidebar"
    print(f"--- Loading LLM via OpenAI (Model: '{resolved_model}') ---")
    
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=resolved_model,
        temperature=temperature,
        openai_api_key=api_key,
        streaming=streaming
    )

def main():
    parser = argparse.ArgumentParser(description="LLM Factory Test CLI.")
    parser.add_argument("--provider", type=str, default="openai", choices=["openai", "ollama"], help="LLM Provider")
    parser.add_argument("--model", type=str, help="Model name (e.g. gpt-4o, llama3)")
    args = parser.parse_args()
    
    llm = get_llm(provider=args.provider, model_name=args.model)
    print(f"Successfully initialized LLM instance: {type(llm).__name__} ({llm.model})")

if __name__ == "__main__":
    main()
