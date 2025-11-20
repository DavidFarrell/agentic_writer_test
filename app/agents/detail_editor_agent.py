"""Detail Editor Agent.

Per spec section 9.4, ensures the post is sufficiently detailed and concrete
relative to source material and previous posts.

Workflow:
1. Identify vague or hand-wavy areas
2. Suggest where additional detail is needed
3. Apply improvements
"""

from sqlalchemy.orm import Session
from app.models import AgentRun, ArtefactVersion
from .base_agent import BaseAgent


class DetailEditorAgent(BaseAgent):
    """Agent for improving detail and concreteness."""

    def __init__(self, model_id: str = None):
        super().__init__("detail_editor", model_id)

    def _execute(
        self,
        db: Session,
        project_id: int,
        artefact_id: int,
        user_instruction: str,
        agent_run: AgentRun
    ) -> ArtefactVersion:
        """Execute detail editor workflow.

        Args:
            db: Database session
            project_id: Project ID
            artefact_id: Artefact ID
            user_instruction: User instruction
            agent_run: AgentRun record

        Returns:
            New ArtefactVersion
        """
        # Get current content
        current_content = self._get_current_content(db, artefact_id)

        # Build context plan
        context_plan = self.context_manager.create_context_plan(
            db=db,
            project_id=project_id,
            model_id=self.model_id,
            prompt=user_instruction,
            artefact_id=artefact_id
        )

        context_string = context_plan.build_context_string()

        # Pass 1: Identify areas needing more detail
        system_prompt_1 = """You are an expert technical editor focused on clarity and detail.

Your task is to analyze a blog post and identify areas that are:
- Too vague or abstract
- Missing concrete examples
- Lacking code snippets where helpful
- Missing important clarifications or explanations

Be specific about what's missing and where."""

        user_prompt_1 = f"""Review this blog post and identify areas needing more detail.

CURRENT DRAFT:
{current_content}

{user_instruction}

List specific sections or paragraphs that need improvement, and suggest what kind of detail to add (examples, code, clarification, etc.)."""

        self._log(db, agent_run.id, 0, "system", system_prompt_1)
        self._log(db, agent_run.id, 0, "user", user_prompt_1)

        analysis, tokens_1 = self._call_llm(system_prompt_1, user_prompt_1, context_string)

        self._log(db, agent_run.id, 0, "assistant", analysis, tokens_1)

        # Pass 2: Apply improvements
        system_prompt_2 = """You are an expert technical editor improving a blog post.

Based on the analysis of what's missing, enhance the post with:
- Concrete examples
- Code snippets where appropriate
- Clear explanations
- Specific details from the source materials

IMPORTANT:
- Maintain the author's voice
- Add detail without making the post unnecessarily long
- Keep the improvements focused and relevant"""

        user_prompt_2 = f"""Based on this analysis of needed improvements:

ANALYSIS:
{analysis}

Update this draft:

CURRENT DRAFT:
{current_content}

Output the complete improved blog post in markdown format."""

        self._log(db, agent_run.id, 1, "system", system_prompt_2)
        self._log(db, agent_run.id, 1, "user", user_prompt_2)

        improved_draft, tokens_2 = self._call_llm(system_prompt_2, user_prompt_2, context_string)

        self._log(db, agent_run.id, 1, "assistant", improved_draft, tokens_2)

        # Create new version
        version = self._create_version(
            db=db,
            artefact_id=artefact_id,
            content=improved_draft,
            prompt_summary=f"Detail editor: Added concrete details and examples"
        )

        return version
