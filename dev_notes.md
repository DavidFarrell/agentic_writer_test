# Developer Notes

## LLM_docs Compliance

Any automated code-writing agent or script used to modify this repository must first read all documents in `LLM_docs/` and must not generate or change code without doing so.

Use the helper function `load_llm_docs()` in `agentic_writer/utils.py` to programmatically access these documents.
