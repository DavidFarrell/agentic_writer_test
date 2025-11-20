import os
import pytest
from agentic_writer.database import init_db, get_db_connection
from agentic_writer.app import app

def test_db_initialization():
    # Use a test DB
    if os.path.exists("agentic_writer.db"):
        os.remove("agentic_writer.db")
        
    init_db()
    assert os.path.exists("agentic_writer.db")
    
    conn = get_db_connection()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t['name'] for t in tables]
    
    assert 'projects' in table_names
    assert 'resources' in table_names
    assert 'artefacts' in table_names
    conn.close()

def test_app_import():
    assert app is not None
