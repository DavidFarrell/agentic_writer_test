"""Artefact management routes."""

from fasthtml.common import *
from sqlalchemy.orm import Session
from app.models import get_db, Artefact, ArtefactVersion
import markdown


def create_artefact_routes(app):
    """Create artefact-related routes."""

    @app.get("/artefacts/{artefact_id}/versions")
    def view_versions(artefact_id: int):
        """View artefact version history."""
        db = next(get_db())

        artefact = db.query(Artefact).filter(Artefact.id == artefact_id).first()
        if not artefact:
            return Response("Artefact not found", status_code=404)

        versions = db.query(ArtefactVersion).filter(
            ArtefactVersion.artefact_id == artefact_id
        ).order_by(ArtefactVersion.created_at.desc()).all()

        return Html(
            Head(
                Title("Version History - Agentic Writer"),
                Script(src="https://cdn.tailwindcss.com"),
                Script(src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"),
            ),
            Body(cls="bg-gray-50 min-h-screen")(
                Div(cls="container mx-auto px-4 py-8 max-w-4xl")(
                    H1(cls="text-3xl font-bold mb-6")("Version History"),
                    A(
                        "← Back to Project",
                        href=f"/projects/{artefact.project_id}",
                        cls="text-blue-600 hover:underline mb-4 inline-block"
                    ),
                    Div(cls="space-y-4")(
                        *[
                            Div(cls="bg-white p-6 rounded-lg shadow")(
                                Div(cls="flex justify-between items-start mb-4")(
                                    Div()(
                                        H3(cls="text-lg font-semibold")(
                                            f"Version {v.id}" + (
                                                " (Current)" if v.id == artefact.current_version_id else ""
                                            )
                                        ),
                                        P(cls="text-sm text-gray-600")(
                                            f"By: {v.created_by_agent or 'user'} | {v.created_at.strftime('%Y-%m-%d %H:%M')}"
                                        ),
                                        P(cls="text-sm text-gray-500")(v.prompt_summary or "")
                                    ),
                                    Div(cls="flex gap-2")(
                                        Form(
                                            method="post",
                                            action=f"/artefacts/{artefact_id}/restore/{v.id}"
                                        )(
                                            Button(
                                                "Restore",
                                                type="submit",
                                                cls="bg-blue-600 text-white px-3 py-1 text-sm rounded hover:bg-blue-700"
                                            )
                                        ),
                                        A(
                                            "View",
                                            href=f"/artefacts/versions/{v.id}",
                                            cls="bg-gray-200 px-3 py-1 text-sm rounded hover:bg-gray-300"
                                        )
                                    )
                                ),
                                Details()(
                                    Summary(cls="cursor-pointer font-semibold")("Preview"),
                                    Div(
                                        cls="prose max-w-none mt-4 p-4 bg-gray-50 rounded",
                                        id=f"preview-{v.id}"
                                    )(v.content_markdown[:500] + "..." if len(v.content_markdown) > 500 else v.content_markdown)
                                )
                            )
                            for v in versions
                        ] if versions else [
                            P(cls="text-gray-500")("No versions yet")
                        ]
                    )
                )
            )
        )

    @app.get("/artefacts/versions/{version_id}")
    def view_version(version_id: int):
        """View a specific version."""
        db = next(get_db())

        version = db.query(ArtefactVersion).filter(ArtefactVersion.id == version_id).first()
        if not version:
            return Response("Version not found", status_code=404)

        artefact = db.query(Artefact).filter(Artefact.id == version.artefact_id).first()

        html_content = markdown.markdown(version.content_markdown, extensions=['fenced_code', 'tables'])

        return Html(
            Head(
                Title(f"Version {version_id} - Agentic Writer"),
                Script(src="https://cdn.tailwindcss.com"),
            ),
            Body(cls="bg-gray-50 min-h-screen")(
                Div(cls="container mx-auto px-4 py-8 max-w-4xl")(
                    Div(cls="mb-6")(
                        A(
                            "← Back to Versions",
                            href=f"/artefacts/{artefact.id}/versions",
                            cls="text-blue-600 hover:underline"
                        )
                    ),
                    Div(cls="bg-white p-8 rounded-lg shadow")(
                        Div(cls="mb-6")(
                            H1(cls="text-2xl font-bold")(f"Version {version_id}"),
                            P(cls="text-gray-600")(
                                f"By: {version.created_by_agent or 'user'} | {version.created_at.strftime('%Y-%m-%d %H:%M')}"
                            ),
                            P(cls="text-gray-500")(version.prompt_summary or "")
                        ),
                        Div(cls="prose max-w-none")(
                            NotStr(html_content)
                        )
                    )
                )
            )
        )

    @app.post("/artefacts/{artefact_id}/restore/{version_id}")
    def restore_version(artefact_id: int, version_id: int):
        """Restore a previous version as current."""
        db = next(get_db())

        artefact = db.query(Artefact).filter(Artefact.id == artefact_id).first()
        version = db.query(ArtefactVersion).filter(ArtefactVersion.id == version_id).first()

        if not artefact or not version:
            return Response("Not found", status_code=404)

        artefact.current_version_id = version_id
        db.commit()

        return RedirectResponse(f"/projects/{artefact.project_id}", status_code=303)

    @app.get("/artefacts/{artefact_id}/export")
    def export_artefact(artefact_id: int, format: str = "markdown"):
        """Export artefact in various formats."""
        db = next(get_db())

        artefact = db.query(Artefact).filter(Artefact.id == artefact_id).first()
        if not artefact or not artefact.current_version_id:
            return Response("Artefact not found", status_code=404)

        version = db.query(ArtefactVersion).filter(
            ArtefactVersion.id == artefact.current_version_id
        ).first()

        if not version:
            return Response("No content to export", status_code=404)

        if format == "markdown":
            return Response(
                version.content_markdown,
                media_type="text/markdown",
                headers={"Content-Disposition": f"attachment; filename={artefact.title}.md"}
            )
        elif format == "html":
            html_content = markdown.markdown(version.content_markdown, extensions=['fenced_code', 'tables'])
            return Response(
                html_content,
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename={artefact.title}.html"}
            )
        elif format == "txt":
            return Response(
                version.content_markdown,
                media_type="text/plain",
                headers={"Content-Disposition": f"attachment; filename={artefact.title}.txt"}
            )
        else:
            return Response("Invalid format", status_code=400)
