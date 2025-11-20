"""Resource management routes."""

from fasthtml.common import *
from sqlalchemy.orm import Session
from app.models import get_db, Resource, Project
from app.services.ingestion import IngestionService
import asyncio


def create_resource_routes(app):
    """Create resource-related routes."""

    ingestion_service = IngestionService()

    @app.get("/projects/{project_id}/resources/new")
    def new_resource_form(project_id: int):
        """Show new resource form."""
        db = next(get_db())
        project = db.query(Project).filter(Project.id == project_id).first()

        if not project:
            return Response("Project not found", status_code=404)

        resource_types = [
            ("audio_notes", "Audio Notes / Transcript"),
            ("source_transcript", "Source Transcript"),
            ("article", "Article"),
            ("book", "Book"),
            ("blog_corpus", "Blog Corpus"),
            ("other", "Other")
        ]

        return Html(
            Head(
                Title("Add Resource - Agentic Writer"),
                Script(src="https://cdn.tailwindcss.com"),
            ),
            Body(cls="bg-gray-50 min-h-screen")(
                Div(cls="container mx-auto px-4 py-8 max-w-2xl")(
                    H1(cls="text-3xl font-bold mb-6")("Add Resource"),
                    Form(
                        method="post",
                        action=f"/projects/{project_id}/resources",
                        enctype="multipart/form-data"
                    )(
                        Div(cls="mb-4")(
                            Label("Resource Type", cls="block font-semibold mb-2"),
                            Select(name="resource_type", cls="w-full border rounded px-3 py-2", required=True)(
                                *[Option(label, value=value) for value, label in resource_types]
                            )
                        ),
                        Div(cls="mb-4")(
                            Label("Label / Name", cls="block font-semibold mb-2"),
                            Input(
                                type="text",
                                name="label",
                                placeholder="e.g., 'My audio notes on topic X'",
                                cls="w-full border rounded px-3 py-2",
                                required=True
                            )
                        ),
                        Div(cls="mb-4")(
                            Label("Source", cls="block font-semibold mb-2"),
                            Div(cls="space-y-2")(
                                Label(cls="flex items-center")(
                                    Input(type="radio", name="source_type", value="file", checked=True),
                                    Span(cls="ml-2")("Upload File")
                                ),
                                Label(cls="flex items-center")(
                                    Input(type="radio", name="source_type", value="url"),
                                    Span(cls="ml-2")("URL")
                                )
                            )
                        ),
                        Div(id="file-input", cls="mb-4")(
                            Label("File", cls="block font-semibold mb-2"),
                            Input(
                                type="file",
                                name="file",
                                cls="w-full border rounded px-3 py-2"
                            )
                        ),
                        Div(id="url-input", cls="mb-4 hidden")(
                            Label("URL", cls="block font-semibold mb-2"),
                            Input(
                                type="url",
                                name="url",
                                placeholder="https://...",
                                cls="w-full border rounded px-3 py-2"
                            )
                        ),
                        Div(cls="flex gap-3")(
                            Button(
                                "Add Resource",
                                type="submit",
                                cls="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
                            ),
                            A(
                                "Cancel",
                                href=f"/projects/{project_id}",
                                cls="bg-gray-300 px-6 py-2 rounded hover:bg-gray-400"
                            )
                        )
                    ),
                    Script("""
                        const radios = document.querySelectorAll('input[name="source_type"]');
                        const fileInput = document.getElementById('file-input');
                        const urlInput = document.getElementById('url-input');

                        radios.forEach(radio => {
                            radio.addEventListener('change', (e) => {
                                if (e.target.value === 'file') {
                                    fileInput.classList.remove('hidden');
                                    urlInput.classList.add('hidden');
                                } else {
                                    fileInput.classList.add('hidden');
                                    urlInput.classList.remove('hidden');
                                }
                            });
                        });
                    """)
                )
            )
        )

    @app.post("/projects/{project_id}/resources")
    async def create_resource(
        project_id: int,
        resource_type: str,
        label: str,
        source_type: str,
        file: UploadFile = None,
        url: str = None
    ):
        """Create a new resource."""
        db = next(get_db())
        project = db.query(Project).filter(Project.id == project_id).first()

        if not project:
            return Response("Project not found", status_code=404)

        try:
            if source_type == "file" and file:
                # File upload
                file_content = await file.read()
                resource = ingestion_service.ingest_file(
                    db=db,
                    project_id=project_id,
                    file_content=file_content,
                    filename=file.filename,
                    label=label,
                    resource_type=resource_type,
                    model_id=project.default_model_id
                )
            elif source_type == "url" and url:
                # URL ingestion
                resource = await ingestion_service.ingest_url(
                    db=db,
                    project_id=project_id,
                    url=url,
                    label=label,
                    resource_type=resource_type,
                    model_id=project.default_model_id
                )
            else:
                return Response("Invalid source", status_code=400)

            return RedirectResponse(f"/projects/{project_id}", status_code=303)

        except Exception as e:
            return Response(f"Error creating resource: {str(e)}", status_code=500)

    @app.post("/resources/{resource_id}/toggle")
    def toggle_resource(resource_id: int):
        """Toggle resource active state."""
        db = next(get_db())

        from app.services.context_manager import ContextManager
        cm = ContextManager()
        active = cm.toggle_resource(db, resource_id)

        # Return updated resource element
        resource = db.query(Resource).filter(Resource.id == resource_id).first()

        return Div(
            cls=f"p-2 border rounded {'bg-blue-50 border-blue-300' if active else 'bg-gray-50 border-gray-200'}"
        )(
            Div(cls="flex justify-between items-start")(
                Div()(
                    P(cls="font-semibold text-sm")(resource.label),
                    P(cls="text-xs text-gray-500")(f"{resource.total_tokens:,} tokens")
                ),
                Form(
                    method="post",
                    action=f"/resources/{resource_id}/toggle",
                    hx_post=f"/resources/{resource_id}/toggle",
                    hx_swap="outerHTML",
                    hx_target="closest div"
                )(
                    Button(
                        "✓" if active else "○",
                        type="submit",
                        cls=f"text-xs px-2 py-1 rounded {'bg-blue-600 text-white' if active else 'bg-gray-300'}"
                    )
                )
            )
        )
