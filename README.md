# Agentic Writer

A local-first web application that helps the user draft blog posts using large language models (LLMs) without producing generic "AI slop".

## Developer Guidelines

> [!IMPORTANT]
> **Mandatory Rule:** Any autonomous agent or code-generation routine used to extend or modify this application must first load and read all documents in `LLM_docs/` before writing any code.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   Create a `.env` file with:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

3. Run the application:
   ```bash
   python agentic_writer/app.py
   ```

## Testing

Run tests with:
```bash
pytest
```
