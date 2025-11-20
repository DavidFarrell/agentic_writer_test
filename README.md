# Agentic Writer

A context-managed AI-assisted blogging tool that helps you draft blog posts using large language models without producing generic "AI slop".

## Overview

Agentic Writer is a local-first web application built with Python and FastHTML that treats you as the primary author. It uses AI to assist with structure, style, and detail—not to overwrite your intent.

### Key Features

- **Context Management**: Explicit, fine-grained control over what context the AI sees
- **Token Visualization**: Visual treemap showing context window allocation
- **Multi-Agent Workflow**: Specialized agents (Writer, Style Editor, Detail Editor, Fact Checker)
- **Resource Ingestion**: Import files, URLs, YouTube videos, and transcripts
- **Version Control**: Track all changes with undo/redo and version history
- **Transparent AI**: Inspect agent reasoning and context usage
- **Local-First**: All data stored locally by default

## Technology Stack

- **Language**: Python 3.10+
- **Framework**: FastHTML
- **UI Components**: Munster UI (ShadCN-based)
- **LLM Provider**: Google Gemini
- **Database**: SQLite
- **File Processing**: PyPDF, python-docx, BeautifulSoup

## Prerequisites

- Python 3.10 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd agentic_writer_test
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

## Configuration

Edit `.env` file:

```env
# Gemini API Configuration
GEMINI_API_KEY=your_api_key_here

# Application Configuration
DEFAULT_MODEL=gemini-2.0-flash-exp
STORAGE_PATH=./storage
DATABASE_URL=sqlite:///./storage/agentic_writer.db

# Server Configuration
HOST=0.0.0.0
PORT=5001
```

## Running the Application

```bash
python main.py
```

Then open your browser to: `http://localhost:5001`

## Usage Guide

### 1. Create a Project

1. Click "New Project" on the home page
2. Enter a name and description
3. Select your preferred Gemini model
4. Click "Create Project"

### 2. Add Resources

Resources are the materials your AI agents will use:

- **Audio Notes**: Your dictated notes or transcripts
- **Source Transcripts**: YouTube videos, podcasts, etc.
- **Articles**: Web pages or documents
- **Blog Corpus**: Your previous blog posts for style reference

To add a resource:
1. Click "Add Resource" in the left panel
2. Choose the resource type
3. Upload a file or provide a URL
4. Click "Add Resource"

### 3. Manage Context

- **Toggle Resources**: Click the checkbox next to each resource to include/exclude it from the AI context
- **View Token Usage**: See how much of your context window is being used
- **Prioritization**: The system automatically prioritizes:
  1. Your audio notes (highest priority)
  2. Source materials
  3. Blog corpus for style

### 4. Run AI Agents

Four specialized agents are available:

#### Writer Agent
Creates a first draft from your notes and source materials.
- Preserves your voice and intentions
- Uses sources for detail, not to overwrite you
- Multi-pass workflow for completeness

#### Style Editor
Adjusts the draft to match your established writing style.
- Analyzes your blog corpus
- Maintains your unique voice
- Avoids generic AI language

#### Detail Editor
Ensures the post is sufficiently detailed and concrete.
- Identifies vague areas
- Adds examples and code snippets
- References source materials

#### Fact Checker
Verifies factual accuracy against source materials.
- Cross-references claims
- Flags unsupported statements
- Suggests corrections

### 5. View and Manage Versions

- **Version History**: Click "Versions" to see all drafts
- **Restore**: Restore any previous version
- **Compare**: View differences between versions

### 6. Export

Export your blog post in multiple formats:
- Markdown (`.md`)
- HTML
- Plain text

## Project Structure

```
agentic_writer_test/
├── app/
│   ├── agents/           # AI agent implementations
│   ├── models/           # Database models
│   ├── routes/           # FastHTML routes
│   ├── services/         # Business logic services
│   └── utils/            # Utility functions
├── storage/              # Local file storage (created on first run)
│   ├── files/           # Uploaded files
│   ├── images/          # Image assets
│   └── agentic_writer.db # SQLite database
├── LLM_docs/            # LLM documentation (for dev agents)
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Supported File Formats

- **Text**: `.txt`, `.md`, `.json`, `.html`
- **Documents**: `.pdf`, `.docx`
- **Images**: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`
- **Video**: `.mp4`, `.mov`, `.avi`, `.webm`
- **Audio**: `.mp3`, `.wav`, `.m4a`, `.ogg`

## Developer Guidelines

### LLM_docs Compliance

**IMPORTANT**: Any automated code-writing agent or script used to modify this repository must first read all documents in `LLM_docs/` before generating or changing code.

Use the helper function:
```python
from app.utils import load_llm_docs

docs = load_llm_docs()
# docs is a dict of filename -> content
```

### Running Tests

```bash
pytest
```

### Code Organization

- **Models**: Database schema (SQLAlchemy ORM)
- **Services**: Business logic (tokenization, ingestion, context management)
- **Agents**: AI orchestration (Writer, Style Editor, etc.)
- **Routes**: HTTP endpoints (FastHTML)

## Architecture

### Context Management

The system implements a sophisticated context management system:

1. **Tokenization**: All resources are tokenized using the selected model's tokenizer
2. **Budget Tracking**: Real-time tracking of token usage vs. model limits
3. **Prioritization**: Automatic prioritization based on resource type
4. **Chunking**: Oversized resources are automatically chunked

### Agent Workflow

Each agent follows a transparent, multi-pass workflow:

1. Build context plan from active resources
2. Execute multiple LLM calls with reflection
3. Log all prompts and responses
4. Create new artefact version
5. Make all logs available for inspection

### Data Storage

- **Database**: SQLite for structured data (projects, resources, versions, logs)
- **Filesystem**: Raw files stored in `storage/files/`
- **Images**: Stored in `storage/images/`

## Troubleshooting

### API Key Issues

If you see authentication errors:
1. Check that `GEMINI_API_KEY` is set in `.env`
2. Verify the API key is valid at https://makersuite.google.com

### Import Errors

If you see module import errors:
```bash
pip install -r requirements.txt --upgrade
```

### Database Issues

To reset the database:
```bash
rm storage/agentic_writer.db
python main.py  # Will recreate database
```

## Limitations (v1)

- No collaboration features (single user)
- No cloud sync (local-first)
- Limited to Gemini models
- Basic treemap visualization (can be enhanced)

## Future Enhancements

- Advanced diff visualization
- Per-paragraph provenance tracking
- Multi-user collaboration
- Model-agnostic plugin system
- Enhanced image generation workflow

## Contributing

1. Read all documents in `LLM_docs/` first
2. Follow the existing code structure
3. Add tests for new features
4. Update this README as needed

## License

[Add your license here]

## Support

For issues and questions, please create an issue in the repository.

## Acknowledgments

Built with:
- [FastHTML](https://fastht.ml/)
- [Google Gemini](https://ai.google.dev/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Tailwind CSS](https://tailwindcss.com/)
