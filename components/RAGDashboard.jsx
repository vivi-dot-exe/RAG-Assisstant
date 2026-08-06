import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  UploadCloud,
  FileText,
  Paperclip,
  Send,
  X,
  Settings,
  ShieldCheck,
  Trash2,
  Sliders
} from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000';

export default function RAGDashboard() {
  // Model & Settings Modal State
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [provider, setProvider] = useState('openai');
  const [apiKey, setApiKey] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');

  // Documents State
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  // Chat State
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 'm1',
      role: 'assistant',
      content: 'Hello. I am Cortex, your document intelligence assistant. Upload your PDF files in the sidebar and ask any questions about their content.',
      citations: []
    }
  ]);
  const [isProcessing, setIsProcessing] = useState(false);

  const hasConversation = messages.length > 1;

  // Fetch documents from FastAPI
  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || []);
      }
    } catch (error) {
      console.error('Error fetching documents from backend:', error);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  // Handle Remove Document
  const handleRemoveDoc = async (filename) => {
    try {
      const res = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        await fetchDocuments();
      }
    } catch (error) {
      console.error('Error deleting document:', error);
    }
  };

  // Handle File Upload
  const handleFileUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        await fetchDocuments();
        alert(data.message || 'Indexed successfully!');
      } else {
        const err = await res.json();
        alert(err.detail || 'Upload failed');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Failed to connect to FastAPI backend at http://localhost:8000.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Save Config
  const handleSaveSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          apiKey,
          model: provider === 'openai' ? 'gpt-4o' : 'llama3',
          ollamaUrl
        })
      });
      if (res.ok) {
        setShowSettingsModal(false);
      }
    } catch (error) {
      console.error('Error saving settings:', error);
    }
  };

  // Handle Send Question
  const handleSendMessage = async (e) => {
    e?.preventDefault();
    if (!query.trim() || isProcessing) return;

    const userMsg = { id: `u_${Date.now()}`, role: 'user', content: query };
    setMessages((prev) => [...prev, userMsg]);
    const currentQuery = query;
    setQuery('');
    setIsProcessing(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: currentQuery,
          provider: provider,
          model: provider === 'openai' ? 'gpt-4o' : 'llama3',
          top_n: 4
        })
      });

      if (res.ok) {
        const data = await res.json();
        const botMsg = {
          id: `b_${Date.now()}`,
          role: 'assistant',
          content: data.content,
          citations: data.citations || []
        };
        setMessages((prev) => [...prev, botMsg]);
      } else {
        const err = await res.json();
        setMessages((prev) => [
          ...prev,
          {
            id: `b_${Date.now()}`,
            role: 'assistant',
            content: `Error: ${err.detail || 'Failed to process RAG query.'}`,
            citations: []
          }
        ]);
      }
    } catch (error) {
      console.error('Error querying backend:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: `b_${Date.now()}`,
          role: 'assistant',
          content: 'Error connecting to FastAPI backend. Please check app.py.',
          citations: []
        }
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-gradient-to-br from-purple-50 via-fuchsia-50/40 to-indigo-50/50 text-purple-950 font-sans">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept=".pdf"
        multiple
        className="hidden"
      />

      {/* ========================================================================= */}
      {/* STREAMLINED SIDEBAR (Knowledge Base & Uploads Only)                       */}
      {/* ========================================================================= */}
      <aside className="w-72 border-r border-purple-100/80 bg-white/70 backdrop-blur-xl flex flex-col justify-between p-4 shadow-xs z-20">
        <div className="space-y-6">
          {/* Brand Header Logo */}
          <div className="flex items-center space-x-3 px-2 py-1">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-purple-500/20">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h1 className="font-bold text-lg leading-none text-purple-950">Cortex RAG</h1>
              <span className="text-[11px] text-purple-600 font-medium">Document Assistant</span>
            </div>
          </div>

          {/* Minimalist Upload Zone */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-purple-900 uppercase tracking-wider px-1">
              Add Documents
            </h3>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-purple-200/80 rounded-2xl p-4 text-center bg-purple-50/30 hover:bg-purple-50/70 transition-all cursor-pointer group"
            >
              <UploadCloud className="h-7 w-7 text-purple-500 group-hover:scale-110 transition-transform mx-auto mb-1.5" />
              <p className="text-xs font-semibold text-purple-900">
                {isUploading ? 'Indexing PDFs...' : 'Upload PDF Files'}
              </p>
              <p className="text-[10px] text-purple-500 mt-0.5">Click or drag and drop</p>
            </div>
          </div>

          {/* Indexed Knowledge Base List */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between px-1">
              <h3 className="text-xs font-bold text-purple-900 uppercase tracking-wider">
                Indexed Files ({documents.length})
              </h3>
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            </div>

            <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
              {documents.map((doc) => (
                <div
                  key={doc.name}
                  className="flex items-center justify-between p-3 rounded-xl border border-purple-100 bg-white/90 shadow-2xs hover:border-purple-200 transition-colors"
                >
                  <div className="flex items-center space-x-2.5 overflow-hidden">
                    <FileText className="h-4 w-4 text-purple-600 shrink-0" />
                    <div className="truncate text-xs">
                      <p className="font-semibold text-purple-950 truncate">{doc.name}</p>
                      <p className="text-[10px] text-purple-500">{doc.pages} pages • {doc.size}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemoveDoc(doc.name)}
                    className="p-1 rounded-lg text-purple-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                    title="Remove document"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}

              {documents.length === 0 && (
                <p className="text-xs text-purple-400 text-center py-4">No documents indexed yet.</p>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar Bottom: Settings Gear & Status */}
        <div className="pt-3 border-t border-purple-100 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-xs font-semibold text-purple-800">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            <span>FastAPI Connected</span>
          </div>

          <button
            onClick={() => setShowSettingsModal(true)}
            className="p-2 rounded-xl text-purple-600 hover:bg-purple-100/60 hover:text-purple-900 transition-colors"
            title="Settings"
          >
            <Settings className="h-4 w-4" />
          </button>
        </div>
      </aside>

      {/* ========================================================================= */}
      {/* CLEAN MAIN CHAT STAGE                                                     */}
      {/* ========================================================================= */}
      <main className="flex-1 flex flex-col relative overflow-hidden">
        {/* Professional Top Bar */}
        <header className="h-16 border-b border-purple-100/80 bg-white/40 backdrop-blur-md px-8 flex items-center justify-between z-10">
          <div className="flex items-center space-x-3">
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-purple-100/80 text-purple-900 text-xs font-semibold border border-purple-200/50">
              <span className="h-2 w-2 rounded-full bg-purple-600" />
              <span>Model: {provider === 'openai' ? 'GPT-4o' : 'Llama3'}</span>
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowSettingsModal(true)}
              className="p-2 rounded-xl border border-purple-200/80 bg-white/80 text-purple-700 hover:bg-purple-50 transition-colors shadow-2xs"
              title="Settings"
            >
              <Settings className="h-4 w-4" />
            </button>
          </div>
        </header>

        {/* Spacious Chat Timeline Area */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 max-w-3xl mx-auto w-full flex flex-col justify-between">
          {/* Dynamic Hero Section */}
          <div
            className={`transition-all duration-500 ease-in-out text-center ${
              hasConversation ? 'py-2 scale-90 opacity-80' : 'py-10 scale-100 opacity-100'
            }`}
          >
            <div className="relative mx-auto mb-4 h-20 w-20 rounded-full bg-radial from-purple-200 via-purple-400 to-indigo-600 shadow-xl shadow-purple-400/40 animate-pulse flex items-center justify-center">
              <div className="h-16 w-16 rounded-full bg-white/20 backdrop-blur-xs border border-white/60" />
            </div>
            <h2 className="text-2xl font-bold text-purple-950">How can I assist you today?</h2>
            <p className="text-xs text-purple-600 mt-1 font-medium">Ask questions about your uploaded documents</p>
          </div>

          {/* Chat Messages */}
          <div className="space-y-4 flex-1">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xl rounded-2xl p-5 shadow-xs border backdrop-blur-md transition-all ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white border-purple-500/30'
                      : 'bg-white/90 text-purple-950 border-purple-100/90'
                  }`}
                >
                  <div className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>

                  {/* Citation Badges */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-purple-100/80 flex flex-wrap gap-2">
                      {msg.citations.map((cite, cIdx) => (
                        <span
                          key={cIdx}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-xl bg-purple-100/80 border border-purple-200/80 text-[11px] font-semibold text-purple-800"
                        >
                          <FileText className="h-3 w-3 text-purple-600" />
                          <span>
                            {cite.file_name} | Page {cite.page_number}
                          </span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isProcessing && (
              <div className="flex justify-start">
                <div className="rounded-2xl p-4 bg-white/90 border border-purple-100 text-purple-600 text-xs font-semibold animate-pulse flex items-center space-x-2">
                  <Sparkles className="h-4 w-4 text-purple-600 animate-spin" />
                  <span>Thinking & searching document context...</span>
                </div>
              </div>
            )}
          </div>

          {/* ========================================================================= */}
          {/* FLOATING GLASSMORPHIC PROMPT BAR                                          */}
          {/* ========================================================================= */}
          <form
            onSubmit={handleSendMessage}
            className="sticky bottom-4 mx-auto w-full max-w-2xl bg-white/90 backdrop-blur-xl border border-purple-200/80 rounded-full p-2 pl-4 shadow-xl shadow-purple-500/10 flex items-center space-x-3 transition-all"
          >
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-2 rounded-full text-purple-500 hover:bg-purple-100/60 hover:text-purple-800 transition-colors"
              title="Attach document"
            >
              <Paperclip className="h-4 w-4" />
            </button>

            <input
              type="text"
              placeholder="Ask anything about your documents..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 bg-transparent text-sm text-purple-950 placeholder-purple-400 focus:outline-none"
            />

            <button
              type="submit"
              disabled={!query.trim() || isProcessing}
              className="p-2.5 rounded-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-500/20 hover:from-purple-700 hover:to-indigo-700 transition-all disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </main>

      {/* ========================================================================= */}
      {/* COMPACT SETTINGS MODAL                                                    */}
      {/* ========================================================================= */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-purple-950/20 backdrop-blur-xs p-4">
          <div className="w-full max-w-md bg-white rounded-3xl border border-purple-100 p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-purple-100 pb-3">
              <div className="flex items-center space-x-2">
                <Sliders className="h-5 w-5 text-purple-600" />
                <h3 className="font-bold text-base text-purple-950">Model Settings</h3>
              </div>
              <button
                onClick={() => setShowSettingsModal(false)}
                className="p-1 rounded-lg text-purple-400 hover:text-purple-800 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-purple-900 mb-1.5">LLM Provider</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full rounded-xl border border-purple-200 bg-white px-3 py-2.5 text-purple-950 font-medium focus:outline-none focus:ring-2 focus:ring-purple-400"
                >
                  <option value="openai">OpenAI (GPT-4o)</option>
                  <option value="ollama">Ollama (Local Llama3)</option>
                </select>
              </div>

              {provider === 'openai' ? (
                <div>
                  <label className="block font-semibold text-purple-900 mb-1.5">OpenAI API Key</label>
                  <input
                    type="password"
                    placeholder="sk-..."
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="w-full rounded-xl border border-purple-200 bg-white px-3 py-2.5 text-purple-950 focus:outline-none focus:ring-2 focus:ring-purple-400"
                  />
                </div>
              ) : (
                <div>
                  <label className="block font-semibold text-purple-900 mb-1.5">Ollama Base URL</label>
                  <input
                    type="text"
                    value={ollamaUrl}
                    onChange={(e) => setOllamaUrl(e.target.value)}
                    className="w-full rounded-xl border border-purple-200 bg-white px-3 py-2.5 text-purple-950 focus:outline-none focus:ring-2 focus:ring-purple-400"
                  />
                </div>
              )}
            </div>

            <button
              onClick={handleSaveSettings}
              className="w-full py-2.5 rounded-xl bg-purple-950 text-white font-semibold text-xs hover:bg-purple-900 transition-all shadow-md shadow-purple-950/10"
            >
              Save Settings
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
