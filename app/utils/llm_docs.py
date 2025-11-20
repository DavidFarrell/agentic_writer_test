"""LLM documentation loader.

Per spec section 11.1, provides a helper to load all documents from LLM_docs/
for use by development agents.
"""

from pathlib import Path
from typing import Dict


def load_llm_docs(docs_path: str = "./LLM_docs") -> Dict[str, str]:
    """Load all documents from LLM_docs directory.

    Per spec section 11.1:
    "Any automated code-writing agent or script used to modify this repository
    must first read all documents in LLM_docs/ and must not generate or change
    code without doing so."

    Args:
        docs_path: Path to LLM_docs directory

    Returns:
        Dictionary mapping filename to content
    """
    docs_dir = Path(docs_path)

    if not docs_dir.exists():
        return {}

    docs = {}

    for file_path in docs_dir.glob("*.md"):
        try:
            docs[file_path.name] = file_path.read_text(encoding="utf-8")
        except Exception as e:
            docs[file_path.name] = f"[Error loading: {e}]"

    return docs


def get_llm_docs_content() -> str:
    """Get concatenated content of all LLM docs.

    Returns:
        Concatenated documentation string
    """
    docs = load_llm_docs()

    if not docs:
        return "[No LLM documentation found]"

    parts = []
    for filename, content in sorted(docs.items()):
        parts.append(f"# {filename}\n\n{content}\n\n")

    return "\n".join(parts)
