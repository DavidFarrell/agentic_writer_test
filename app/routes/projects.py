"""Project management routes."""

from fasthtml.common import *
from sqlalchemy.orm import Session
from app.models import Project, Artefact, get_db
from app.config import Config, list_available_models
from datetime import datetime


router = []


def get_projects_list(db: Session):
    """Get list of all projects."""
    return db.query(Project).order_by(Project.updated_at.desc()).all()


def create_project_route(app):
    """Create project-related routes."""

    @app.get("/")
    def home():
        """Home page - list of projects."""
        db = next(get_db())

        projects = get_projects_list(db)

        return Html(
            Head(
                Title("Agentic Writer"),
                Script(src="https://cdn.tailwindcss.com"),
                Script(src="https://unpkg.com/htmx.org@1.9.10"),
            ),
            Body(cls="bg-gray-50 min-h-screen")(
                Div(cls="container mx-auto px-4 py-8")(
                    H1(cls="text-4xl font-bold mb-8")("Agentic Writer"),
                    Div(cls="mb-6")(
                        A(
                            "New Project",
                            href="/projects/new",
                            cls="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                        )
                    ),
                    Div(cls="grid gap-4")(
                        *[
                            Div(cls="bg-white p-6 rounded-lg shadow")(
                                H2(cls="text-2xl font-semibold mb-2")(
                                    A(p.name, href=f"/projects/{p.id}", cls="text-blue-600 hover:underline")
                                ),
                                P(cls="text-gray-600 mb-2")(p.description or "No description"),
                                P(cls="text-sm text-gray-500")(
                                    f"Model: {p.default_model_id} | Updated: {p.updated_at.strftime('%Y-%m-%d %H:%M')}"
                                )
                            )
                            for p in projects
                        ] if projects else [
                            P(cls="text-gray-500")("No projects yet. Create one to get started!")
                        ]
                    )
                )
            )
        )

    @app.get("/projects/new")
    def new_project_form():
        """Show new project form."""
        models = list_available_models()

        return Html(
            Head(
                Title("New Project - Agentic Writer"),
                Script(src="https://cdn.tailwindcss.com"),
            ),
            Body(cls="bg-gray-50 min-h-screen")(
                Div(cls="container mx-auto px-4 py-8 max-w-2xl")(
                    H1(cls="text-3xl font-bold mb-6")("Create New Project"),
                    Form(method="post", action="/projects")(
                        Div(cls="mb-4")(
                            Label("Project Name", cls="block font-semibold mb-2"),
                            Input(
                                type="text",
                                name="name",
                                required=True,
                                cls="w-full border rounded px-3 py-2"
                            )
                        ),
                        Div(cls="mb-4")(
                            Label("Description", cls="block font-semibold mb-2"),
                            Textarea(
                                name="description",
                                rows=3,
                                cls="w-full border rounded px-3 py-2"
                            )
                        ),
                        Div(cls="mb-6")(
                            Label("Default Model", cls="block font-semibold mb-2"),
                            Select(name="default_model_id", cls="w-full border rounded px-3 py-2")(
                                *[Option(m.display_name, value=m.model_id) for m in models]
                            )
                        ),
                        Div(cls="flex gap-3")(
                            Button(
                                "Create Project",
                                type="submit",
                                cls="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
                            ),
                            A(
                                "Cancel",
                                href="/",
                                cls="bg-gray-300 px-6 py-2 rounded hover:bg-gray-400"
                            )
                        )
                    )
                )
            )
        )

    @app.post("/projects")
    def create_project(name: str, description: str, default_model_id: str):
        """Create a new project."""
        db = next(get_db())

        project = Project(
            name=name,
            description=description,
            default_model_id=default_model_id
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # Create initial artefact
        artefact = Artefact(
            project_id=project.id,
            title=f"{name} - Draft"
        )
        db.add(artefact)
        db.commit()

        return RedirectResponse(f"/projects/{project.id}", status_code=303)

    @app.get("/projects/{project_id}")
    def view_project(project_id: int):
        """View project workspace."""
        db = next(get_db())

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return Response("Project not found", status_code=404)

        # Get resources
        from app.models import Resource
        resources = db.query(Resource).filter(Resource.project_id == project_id).all()

        # Get artefact
        artefact = db.query(Artefact).filter(Artefact.project_id == project_id).first()

        # Get current content
        current_content = ""
        if artefact and artefact.current_version_id:
            from app.models import ArtefactVersion
            version = db.query(ArtefactVersion).filter(
                ArtefactVersion.id == artefact.current_version_id
            ).first()
            if version:
                current_content = version.content_markdown

        # Get token summary
        from app.services.context_manager import ContextManager
        cm = ContextManager()
        token_summary = cm.get_token_summary(db, project_id, project.default_model_id)

        return Html(
            Head(
                Title(f"{project.name} - Agentic Writer"),
                Script(src="https://cdn.tailwindcss.com"),
                Script(src="https://unpkg.com/htmx.org@1.9.10"),
                Script(src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"),
            ),
            Body(cls="bg-gray-50 min-h-screen")(
                Div(cls="container mx-auto px-4 py-4")(
                    # Header
                    Div(cls="mb-4 flex justify-between items-center")(
                        Div()(
                            H1(cls="text-3xl font-bold")(project.name),
                            P(cls="text-gray-600")(project.description or "")
                        ),
                        A("← Back to Projects", href="/", cls="text-blue-600 hover:underline")
                    ),

                    # Three-panel layout
                    Div(cls="grid grid-cols-12 gap-4")(
                        # Left panel: Resources
                        Div(cls="col-span-3 bg-white p-4 rounded-lg shadow")(
                            H2(cls="text-xl font-bold mb-4")("Resources"),
                            Div(cls="mb-4")(
                                A(
                                    "Add Resource",
                                    href=f"/projects/{project_id}/resources/new",
                                    cls="text-blue-600 hover:underline text-sm"
                                )
                            ),
                            Div(cls="space-y-2")(
                                *[
                                    Div(
                                        cls=f"p-2 border rounded {'bg-blue-50 border-blue-300' if r.active else 'bg-gray-50 border-gray-200'}"
                                    )(
                                        Div(cls="flex justify-between items-start")(
                                            Div()(
                                                P(cls="font-semibold text-sm")(r.label),
                                                P(cls="text-xs text-gray-500")(f"{r.total_tokens:,} tokens")
                                            ),
                                            Form(
                                                method="post",
                                                action=f"/resources/{r.id}/toggle",
                                                hx_post=f"/resources/{r.id}/toggle",
                                                hx_swap="outerHTML",
                                                hx_target="closest div"
                                            )(
                                                Button(
                                                    "✓" if r.active else "○",
                                                    type="submit",
                                                    cls=f"text-xs px-2 py-1 rounded {'bg-blue-600 text-white' if r.active else 'bg-gray-300'}"
                                                )
                                            )
                                        )
                                    )
                                    for r in resources
                                ] if resources else [P(cls="text-sm text-gray-500")("No resources yet")]
                            ),
                            Div(cls="mt-6 p-3 bg-gray-100 rounded")(
                                H3(cls="font-semibold mb-2 text-sm")("Token Usage"),
                                P(cls="text-xs")(f"Active: {token_summary['active_tokens']:,}"),
                                P(cls="text-xs")(f"Max: {token_summary['max_tokens']:,}"),
                                P(cls="text-xs")(f"Utilization: {token_summary['utilization']*100:.1f}%")
                            )
                        ),

                        # Center panel: Chat and agents
                        Div(cls="col-span-5 bg-white p-4 rounded-lg shadow")(
                            H2(cls="text-xl font-bold mb-4")("AI Assistant"),
                            Form(
                                method="post",
                                action=f"/projects/{project_id}/agents/run",
                                cls="space-y-4"
                            )(
                                Textarea(
                                    name="instruction",
                                    placeholder="Enter your instruction...",
                                    rows=4,
                                    cls="w-full border rounded px-3 py-2"
                                ),
                                Div(cls="grid grid-cols-2 gap-2")(
                                    Button(
                                        "Writer Agent",
                                        type="submit",
                                        name="agent_type",
                                        value="writer",
                                        cls="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                                    ),
                                    Button(
                                        "Style Editor",
                                        type="submit",
                                        name="agent_type",
                                        value="style_editor",
                                        cls="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
                                    ),
                                    Button(
                                        "Detail Editor",
                                        type="submit",
                                        name="agent_type",
                                        value="detail_editor",
                                        cls="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700"
                                    ),
                                    Button(
                                        "Fact Checker",
                                        type="submit",
                                        name="agent_type",
                                        value="fact_checker",
                                        cls="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                                    )
                                ),
                                Input(type="hidden", name="artefact_id", value=str(artefact.id if artefact else ""))
                            ),
                            Div(cls="mt-6")(
                                A(
                                    "View Agent Logs",
                                    href=f"/projects/{project_id}/agents",
                                    cls="text-blue-600 hover:underline text-sm"
                                )
                            )
                        ),

                        # Right panel: Artefact
                        Div(cls="col-span-4 bg-white p-4 rounded-lg shadow")(
                            H2(cls="text-xl font-bold mb-4")("Blog Post"),
                            Div(cls="mb-4 flex gap-2")(
                                A(
                                    "Versions",
                                    href=f"/artefacts/{artefact.id}/versions" if artefact else "#",
                                    cls="text-blue-600 hover:underline text-sm"
                                ),
                                A(
                                    "Export",
                                    href=f"/artefacts/{artefact.id}/export" if artefact else "#",
                                    cls="text-blue-600 hover:underline text-sm"
                                )
                            ),
                            Div(
                                id="artefact-preview",
                                cls="prose max-w-none border rounded p-4 bg-gray-50 max-h-[600px] overflow-y-auto"
                            )(
                                current_content if current_content else P(cls="text-gray-500")("No content yet. Run the Writer agent to create a draft.")
                            ),
                            Script("""
                                // Render markdown
                                const preview = document.getElementById('artefact-preview');
                                if (preview.textContent.trim() && !preview.textContent.includes('No content yet')) {
                                    const markdown = preview.textContent;
                                    preview.innerHTML = marked.parse(markdown);
                                }
                            """)
                        )
                    )
                )
            )
        )
