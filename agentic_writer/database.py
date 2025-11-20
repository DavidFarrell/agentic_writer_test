import sqlite3
from dataclasses import dataclass
from typing import Optional, List
import json
import os

DB_PATH = "agentic_writer.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Projects
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        default_model_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Resources
    c.execute('''CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        type TEXT NOT NULL,
        origin TEXT NOT NULL,
        content TEXT, 
        raw_path TEXT,
        url TEXT,
        token_count INTEGER,
        active BOOLEAN DEFAULT 1,
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )''')
    
    # Artefacts
    c.execute('''CREATE TABLE IF NOT EXISTS artefacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT,
        current_version_id INTEGER,
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )''')
    
    # Artefact Versions
    c.execute('''CREATE TABLE IF NOT EXISTS artefact_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artefact_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_agent TEXT,
        prompt_summary TEXT,
        content_markdown TEXT,
        FOREIGN KEY (artefact_id) REFERENCES artefacts (id)
    )''')

    # Agent Runs
    c.execute('''CREATE TABLE IF NOT EXISTS agent_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        artefact_id INTEGER,
        agent_type TEXT,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        status TEXT,
        iteration_count INTEGER,
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )''')

    # Agent Run Logs
    c.execute('''CREATE TABLE IF NOT EXISTS agent_run_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_run_id INTEGER NOT NULL,
        iteration_index INTEGER,
        role TEXT,
        content TEXT,
        tokens_used INTEGER,
        FOREIGN KEY (agent_run_id) REFERENCES agent_runs (id)
    )''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
