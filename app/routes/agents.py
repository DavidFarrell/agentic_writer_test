"""Agent execution and monitoring routes."""

from fasthtml.common import *
from sqlalchemy.orm import Session
from app.models import get_db, Project, Artefact, AgentRun, AgentRunLog
from app.agents import WriterAgent, StyleEditorAgent, DetailEditorAgent, FactCheckerAgent


def create_agent_routes(app):
    """Create agent-related routes."""

    @app.post("/projects/{project_id}/agents/run")
    async def run_agent(
        project_id: int,
        agent_type: str,
        instruction: str,
        artefact_id: int
    ):
        """Run an agent."""
        db = next(get_db())

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return Response("Project not found", status_code=404)

        # Get or create artefact
        artefact = db.query(Artefact).filter(Artefact.id == artefact_id).first()
        if not artefact:
            artefact = Artefact(
                project_id=project_id,
                title=f"{project.name} - Draft"
            )
            db.add(artefact)
            db.commit()
            db.refresh(artefact)

        # Select agent
        agent_map = {
            "writer": WriterAgent,
            "style_editor": StyleEditorAgent,
            "detail_editor": DetailEditorAgent,
            "fact_checker": FactCheckerAgent
        }

        if agent_type not in agent_map:
            return Response("Invalid agent type", status_code=400)

        try:
            agent = agent_map[agent_type](model_id=project.default_model_id)
            version = agent.run(
                db=db,
                project_id=project_id,
                artefact_id=artefact.id,
                user_instruction=instruction
            )

            return RedirectResponse(f"/projects/{project_id}", status_code=303)

        except Exception as e:
            return Response(f"Agent execution failed: {str(e)}", status_code=500)

    @app.get("/projects/{project_id}/agents")
    def view_agent_runs(project_id: int):
        """View agent run history."""
        db = next(get_db())

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return Response("Project not found", status_code=404)

        agent_runs = db.query(AgentRun).filter(
            AgentRun.project_id == project_id
        ).order_by(AgentRun.started_at.desc()).all()

        return Html(
            Head(
                Title("Agent Runs - Agentic Writer"),
                Script(src="https://cdn.tailwindcss.com"),
            ),
            Body(cls="bg-gray-50 min-h-screen")(
                Div(cls="container mx-auto px-4 py-8 max-w-6xl")(
                    H1(cls="text-3xl font-bold mb-6")("Agent Run History"),
                    A(
                        "← Back to Project",
                        href=f"/projects/{project_id}",
                        cls="text-blue-600 hover:underline mb-4 inline-block"
                    ),
                    Div(cls="space-y-4")(
                        *[
                            Div(cls="bg-white p-6 rounded-lg shadow")(
                                Div(cls="flex justify-between items-start mb-4")(
                                    Div()(
                                        H3(cls="text-lg font-semibold capitalize")(
                                            run.agent_type.replace('_', ' ')
                                        ),
                                        P(cls="text-sm text-gray-600")(
                                            f"Status: {run.status} | Iterations: {run.iteration_count}"
                                        ),
                                        P(cls="text-sm text-gray-500")(
                                            f"Started: {run.started_at.strftime('%Y-%m-%d %H:%M')}"
                                        )
                                    ),
                                    A(
                                        "View Logs",
                                        href=f"/agents/runs/{run.id}/logs",
                                        cls="bg-blue-600 text-white px-3 py-1 text-sm rounded hover:bg-blue-700"
                                    )
                                )
                            )
                            for run in agent_runs
                        ] if agent_runs else [
                            P(cls="text-gray-500")("No agent runs yet")
                        ]
                    )
                )
            )
        )

    @app.get("/agents/runs/{run_id}/logs")
    def view_agent_logs(run_id: int):
        """View detailed logs for an agent run."""
        db = next(get_db())

        agent_run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not agent_run:
            return Response("Agent run not found", status_code=404)

        logs = db.query(AgentRunLog).filter(
            AgentRunLog.agent_run_id == run_id
        ).order_by(AgentRunLog.iteration_index, AgentRunLog.created_at).all()

        # Group by iteration
        iterations = {}
        for log in logs:
            if log.iteration_index not in iterations:
                iterations[log.iteration_index] = []
            iterations[log.iteration_index].append(log)

        return Html(
            Head(
                Title("Agent Logs - Agentic Writer"),
                Script(src="https://cdn.tailwindcss.com"),
            ),
            Body(cls="bg-gray-50 min-h-screen")(
                Div(cls="container mx-auto px-4 py-8 max-w-6xl")(
                    H1(cls="text-3xl font-bold mb-6")(f"Agent Run Logs: {agent_run.agent_type.replace('_', ' ').title()}"),
                    A(
                        "← Back to Agent Runs",
                        href=f"/projects/{agent_run.project_id}/agents",
                        cls="text-blue-600 hover:underline mb-4 inline-block"
                    ),
                    Div(cls="mb-6 p-4 bg-white rounded-lg shadow")(
                        P(cls="text-sm")(f"Status: {agent_run.status}"),
                        P(cls="text-sm")(f"Iterations: {agent_run.iteration_count}"),
                        P(cls="text-sm")(f"Started: {agent_run.started_at.strftime('%Y-%m-%d %H:%M')}"),
                        P(cls="text-sm")(
                            f"Completed: {agent_run.completed_at.strftime('%Y-%m-%d %H:%M')}"
                            if agent_run.completed_at else "Running..."
                        )
                    ),
                    Div(cls="space-y-6")(
                        *[
                            Div()(
                                H2(cls="text-xl font-bold mb-4")(f"Iteration {iteration_idx}"),
                                Div(cls="space-y-2")(
                                    *[
                                        Div(
                                            cls=f"p-4 rounded-lg {'bg-blue-50' if log.role == 'system' else 'bg-green-50' if log.role == 'user' else 'bg-gray-50' if log.role == 'tool' else 'bg-yellow-50'}"
                                        )(
                                            Div(cls="flex justify-between items-start mb-2")(
                                                P(cls="font-semibold uppercase text-sm")(log.role),
                                                P(cls="text-xs text-gray-500")(
                                                    f"{log.tokens_used} tokens" if log.tokens_used else ""
                                                )
                                            ),
                                            Pre(cls="whitespace-pre-wrap text-sm font-mono")(
                                                log.content[:1000] + ("..." if len(log.content) > 1000 else "")
                                            )
                                        )
                                        for log in iteration_logs
                                    ]
                                )
                            )
                            for iteration_idx, iteration_logs in sorted(iterations.items())
                        ]
                    )
                )
            )
        )
