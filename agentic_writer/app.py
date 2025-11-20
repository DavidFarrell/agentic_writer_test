from fasthtml.common import *
from monsterui.all import *
from agentic_writer.database import get_db_connection, init_db
from agentic_writer.config import MODELS, DEFAULT_MODEL

# Initialize DB
init_db()

# Theme
hdrs = Theme.blue.headers()
app, rt = fast_app(hdrs=hdrs)

def get_projects():
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM projects ORDER BY created_at DESC').fetchall()
    conn.close()
    return projects

def create_project_db(name, description, model_id):
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO projects (name, description, default_model_id) VALUES (?, ?, ?)',
        (name, description, model_id)
    )
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return project_id

@rt("/")
def index():
    projects = get_projects()
    
    project_list = Div(
        *[Card(
            H3(p['name']),
            P(p['description'], cls=TextT.sm + TextT.gray),
            Div(
                Small(f"Model: {MODELS.get(p['default_model_id'], {}).get('display_name', p['default_model_id'])}"),
                cls="mt-2"
            ),
            A(Button("Open", cls=ButtonT.primary + " w-full mt-4"), href=f"/projects/{p['id']}"),
            cls="mb-4"
        ) for p in projects],
        cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    ) if projects else P("No projects yet. Create one to get started!", cls="text-center text-gray-500 my-8")

    return Titled("Agentic Writer",
        Container(
            DivFullySpaced(
                H1("My Projects"),
                A(Button("New Project", cls=ButtonT.primary), href="/projects/new")
            ),
            Divider(),
            project_list
        )
    )

@rt("/projects/new")
def new_project():
    model_options = [Option(m['display_name'], value=k, selected=(k==DEFAULT_MODEL)) for k, m in MODELS.items()]
    
    return Titled("New Project",
        Container(
            H1("Create New Project"),
            Form(
                LabelInput("Project Name", name="name", required=True),
                LabelTextArea("Description", name="description", rows=3),
                LabelSelect("Default Model", Options(*model_options), name="model_id"),
                Div(
                    Button("Create Project", cls=ButtonT.primary),
                    A(Button("Cancel", cls=ButtonT.ghost), href="/"),
                    cls="flex gap-2 mt-4"
                ),
                method="post",
                action="/projects"
            )
        )
    )

@rt("/projects")
def create_project(name: str, description: str, model_id: str):
    pid = create_project_db(name, description, model_id)
    return RedirectResponse(f"/projects/{pid}", status_code=303)

from agentic_writer.services.ingestion_service import IngestionService, UPLOAD_DIR
from agentic_writer.services.llm_service import LLMService

# Initialize Services
ingestion_service = IngestionService()
llm_service = LLMService()

def add_resource_db(project_id, label, type, origin, content, raw_path, url, token_count):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO resources (project_id, label, type, origin, content, raw_path, url, token_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (project_id, label, type, origin, content, raw_path, url, token_count)
    )
    conn.commit()
    conn.close()

def get_resources(project_id):
    conn = get_db_connection()
    resources = conn.execute('SELECT * FROM resources WHERE project_id = ?', (project_id,)).fetchall()
    conn.close()
    return resources

@rt("/projects/{pid}/upload")
async def upload_file(pid: int, file: UploadFile, request: Request):
    content = await file.read()
    filename = file.filename
    
    # Save file
    path = UPLOAD_DIR / filename
    with open(path, "wb") as f:
        f.write(content)
    
    # Extract text
    text = ingestion_service.extract_text(str(path), file.content_type)
    
    # Count tokens (using default model of project or global default)
    # Ideally fetch project default model, for now use DEFAULT_MODEL
    token_count = llm_service.count_tokens(text, DEFAULT_MODEL)
    
    add_resource_db(pid, filename, "file", "file_upload", text, str(path), "", token_count)
    return RedirectResponse(f"/projects/{pid}", status_code=303)

@rt("/projects/{pid}/add_url")
def add_url(pid: int, url: str):
    title, text, type_ = ingestion_service.process_url(url)
    token_count = llm_service.count_tokens(text, DEFAULT_MODEL)
    
    add_resource_db(pid, title, type_, "url", text, "", url, token_count)
    return RedirectResponse(f"/projects/{pid}", status_code=303)

@rt("/projects/{pid}/toggle_resource/{rid}")
def toggle_resource(pid: int, rid: int):
    conn = get_db_connection()
    # Toggle active status
    conn.execute('UPDATE resources SET active = NOT active WHERE id = ?', (rid,))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/projects/{pid}", status_code=303)

def get_artefact(project_id):
    conn = get_db_connection()
    artefact = conn.execute('SELECT * FROM artefacts WHERE project_id = ?', (project_id,)).fetchone()
    conn.close()
    return artefact

def create_artefact(project_id, title):
    conn = get_db_connection()
    cursor = conn.execute('INSERT INTO artefacts (project_id, title) VALUES (?, ?)', (project_id, title))
    aid = cursor.lastrowid
    conn.commit()
    conn.close()
    return aid

def create_artefact_version(artefact_id, content, created_by, prompt_summary):
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO artefact_versions (artefact_id, content_markdown, created_by, prompt_summary) VALUES (?, ?, ?, ?)',
        (artefact_id, content, created_by, prompt_summary)
    )
    vid = cursor.lastrowid
    # Update current version
    conn.execute('UPDATE artefacts SET current_version_id = ? WHERE id = ?', (vid, artefact_id))
    conn.commit()
    conn.close()
    return vid

def get_current_version(artefact_id):
    conn = get_db_connection()
    # Get current version ID from artefact
    art = conn.execute('SELECT current_version_id FROM artefacts WHERE id = ?', (artefact_id,)).fetchone()
    if not art or not art['current_version_id']:
        conn.close()
        return None
    
    version = conn.execute('SELECT * FROM artefact_versions WHERE id = ?', (art['current_version_id'],)).fetchone()
    conn.close()
    return version

@rt("/projects/{pid}/run_agent")
def run_agent(pid: int, prompt: str, agent_type: str, model_id: str):
    # Get resources
    resources = [dict(r) for r in get_resources(pid)] # Convert Row to dict
    
    # Get current artefact
    artefact = get_artefact(pid)
    if not artefact:
        aid = create_artefact(pid, "Draft")
        current_content = ""
    else:
        aid = artefact['id']
        current_version = get_current_version(aid)
        current_content = current_version['content_markdown'] if current_version else ""

    # Run Agent
    result = llm_service.run_agent(agent_type, prompt, resources, current_content, model_id)
    
    # Save new version
    create_artefact_version(aid, result['content'], agent_type, prompt)
    
    # TODO: Save logs
    
    return RedirectResponse(f"/projects/{pid}", status_code=303)

@rt("/projects/{pid}")
def project_dashboard(pid: int):
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (pid,)).fetchone()
    conn.close()
    
    if not project:
        return Titled("Error", Container(H1("Project not found"), A("Back to Home", href="/")))

    resources = get_resources(pid)
    
    # Context Map Visualization
    total_tokens = sum(r['token_count'] for r in resources if r['active'])
    max_tokens = MODELS[project['default_model_id']]['context_window']
    usage_percent = min(100, (total_tokens / max_tokens) * 100)
    
    context_map = Card(
        H3("Context Usage"),
        Div(
            Div(f"{total_tokens:,} / {max_tokens:,} tokens ({usage_percent:.1f}%)", cls="text-sm mb-1"),
            Div(
                Div(style=f"width: {usage_percent}%;", cls="bg-blue-500 h-full rounded"),
                cls="w-full h-4 bg-gray-200 rounded overflow-hidden"
            ),
            cls="mb-4"
        ),
        Div(
            *[Div(
                Div(
                    Span(r['label'], cls="font-bold truncate"),
                    Span(f"{r['token_count']:,} toks", cls="text-xs text-gray-500"),
                    cls="flex justify-between items-center"
                ),
                Div(
                    Badge(r['type'], cls="mr-2"),
                    A("Toggle", href=f"/projects/{pid}/toggle_resource/{r['id']}", cls="text-xs text-blue-500 hover:underline"),
                    cls="flex items-center mt-1"
                ),
                cls=f"p-2 border rounded mb-2 {'bg-white' if r['active'] else 'bg-gray-100 opacity-50'}"
            ) for r in resources],
            cls="max-h-64 overflow-y-auto"
        ) if resources else P("No resources added."),
        cls="h-full"
    )

    # Artefact Display
    artefact = get_artefact(pid)
    current_version = get_current_version(artefact['id']) if artefact else None
    artefact_content = current_version['content_markdown'] if current_version else "No content yet. Start by running the Writer agent."

    return Titled(project['name'],
        Container(
            DivFullySpaced(
                H1(project['name']),
                Div(
                    A(Button("Back", cls=ButtonT.ghost), href="/"),
                    Button("Settings", cls=ButtonT.secondary)
                )
            ),
            P(project['description'], cls="text-gray-600 mb-6"),
            
            # 3-Panel Layout
            Grid(
                # Left Panel: Resources
                Div(
                    H3("Resources"),
                    context_map,
                    Card(
                        H4("Add Resource"),
                        Form(
                            LabelInput("Upload File", type="file", name="file"),
                            Button("Upload", cls=ButtonT.sm + " w-full mb-4"),
                            enctype="multipart/form-data",
                            method="post",
                            action=f"/projects/{pid}/upload"
                        ),
                        Divider(),
                        Form(
                            LabelInput("Add URL", name="url", placeholder="https://..."),
                            Button("Add URL", cls=ButtonT.sm + " w-full"),
                            method="post",
                            action=f"/projects/{pid}/add_url"
                        ),
                        cls="mt-4"
                    ),
                    cls="col-span-3"
                ),
                
                # Center Panel: Chat
                Div(
                    H3("Chat & Agents"),
                    Card(
                        Div("Chat history will appear here...", cls="h-64 bg-gray-50 p-4 rounded mb-4"),
                        Form(
                            TextArea(name="prompt", placeholder="Instructions for the agent...", rows=3, cls="w-full mb-2"),
                            DivFullySpaced(
                                Select(Options(*[Option(m['display_name'], value=k) for k, m in MODELS.items()]), name="model_id", cls="w-40"),
                                Div(
                                    Button("Writer", name="agent_type", value="writer", cls=ButtonT.primary),
                                    Button("Style", name="agent_type", value="style_editor", cls=ButtonT.secondary),
                                    Button("Detail", name="agent_type", value="detail_editor", cls=ButtonT.secondary),
                                    Button("Fact", name="agent_type", value="fact_checker", cls=ButtonT.secondary),
                                    cls="flex gap-1"
                                )
                            ),
                            method="post",
                            action=f"/projects/{pid}/run_agent"
                        ),
                        cls="h-full"
                    ),
                    cls="col-span-5"
                ),
                
                # Right Panel: Artefact
                Div(
                    H3("Artefact"),
                    Card(
                        Div(
                            Div(artefact_content, cls="prose max-w-none"), # Use prose for markdown styling
                            cls="h-full overflow-y-auto"
                        ),
                        cls="h-full"
                    ),
                    cls="col-span-4"
                ),
                cols=12,
                gap=4
            )
        , size=Container.xl)
    )

if __name__ == "__main__":
    serve()
