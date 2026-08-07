'use client'

import { useState, useEffect, useRef, ChangeEvent } from 'react'
import { Button } from '@/components/ui/button'
import {
  ArrowUp,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  FileText,
  LayoutGrid,
  Menu,
  Paperclip,
  Plus,
  Search,
  Sparkles,
  UserRound,
  Trash2,
  Settings,
  Sliders,
  X,
  CheckCircle2,
  MessageSquare,
  HardDrive,
  FolderUp,
} from 'lucide-react'

type MessageAttachment = {
  name: string
  size: string
}

type Message = {
  id: number | string
  role: 'user' | 'assistant'
  content: string
  attachments?: MessageAttachment[]
  sources?: string[]
}

type ChatHistorySession = {
  id: string
  title: string
  timestamp: string
  messages: Message[]
}

type AttachedFile = {
  file: File
  name: string
  size: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000'


const INITIAL_HISTORY: ChatHistorySession[] = [
  {
    id: 'h1',
    title: 'Summarize ipsem5notes.pdf',
    timestamp: 'Just now',
    messages: [
      {
        id: 1,
        role: 'assistant',
        content: 'Hello! I am Cortex, your document intelligence assistant. Upload your PDF files or ask questions directly.',
        sources: []
      }
    ]
  },
  {
    id: 'h2',
    title: 'Module 2.pdf Network Analysis',
    timestamp: '1 hour ago',
    messages: [
      { id: 101, role: 'user', content: 'What is classful addressing in Module 2?' },
      {
        id: 102,
        role: 'assistant',
        content: 'Classful addressing divides 32-bit IPv4 addresses into sub-classes: Class A, Class B, and Class C.',
        sources: ['Module 2.pdf | Page 136']
      }
    ]
  },
  {
    id: 'h3',
    title: 'AI Concepts and Applications',
    timestamp: 'Yesterday',
    messages: [
      { id: 201, role: 'user', content: 'Summarize AI Agents vs Assistants' },
      { id: 202, role: 'assistant', content: 'AI Agents act autonomously to perform multi-step workflows, while AI Assistants interact responsively to direct human prompts.', sources: ['AI Agents and AI Assistants.pdf | Page 1'] }
    ]
  }
]

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function Page() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [historyList, setHistoryList] = useState<ChatHistorySession[]>(INITIAL_HISTORY)
  const [activeSessionId, setActiveSessionId] = useState<string>('h1')
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState<Message[]>(INITIAL_HISTORY[0].messages)
  const [isRetrieving, setIsRetrieving] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [indexedDocCount, setIndexedDocCount] = useState<number>(0)

  // Gemini Style File Attachment & Upload Menu State
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
  const [showUploadMenu, setShowUploadMenu] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploadMenuRef = useRef<HTMLDivElement>(null)

  // Toast Notification State (Only for errors or explicit settings save)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  // Model & Settings State
  const [showSettingsModal, setShowSettingsModal] = useState(false)
  const [provider, setProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434')

  // Fetch document count from FastAPI Backend
  const fetchDocCount = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/documents`)
      if (res.ok) {
        const data = await res.json()
        setIndexedDocCount((data.documents || []).length)
      }
    } catch (error) {
      console.error('Failed to fetch documents count from backend:', error)
    }
  }

  useEffect(() => {
    fetchDocCount()
  }, [])

  // Close upload popup menu when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (uploadMenuRef.current && !uploadMenuRef.current.contains(e.target as Node)) {
        setShowUploadMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Start New Chat Session
  const handleNewChat = () => {
    const newSessionId = `chat_${Date.now()}`
    const newSession: ChatHistorySession = {
      id: newSessionId,
      title: 'New conversation',
      timestamp: 'Just now',
      messages: [
        {
          id: 1,
          role: 'assistant',
          content: 'Hello! I am Cortex, your document intelligence assistant. Upload PDF files or ask any questions directly.',
          sources: []
        }
      ]
    }
    setHistoryList((prev) => [newSession, ...prev])
    setActiveSessionId(newSessionId)
    setMessages(newSession.messages)
    setPrompt('')
    setAttachedFiles([])
  }

  // Select Conversation from History
  const handleSelectSession = (session: ChatHistorySession) => {
    setActiveSessionId(session.id)
    setMessages(session.messages)
    setPrompt('')
    setAttachedFiles([])
  }

  // Delete History Item
  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setHistoryList((prev) => prev.filter((s) => s.id !== sessionId))
    if (activeSessionId === sessionId) {
      handleNewChat()
    }
  }

  // Handle File Selection (Gemini attachment style)
  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const newAttachments: AttachedFile[] = []
    for (let i = 0; i < files.length; i++) {
      const f = files[i]
      if (f.name.toLowerCase().endsWith('.pdf')) {
        newAttachments.push({
          file: f,
          name: f.name,
          size: formatFileSize(f.size)
        })
      }
    }

    if (newAttachments.length === 0) {
      showToast('Please select valid PDF files.', 'error')
      return
    }

    setAttachedFiles((prev) => [...prev, ...newAttachments])
    setShowUploadMenu(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // Remove attached file card before sending
  const handleRemoveAttachment = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, idx) => idx !== index))
  }

  // Save Settings Config
  const handleSaveSettings = async () => {
    try {
      await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          apiKey,
          model: provider === 'openai' ? 'gpt-4o' : 'llama3',
          ollamaUrl
        })
      })
      setShowSettingsModal(false)
      showToast('Settings saved successfully!', 'success')
    } catch (error) {
      console.error('Failed to save settings:', error)
      showToast('Failed to save settings.', 'error')
    }
  }

  // Open PDF file in new browser tab
  const handleOpenDocument = (sourceStr: string) => {
    const parts = sourceStr.split('|')
    const fileName = parts[0].trim()
    let pageNum = ''
    if (parts.length > 1) {
      const pageMatch = parts[1].match(/\d+/)
      if (pageMatch) pageNum = `#page=${pageMatch[0]}`
    }
    const fileUrl = `${API_BASE}/api/documents/${encodeURIComponent(fileName)}/file${pageNum}`
    window.open(fileUrl, '_blank')
  }

  // Submit Prompt & Upload Attached Files

  async function submitPrompt() {
    const trimmed = prompt.trim()
    if ((!trimmed && attachedFiles.length === 0) || isRetrieving) return

    setIsRetrieving(true)

    const attachedFileNames = attachedFiles.map((f) => f.name)

    // 1. Upload attached files if any (silent indexing, no toast alert)
    if (attachedFiles.length > 0) {
      setIsUploading(true)
      const formData = new FormData()
      attachedFiles.forEach((item) => formData.append('files', item.file))

      try {
        const uploadRes = await fetch(`${API_BASE}/api/upload`, {
          method: 'POST',
          body: formData
        })
        if (uploadRes.ok) {
          await fetchDocCount()
        }
      } catch (err) {
        console.error('Error uploading attached files:', err)
      } finally {
        setIsUploading(false)
      }
    }

    const userQueryText = trimmed || (attachedFileNames.length > 0 ? `Summarize ${attachedFileNames.join(', ')}` : '')
    
    // Build user message including attached file badges
    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: userQueryText,
      attachments: attachedFiles.map((f) => ({ name: f.name, size: f.size }))
    }

    // Update active conversation & history
    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setPrompt('')
    setAttachedFiles([])

    // Update history session title if it's new
    setHistoryList((prev) =>
      prev.map((session) => {
        if (session.id === activeSessionId) {
          const newTitle = session.title === 'New conversation' ? userQueryText.slice(0, 32) : session.title
          return { ...session, title: newTitle, messages: updatedMessages }
        }
        return session
      })
    )

    // 2. Query FastAPI Backend with attached_files restriction
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userQueryText,
          provider: provider,
          model: provider === 'openai' ? 'gpt-4o' : 'llama3',
          top_n: 4,
          attached_files: attachedFileNames.length > 0 ? attachedFileNames : undefined
        })
      })

      if (res.ok) {
        const data = await res.json()
        const sources = (data.citations || []).map(
          (cite: any) => `${cite.file_name} | Page ${cite.page_number}`
        )

        const botMessage: Message = {
          id: Date.now() + 1,
          role: 'assistant',
          content: data.content,
          sources: sources
        }

        setMessages((current) => [...current, botMessage])
        setHistoryList((prev) =>
          prev.map((session) =>
            session.id === activeSessionId
              ? { ...session, messages: [...session.messages, botMessage] }
              : session
          )
        )
      } else {
        const err = await res.json()
        const errorMessage: Message = {
          id: Date.now() + 1,
          role: 'assistant',
          content: `Error: ${err.detail || 'Failed to process RAG response.'}`
        }
        setMessages((current) => [...current, errorMessage])
      }
    } catch (error) {
      console.error('Chat API Error:', error)
      const errorConnMessage: Message = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Error connecting to FastAPI backend. Ensure app.py is running on http://127.0.0.1:8000.'
      }
      setMessages((current) => [...current, errorConnMessage])
    } finally {
      setIsRetrieving(false)
    }
  }

  return (
    <main className="app-shell h-screen overflow-hidden bg-background text-foreground relative">
      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 flex items-center space-x-2.5 px-4 py-3 rounded-2xl shadow-xl border backdrop-blur-md transition-all text-xs font-semibold animate-in fade-in slide-in-from-top-2 ${
            toast.type === 'success'
              ? 'bg-purple-950/90 text-purple-100 border-purple-400/40'
              : 'bg-rose-950/90 text-rose-100 border-rose-500/40'
          }`}
        >
          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          <span>{toast.message}</span>
          <button onClick={() => setToast(null)} className="ml-2 text-purple-300 hover:text-white transition-colors">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept=".pdf"
        multiple
        className="hidden"
      />

      <div className="ambient ambient-one" aria-hidden="true" />
      <div className="ambient ambient-two" aria-hidden="true" />
      <div className="workspace relative z-10 flex h-screen overflow-hidden">
        
        {/* GEMINI STYLE COLLAPSIBLE SIDEBAR */}
        <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : 'sidebar-collapsed'}`}>
          <div className="sidebar-top flex items-center justify-between">
            <div className="brand-mark flex items-center gap-3" aria-label="Cortex home">
              <span className="brand-icon"><Sparkles /></span>
              {sidebarOpen && <span className="brand-name">Cortex</span>}
            </div>
            <Button
              variant="ghost"
              size="icon-sm"
              className="sidebar-toggle"
              onClick={() => setSidebarOpen((open) => !open)}
              aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              {sidebarOpen ? <ChevronLeft /> : <ChevronRight />}
            </Button>
          </div>

          {/* New Chat Button */}
          <Button
            onClick={handleNewChat}
            variant="ghost"
            className={`nav-item mb-2 border border-purple-200/20 bg-white/5 hover:bg-white/10 ${
              sidebarOpen ? 'justify-start px-3 py-2.5 rounded-xl' : 'justify-center'
            }`}
          >
            <Plus className="h-4 w-4 text-purple-400 shrink-0" />
            {sidebarOpen && <span className="font-semibold text-xs text-foreground">New chat</span>}
          </Button>

          {/* Workspace Navigation Links */}
          <nav className="sidebar-nav flex flex-col gap-1" aria-label="Workspace navigation">
            <Button variant="ghost" className={`nav-item ${sidebarOpen ? 'justify-start' : 'justify-center'}`} aria-label="Search chats">
              <Search data-icon="inline-start" />
              {sidebarOpen && 'Search chats'}
            </Button>
            <Button variant="ghost" className={`nav-item ${sidebarOpen ? 'justify-start' : 'justify-center'}`} aria-label="Library">
              <BookOpen data-icon="inline-start" />
              {sidebarOpen && 'Library'}
            </Button>
          </nav>

          <div className="sidebar-divider" />

          {/* Recents Chat History List */}
          <div className="documents-header flex items-center justify-between">
            {sidebarOpen && <span className="eyebrow">Recents</span>}
          </div>

          {sidebarOpen && (
            <div className="documents-list flex flex-col gap-1 overflow-y-auto flex-1 pr-1" aria-label="Recent chats">
              {historyList.map((session) => (
                <div
                  key={session.id}
                  className={`document-row flex items-center gap-2.5 text-left cursor-pointer group ${
                    activeSessionId === session.id ? 'document-selected' : ''
                  }`}
                  onClick={() => handleSelectSession(session)}
                >
                  <MessageSquare className="h-3.5 w-3.5 text-purple-400 shrink-0" />
                  <span className="min-w-0 flex-1">
                    <span className="document-name block truncate text-xs font-medium">{session.title}</span>
                  </span>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="h-5 w-5 opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity"
                    onClick={(e) => handleDeleteSession(session.id, e)}
                    title="Delete chat"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* Sidebar Bottom Profile & Settings */}
          <div className="sidebar-footer mt-auto pt-3 border-t border-white/10 flex items-center justify-between">
            <div className={`profile-card border-none mt-0 pt-0 flex items-center gap-2.5 ${!sidebarOpen ? 'justify-center' : ''}`}>
              <span className="avatar"><UserRound /></span>
              {sidebarOpen && (
                <span className="min-w-0 flex-1">
                  <span className="profile-name block truncate text-xs font-semibold">Vaibhavi Tiwari</span>
                  <span className="profile-plan block text-[10px] text-purple-400">Pro User</span>
                </span>
              )}
            </div>
            {sidebarOpen && (
              <Button
                variant="ghost"
                size="icon-sm"
                className="subtle-icon"
                onClick={() => setShowSettingsModal(true)}
                title="Model Settings"
              >
                <Settings className="h-4 w-4" />
              </Button>
            )}
          </div>
        </aside>

        {/* MAIN STAGE */}
        <section className="chat-area flex min-w-0 flex-1 flex-col h-screen overflow-hidden">
          {/* Header */}
          <header className="chat-header flex items-center justify-between flex-shrink-0">
            <div className="mobile-brand flex items-center gap-3">
              <Button variant="ghost" size="icon-sm" className="mobile-menu" onClick={() => setSidebarOpen((open) => !open)} aria-label="Toggle sidebar"><Menu /></Button>
              <span className="header-title">Cortex Assistant</span>
            </div>
            <div className="header-actions flex items-center gap-2">
              <span className="status-pill"><span className="status-dot" /> {indexedDocCount} PDF sources indexed</span>
              <Button
                variant="ghost"
                size="icon-sm"
                className="subtle-icon"
                onClick={() => setShowSettingsModal(true)}
                title="Model Settings"
              >
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </header>

          {/* Chat Messages Timeline */}
          <div className="conversation-wrap flex-1 min-h-0 overflow-y-auto px-6 py-6 w-full">
            <div className="conversation-head text-center my-4">
              <div className="conversation-icon mx-auto flex items-center justify-center"><Sparkles /></div>
              <p className="conversation-kicker">Cortex / Document Workspace</p>
              <h1 className="conversation-title text-balance">Ask anything about your documents.</h1>
              <p className="conversation-description text-pretty">Answers are powered by Hybrid RRF Search & Cross-Encoder Reranking with structured page citations.</p>
            </div>

            <div className="message-list flex flex-1 flex-col gap-6 w-full" aria-live="polite">
              {messages.map((message) => (
                <article key={message.id} className={`message-row flex ${message.role === 'user' ? 'message-user justify-end' : 'message-assistant'}`}>
                  {message.role === 'assistant' && <span className="assistant-avatar"><Sparkles /></span>}
                  <div className={`message-content ${message.role === 'user' ? 'user-bubble' : 'assistant-bubble'}`}>


                    {/* Render Attached Document Cards inside User Chat Bubble */}
                    {message.attachments && message.attachments.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-2">
                        {message.attachments.map((att, aIdx) => (
                          <button
                            key={aIdx}
                            type="button"
                            onClick={() => handleOpenDocument(att.name)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/15 hover:bg-white/25 text-purple-100 border border-white/20 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
                            title="Click to view PDF"
                          >
                            <FileText className="h-3.5 w-3.5 text-purple-300" />
                            <span>{att.name}</span>
                          </button>
                        ))}
                      </div>
                    )}

                    <p className="whitespace-pre-wrap">{message.content}</p>

                    {message.sources && message.sources.length > 0 && (
                      <div className="source-list flex flex-wrap gap-2 mt-3 pt-2 border-t border-purple-200/20" aria-label="Response sources">
                        {message.sources.map((source, sIdx) => (
                          <button
                            key={`${message.id}-${sIdx}`}
                            type="button"
                            onClick={() => handleOpenDocument(source)}
                            className="source-chip inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/15 border border-white/10 text-purple-200 transition-colors cursor-pointer"
                            title="Click to open PDF"
                          >
                            <FileText className="h-3 w-3 text-purple-400" /> {source}
                          </button>
                        ))}
                      </div>
                    )}

                  </div>
                </article>
              ))}

              {isRetrieving && (
                <div className="message-row message-assistant flex items-center gap-2">
                  <span className="assistant-avatar"><Sparkles /></span>
                  <div className="retrieving-state text-xs text-purple-400 font-medium animate-pulse">
                    {isUploading ? 'Indexing attached PDF file(s)...' : 'Searching document context & reranking...'}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* FLOATING COMPOSER */}
          <div className="composer-zone flex-shrink-0 w-full relative">
            
            {/* Upload Menu Popup */}
            {showUploadMenu && (
              <div
                ref={uploadMenuRef}
                className="absolute bottom-20 left-6 z-50 w-56 rounded-2xl bg-zinc-900/95 border border-zinc-800 p-2 shadow-2xl backdrop-blur-xl text-xs space-y-1 animate-in fade-in slide-in-from-bottom-2"
              >
                <button
                  onClick={() => {
                    setShowUploadMenu(false)
                    fileInputRef.current?.click()
                  }}
                  className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl hover:bg-zinc-800 text-left text-zinc-100 transition-colors font-medium"
                >
                  <Paperclip className="h-4 w-4 text-purple-400" />
                  <span>Upload files</span>
                </button>

                <button
                  onClick={() => {
                    setShowUploadMenu(false)
                    showToast('Drive integration ready for connected accounts.', 'success')
                  }}
                  className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl hover:bg-zinc-800 text-left text-zinc-100 transition-colors font-medium"
                >
                  <HardDrive className="h-4 w-4 text-indigo-400" />
                  <span>Add from Drive</span>
                </button>

                <button
                  onClick={() => {
                    setShowUploadMenu(false)
                    fileInputRef.current?.click()
                  }}
                  className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl hover:bg-zinc-800 text-left text-zinc-100 transition-colors font-medium border-t border-zinc-800/80 mt-1 pt-2"
                >
                  <FolderUp className="h-4 w-4 text-fuchsia-400" />
                  <span>More uploads</span>
                </button>
              </div>
            )}

            <form
              onSubmit={(event) => {
                event.preventDefault()
                submitPrompt()
              }}
              className="composer flex flex-col gap-2 relative bg-zinc-900/90 border border-zinc-800 rounded-3xl p-3 shadow-2xl backdrop-blur-xl"
            >
              {/* Attached File Cards Preview inside Composer */}
              {attachedFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 px-2 pt-1 pb-2 border-b border-zinc-800/80">
                  {attachedFiles.map((item, idx) => (
                    <div
                      key={idx}
                      className="flex items-center space-x-3 bg-zinc-800/90 border border-zinc-700/80 rounded-xl px-3 py-2 text-xs shadow-sm group relative"
                    >
                      <div className="h-7 w-7 rounded-lg bg-rose-500/20 text-rose-400 font-bold text-[10px] flex items-center justify-center border border-rose-500/30">
                        PDF
                      </div>
                      <div className="min-w-0 pr-1">
                        <p className="font-semibold text-zinc-100 text-xs truncate max-w-[140px]">{item.name}</p>
                        <p className="text-[10px] text-zinc-400">{item.size}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveAttachment(idx)}
                        className="p-1 text-zinc-400 hover:text-rose-400 rounded-md hover:bg-zinc-700/60 transition-colors"
                        title="Remove file"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Input Row */}
              <div className="composer-top flex items-center gap-3 px-1">
                <button
                  type="button"
                  onClick={() => setShowUploadMenu((prev) => !prev)}
                  className="p-2 rounded-full text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors shrink-0"
                  title="Attach files"
                >
                  <Plus className="h-5 w-5" />
                </button>

                <input
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  placeholder="Ask Cortex a question about your documents..."
                  aria-label="Ask a question"
                  className="flex-1 bg-transparent text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none"
                />

                <Button
                  type="submit"
                  size="icon"
                  className="send-button shrink-0 h-9 w-9 rounded-full bg-purple-600 hover:bg-purple-500 text-white shadow-md"
                  aria-label="Send question"
                  disabled={(!prompt.trim() && attachedFiles.length === 0) || isRetrieving}
                >
                  <ArrowUp className="h-4 w-4" />
                </Button>
              </div>

              {/* Disclaimer */}
              <div className="composer-bottom flex items-center justify-between border-t border-zinc-800/40 pt-2 px-2">
                <span className="composer-hint text-[11px] text-zinc-400">
                  Cortex is AI and can make mistakes. Check important information.
                </span>
                <span className="composer-shortcut text-[10px] text-zinc-500">⌘ ↵</span>
              </div>
            </form>
          </div>
        </section>
      </div>

      {/* Model & API Settings Modal */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md bg-zinc-900 rounded-3xl border border-zinc-800 p-6 shadow-2xl space-y-5 text-zinc-100">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center space-x-2">
                <Sliders className="h-5 w-5 text-purple-400" />
                <h3 className="font-bold text-base">Model Settings</h3>
              </div>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setShowSettingsModal(false)}
              >
                <X className="h-5 w-5 text-zinc-400" />
              </Button>
            </div>

            <div className="space-y-4 text-sm">
              <div>
                <label className="block font-semibold mb-1.5 text-xs text-zinc-300">LLM Provider</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-purple-400 text-zinc-100"
                >
                  <option value="openai">OpenAI (GPT-4o)</option>
                  <option value="ollama">Ollama (Local Llama3)</option>
                </select>
              </div>

              {provider === 'openai' ? (
                <div>
                  <label className="block font-semibold mb-1.5 text-xs text-zinc-300">OpenAI API Key</label>
                  <input
                    type="password"
                    placeholder="sk-..."
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-purple-400 text-zinc-100"
                  />
                  <p className="text-[11px] text-zinc-400 mt-1">Leave empty if OPENAI_API_KEY is already set in your environment.</p>
                </div>
              ) : (
                <div>
                  <label className="block font-semibold mb-1.5 text-xs text-zinc-300">Ollama Base URL</label>
                  <input
                    type="text"
                    value={ollamaUrl}
                    onChange={(e) => setOllamaUrl(e.target.value)}
                    className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-purple-400 text-zinc-100"
                  />
                </div>
              )}
            </div>

            <Button
              onClick={handleSaveSettings}
              className="w-full py-2 bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs rounded-xl shadow-md"
            >
              Save Settings
            </Button>
          </div>
        </div>
      )}
    </main>
  )
}
