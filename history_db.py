import sqlite3
import json
import os
import time
from typing import List, Dict, Any, Optional

DB_FILE = "./chat_history.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            attachments TEXT,
            sources TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

def get_all_sessions() -> List[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, title, created_at FROM sessions ORDER BY updated_at DESC")
    session_rows = cursor.fetchall()
    
    sessions = []
    for s_row in session_rows:
        s_id = s_row["id"]
        cursor.execute(
            "SELECT id, role, content, attachments, sources FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (s_id,)
        )
        msg_rows = cursor.fetchall()
        
        messages = []
        for m_row in msg_rows:
            attachments = json.loads(m_row["attachments"]) if m_row["attachments"] else []
            sources = json.loads(m_row["sources"]) if m_row["sources"] else []
            messages.append({
                "id": m_row["id"],
                "role": m_row["role"],
                "content": m_row["content"],
                "attachments": attachments,
                "sources": sources
            })
            
        sessions.append({
            "id": s_id,
            "title": s_row["title"],
            "timestamp": s_row["created_at"],
            "messages": messages
        })
        
    conn.close()
    return sessions

def create_or_update_session(session_id: str, title: str) -> Dict[str, Any]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute(
            "UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, session_id)
        )
    else:
        cursor.execute(
            "INSERT INTO sessions (id, title) VALUES (?, ?)",
            (session_id, title)
        )
        
    conn.commit()
    conn.close()
    return {"id": session_id, "title": title}

def add_message_to_session(session_id: str, role: str, content: str, attachments: Optional[List[Any]] = None, sources: Optional[List[Any]] = None, msg_id: Optional[str] = None) -> Dict[str, Any]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if not msg_id:
        msg_id = f"msg_{int(time.time() * 1000)}"
        
    att_json = json.dumps(attachments) if attachments else None
    src_json = json.dumps(sources) if sources else None
    
    cursor.execute(
        "INSERT INTO messages (id, session_id, role, content, attachments, sources) VALUES (?, ?, ?, ?, ?, ?)",
        (msg_id, session_id, role, content, att_json, src_json)
    )
    
    # Touch updated_at on session
    cursor.execute("UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
    
    conn.commit()
    conn.close()
    return {
        "id": msg_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "attachments": attachments or [],
        "sources": sources or []
    }

def delete_session_db(session_id: str) -> bool:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    
    conn.commit()
    conn.close()
    return True
