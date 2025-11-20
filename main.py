"""Main application entry point for Agentic Writer.

Per spec sections 2.1 and 4.1:
- Uses FastHTML as the server framework
- Provides UI for project/resource/artefact management
- Orchestrates AI agents for blog post generation
"""

from fasthtml.common import *
from app.models import init_db
from app.routes.projects import create_project_route
from app.routes.resources import create_resource_routes
from app.routes.artefacts import create_artefact_routes
from app.routes.agents import create_agent_routes
from app.config import Config
import os

# Ensure storage directories exist
os.makedirs(Config.STORAGE_PATH, exist_ok=True)
os.makedirs(Config.FILES_PATH, exist_ok=True)
os.makedirs(Config.IMAGES_PATH, exist_ok=True)

# Initialize database
print("Initializing database...")
init_db()
print("Database initialized.")

# Create FastHTML app
app = FastHTML(
    hdrs=(
        Script(src="https://cdn.tailwindcss.com"),
        Script(src="https://unpkg.com/htmx.org@1.9.10"),
    )
)

# Register routes
print("Registering routes...")
create_project_route(app)
create_resource_routes(app)
create_artefact_routes(app)
create_agent_routes(app)
print("Routes registered.")

if __name__ == "__main__":
    import uvicorn

    print(f"""
    ╔═══════════════════════════════════════════╗
    ║      Agentic Writer - Starting Up         ║
    ╚═══════════════════════════════════════════╝

    🌐 Server: http://{Config.HOST}:{Config.PORT}
    📁 Storage: {Config.STORAGE_PATH}
    🤖 Default Model: {Config.DEFAULT_MODEL}

    """)

    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=True
    )
