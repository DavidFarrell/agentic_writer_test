import os
from pathlib import Path

def load_llm_docs() -> str:
    """
    Reads all files in LLM_docs/ and returns their concatenated contents.
    Useful for agents to understand the codebase context.
    """
    docs_dir = Path("LLM_docs")
    if not docs_dir.exists():
        return "LLM_docs directory not found."
        
    content = ""
    for file_path in docs_dir.glob("**/*"):
        if file_path.is_file() and file_path.suffix in ['.md', '.txt']:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content += f"\n\n--- File: {file_path.name} ---\n\n"
                    content += f.read()
            except Exception as e:
                content += f"\n\nError reading {file_path.name}: {e}\n"
                
    return content
