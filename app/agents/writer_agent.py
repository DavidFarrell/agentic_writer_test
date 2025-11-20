"""Writer Agent.

Per spec section 9.2, converts user's audio notes plus source materials
into a coherent first draft.

Workflow:
1. Pass 1: Create structured draft preserving user's voice
2. Pass 2: Check against notes for missing items
3. Pass 3: Check against sources for factual gaps
"""

from sqlalchemy.orm import Session
from app.models import AgentRun, ArtefactVersion
from .base_agent import BaseAgent


class WriterAgent(BaseAgent):
    """Agent for creating first drafts from notes and sources."""

    def __init__(self, model_id: str = None):
        super().__init__("writer", model_id)

    def _execute(
        self,
        db: Session,
        project_id: int,
        artefact_id: int,
        user_instruction: str,
        agent_run: AgentRun
    ) -> ArtefactVersion:
        """Execute writer agent workflow.

        Args:
            db: Database session
            project_id: Project ID
            artefact_id: Artefact ID
            user_instruction: User instruction
            agent_run: AgentRun record

        Returns:
            New ArtefactVersion
        """
        # Build context plan
        context_plan = self.context_manager.create_context_plan(
            db=db,
            project_id=project_id,
            model_id=self.model_id,
            prompt=user_instruction,
            artefact_id=artefact_id
        )

        context_string = context_plan.build_context_string()

        # Pass 1: Create initial draft
        system_prompt_1 = """You are an expert writing assistant helping to draft a blog post.

CRITICAL RULES:
- The user's audio notes reflect their intended structure and content
- Preserve their voice, intentions, and personal perspective as much as possible
- Use source materials ONLY for clarification and additional detail
- Do NOT overwrite the author's intent with generic AI language
- Maintain the author's unique voice and style
- Include specific examples, code snippets, and concrete details

Your task is to create a well-structured blog post in markdown format."""

        user_prompt_1 = f"""Based on the provided materials, create a first draft of a blog post.

User instruction: {user_instruction}

Focus on:
1. Preserving the author's voice from their notes
2. Creating a clear structure (introduction, main points, conclusion)
3. Adding detail from source materials where helpful
4. Keeping it concrete and specific, not generic

Output the complete blog post in markdown format."""

        self._log(db, agent_run.id, 0, "system", system_prompt_1)
        self._log(db, agent_run.id, 0, "user", user_prompt_1)
        self._log(db, agent_run.id, 0, "tool", f"Context plan: {context_plan.to_dict()}")

        draft, tokens_1 = self._call_llm(system_prompt_1, user_prompt_1, context_string)

        self._log(db, agent_run.id, 0, "assistant", draft, tokens_1)

        # Pass 2: Check against notes for completeness
        system_prompt_2 = """You are a careful editor checking a draft against source notes.

Your task is to:
1. Compare the draft to the user's notes
2. Identify any important points from the notes that are missing or underdeveloped
3. Update the draft to incorporate those missing elements
4. Preserve the existing quality and voice"""

        user_prompt_2 = f"""Review this draft and check if it covers all important points from the notes.

CURRENT DRAFT:
{draft}

If there are missing or underdeveloped points:
- Update the draft to include them
- Maintain consistency with the existing style

Output the updated complete blog post in markdown format."""

        self._log(db, agent_run.id, 1, "system", system_prompt_2)
        self._log(db, agent_run.id, 1, "user", user_prompt_2)

        refined_draft, tokens_2 = self._call_llm(system_prompt_2, user_prompt_2, context_string)

        self._log(db, agent_run.id, 1, "assistant", refined_draft, tokens_2)

        # Pass 3: Check against sources for accuracy
        system_prompt_3 = """You are a fact-checking editor reviewing a draft against source materials.

Your task is to:
1. Check the draft for any obvious factual gaps or misinterpretations
2. Ensure technical details align with the source materials
3. Make corrections where needed
4. Preserve the author's voice and intent"""

        user_prompt_3 = f"""Review this draft against the source materials for accuracy.

CURRENT DRAFT:
{refined_draft}

If you find factual issues or gaps:
- Correct them using information from the sources
- Maintain the author's voice and style

Output the final complete blog post in markdown format."""

        self._log(db, agent_run.id, 2, "system", system_prompt_3)
        self._log(db, agent_run.id, 2, "user", user_prompt_3)

        final_draft, tokens_3 = self._call_llm(system_prompt_3, user_prompt_3, context_string)

        self._log(db, agent_run.id, 2, "assistant", final_draft, tokens_3)

        # Create new version
        version = self._create_version(
            db=db,
            artefact_id=artefact_id,
            content=final_draft,
            prompt_summary=f"Writer agent: {user_instruction[:100]}"
        )

        return version
