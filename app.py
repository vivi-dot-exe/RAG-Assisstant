import os
import base64
import shutil
import sys
import streamlit as st

from pdf_processor import process_and_chunk_pdfs
from hybrid_indexer import HybridIndexer
from hybrid_retriever import HybridRetriever
from query_reranker import rewrite_query, CandidateReranker
from rag_generation import RAGGenerator

# -----------------------------------------------------------------------------
# Page Configuration & Clean Pastel Design System
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Cortex RAG Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* GLOBAL SOFT PASTEL BACKGROUND */
    .stApp {
        background: linear-gradient(135deg, #f8f4f9 0%, #ede4f5 50%, #f4ebf6 100%) !important;
        color: #2e1065 !important;
        font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    }

    /* HIDE TOP BLACK HEADER & FOOTER */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    footer {
        visibility: hidden;
    }

    /* REMOVE ALL AVATARS & EMOJIS */
    [data-testid="stChatMessageAvatar"], .stChatMessageAvatar, div[data-testid="stChatMessageAvatarIcon"], img[data-testid="stChatMessageAvatar"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* SIDEBAR STYLING & HIGH CONTRAST TYPOGRAPHY */
    section[data-testid="stSidebar"] {
        background: #faf6fc !important;
        border-right: 1px solid #ebdcf0 !important;
    }
    section[data-testid="stSidebar"] *, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] p {
        color: #4c1d95 !important;
        font-weight: 600 !important;
    }

    /* SELECTBOXES & DROPDOWNS */
    div[data-baseweb="select"], div[data-baseweb="select"] > div, div[class*="stSelectbox"] > div > div {
        background-color: #ffffff !important;
        color: #3b0764 !important;
        border: 1px solid #d8b4fe !important;
        border-radius: 10px !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"], li[role="option"] {
        background-color: #ffffff !important;
        color: #3b0764 !important;
    }

    /* TEXT INPUTS & PASSWORD FIELDS */
    div[data-baseweb="input"], div[data-baseweb="base-input"], input {
        background-color: #ffffff !important;
        color: #3b0764 !important;
        border-color: #d8b4fe !important;
        border-radius: 10px !important;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="base-input"] > div {
        background-color: #ffffff !important;
    }
    div[data-baseweb="input"] button, div[data-baseweb="input"] svg {
        color: #7e22ce !important;
        fill: #7e22ce !important;
        background-color: transparent !important;
    }

    /* FILE UPLOADER & FILE CHIPS */
    div[data-testid="stFileUploader"] section {
        background-color: #f5eefb !important;
        border: 1.5px dashed #c084fc !important;
        border-radius: 14px !important;
    }
    div[data-testid="stFileUploader"] section * {
        color: #581c87 !important;
    }
    div[data-testid="stFileUploaderDeleteBtn"], div[data-testid="stFileUploaderFileData"], div[data-testid="stFileUploader"] div[role="button"] {
        background-color: #ffffff !important;
        color: #581c87 !important;
        border: 1px solid #e9d5ff !important;
        border-radius: 8px !important;
    }

    /* FLOATING CHAT INPUT BAR */
    div[data-testid="stChatInput"] {
        background-color: #ffffff !important;
        border: 1.5px solid #d8b4fe !important;
        border-radius: 28px !important;
        box-shadow: 0 10px 32px rgba(147, 51, 234, 0.08) !important;
        padding: 4px 10px !important;
    }
    div[data-testid="stChatInput"] textarea {
        background-color: #ffffff !important;
        color: #3b0764 !important;
        font-size: 0.95rem !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder {
        color: #a855f7 !important;
    }
    div[data-testid="stChatInput"] button {
        background: linear-gradient(135deg, #9333ea 0%, #7c3aed 100%) !important;
        border-radius: 50% !important;
        border: none !important;
    }
    div[data-testid="stChatInput"] button svg {
        fill: #ffffff !important;
        color: #ffffff !important;
    }

    /* CHAT MESSAGE CARDS */
    div[data-testid="stChatMessage"] {
        background-color: #ffffff !important;
        border: 1px solid #e9d7ef !important;
        border-radius: 18px !important;
        padding: 20px 24px !important;
        box-shadow: 0 4px 24px rgba(124, 58, 237, 0.04) !important;
        margin-bottom: 16px !important;
    }
    div[data-testid="stChatMessage"] * {
        color: #2e1065 !important;
    }

    /* PRIMARY BUTTONS */
    .stButton > button {
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 8px 18px !important;
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.25) !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%) !important;
    }

    /* GLOWING 3D PASTEL PURPLE ORB HERO */
    .hero-container {
        text-align: center;
        padding: 10px 0 20px 0;
    }
    .purple-orb {
        width: 76px;
        height: 76px;
        background: radial-gradient(circle at 30% 30%, #f3e8ff 0%, #d8b4fe 40%, #c084fc 70%, #9333ea 100%);
        border-radius: 50%;
        margin: 0 auto 12px auto;
        box-shadow: 0 12px 36px rgba(192, 132, 252, 0.45), inset 0 2px 10px rgba(255, 255, 255, 0.9);
        animation: floatOrb 4s ease-in-out infinite alternate;
    }
    @keyframes floatOrb {
        0% { transform: translateY(0px); }
        100% { transform: translateY(-8px); }
    }
    
    .hero-title {
        color: #2e1065;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
</style>
""", unsafe_allow_html=True)

SOURCE_DIR = "./source_documents"
DB_DIR = "./chroma_db"

os.makedirs(SOURCE_DIR, exist_ok=True)

@st.cache_resource(show_spinner=False)
def load_reranker():
    return CandidateReranker()

def process_and_index_documents():
    """Processes PDFs with pdfplumber and updates ChromaDB & BM25Okapi."""
    with st.spinner("Processing & indexing PDF documents..."):
        chunks = process_and_chunk_pdfs(SOURCE_DIR, chunk_size=1000, chunk_overlap=150)
        if not chunks:
            st.sidebar.error("No valid PDF content extracted.")
            return 0, 0
            
        try:
            indexer = HybridIndexer(db_dir=DB_DIR)
            doc_count, corpus_count = indexer.index_documents(chunks)
            return doc_count, corpus_count
        except Exception as e:
            st.sidebar.warning(f"Embedding notice: {e}. Defaulting to local embeddings.")
            from langchain_huggingface import HuggingFaceEmbeddings
            indexer = HybridIndexer(db_dir=DB_DIR)
            indexer.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            doc_count, corpus_count = indexer.index_documents(chunks)
            return doc_count, corpus_count

# -----------------------------------------------------------------------------
# Sidebar: Streamlined Document Center & Settings
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Document Center", unsafe_allow_html=True)
    st.markdown("Upload PDF files to build your knowledge base.")
    
    uploaded_files = st.file_uploader(
        "Upload PDF Files",
        type=["pdf"],
        accept_multiple_files=True,
        help="Select PDF files to index"
    )
    
    if st.button("Process and Index PDFs", use_container_width=True):
        if uploaded_files:
            for file in uploaded_files:
                file_path = os.path.join(SOURCE_DIR, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
            
            pages_count, chunks_count = process_and_index_documents()
            if chunks_count > 0:
                st.success(f"Indexed {pages_count} chunks into ChromaDB.")
        else:
            st.warning("Please upload at least one PDF file first.")

    st.markdown("---")
    st.markdown("### Indexed Knowledge Base")
    
    existing_pdfs = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".pdf")] if os.path.exists(SOURCE_DIR) else []
    if existing_pdfs:
        st.info(f"**Indexed Documents ({len(existing_pdfs)}):**\n" + "\n".join([f"• {f}" for f in existing_pdfs]))
    else:
        st.write("No PDF documents uploaded yet.")

    st.markdown("---")
    with st.expander("Model Configuration"):
        llm_provider = st.selectbox("Provider", ["OpenAI (GPT-4o)", "Ollama (Local Llama3)"])
        provider_str = "ollama" if "Ollama" in llm_provider else "openai"
        model_str = "llama3" if "Ollama" in llm_provider else "gpt-4o"
        os.environ["LLM_PROVIDER"] = provider_str
        os.environ["LLM_MODEL"] = model_str
        
        if provider_str == "openai":
            api_key_input = st.text_input("API Key", type="password")
            if api_key_input:
                os.environ["OPENAI_API_KEY"] = api_key_input
        else:
            ollama_url = st.text_input("Ollama URL", value="http://localhost:11434")
            os.environ["OLLAMA_BASE_URL"] = ollama_url

# -----------------------------------------------------------------------------
# Main Stage: Clean Chat Interface
# -----------------------------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <div class="purple-orb"></div>
    <div class="hero-title">How can I assist you today?</div>
</div>
""", unsafe_allow_html=True)

# Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "Hello. I am your document intelligence assistant. Upload your PDF files in the sidebar and ask any question about their contents.",
            "citations": []
        }
    ]

for msg_idx, msg in enumerate(st.session_state["messages"]):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        if msg.get("citations"):
            st.markdown("<p style='color:#6b21a8; font-size:0.85rem; font-weight:600; margin: 10px 0 4px 0;'>Source Citations:</p>", unsafe_allow_html=True)
            c_cols = st.columns(min(len(msg["citations"]), 4))
            for c_idx, cite in enumerate(msg["citations"]):
                fname = cite.get("file_name", "document.pdf")
                p_num = cite.get("page_number", 1)
                btn_label = f"{fname} | Page {p_num}"
                with c_cols[c_idx % 4]:
                    st.button(btn_label, key=f"btn_{msg_idx}_{c_idx}")

user_query = st.chat_input("Ask any question about your documents...")

if user_query:
    st.session_state["messages"].append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        chunks = process_and_chunk_pdfs(SOURCE_DIR, chunk_size=1000, chunk_overlap=150)
        if not chunks:
            response_text = "Please upload and process PDF documents using the sidebar first."
            st.markdown(response_text)
            st.session_state["messages"].append({"role": "assistant", "content": response_text, "citations": []})
        else:
            with st.spinner("Searching document context..."):
                indexer = HybridIndexer(db_dir=DB_DIR)
                indexer.index_documents(chunks)
                
                opt_query = rewrite_query(user_query)
                retriever = HybridRetriever(indexer=indexer)
                candidate_15 = retriever.retrieve(opt_query, dense_k=20, sparse_k=20, final_k=15)

            if not candidate_15:
                response_text = "No relevant context found in your documents."
                st.markdown(response_text)
                st.session_state["messages"].append({"role": "assistant", "content": response_text, "citations": []})
            else:
                with st.spinner("Reranking relevant chunks..."):
                    reranker = load_reranker()
                    definitive_top_4 = reranker.rerank(opt_query, candidate_15, top_n=4)

                generator = RAGGenerator(model_name=os.environ.get("LLM_MODEL", "gpt-4o"))
                stream, structured_citations = generator.generate(user_query, definitive_top_4)
                
                full_response = st.write_stream(stream)

                st.markdown("<p style='color:#6b21a8; font-size:0.85rem; font-weight:600; margin: 10px 0 4px 0;'>Source Citations:</p>", unsafe_allow_html=True)
                c_cols = st.columns(min(len(structured_citations), 4))
                for c_idx, cite in enumerate(structured_citations):
                    fname = cite["file_name"]
                    p_num = cite["page_number"]
                    btn_label = f"{fname} | Page {p_num}"
                    with c_cols[c_idx % 4]:
                        st.button(btn_label, key=f"btn_new_{c_idx}")
                        
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": full_response,
                    "citations": structured_citations
                })
