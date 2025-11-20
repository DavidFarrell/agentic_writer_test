"""Style Editor Agent.

Per spec section 9.3, adjusts draft to match user's established writing style
while avoiding generic AI voice.

Workflow:
1. Pre-pass: Create style profile from blog corpus (optional, cached)
2. Style pass: Rewrite to match style profile
3. Reflection pass: Check for content loss
"""

from sqlalchemy.orm import Session
from app.models import AgentRun, ArtefactVersion
from .base_agent import BaseAgent


class StyleEditorAgent(BaseAgent):
    """Agent for adjusting writing style."""

    def __init__(self, model_id: str = None):
        super().__init__("style_editor", model_id)

    def _execute(
        self,
        db: Session,
        project_id: int,
        artefact_id: int,
        user_instruction: str,
        agent_run: AgentRun
    ) -> ArtefactVersion:
        """Execute style editor workflow.

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

        # Pass 1: Create style profile from corpus
        system_prompt_1 = """You are an expert writing analyst.

Your task is to analyze example blog posts and create a concise style profile.

Focus on:
- Tone (formal/casual, technical/accessible, etc.)
- Sentence structure and length
- Common phrases or expressions
- Use of examples and code
- Personal voice and quirks
- Things to avoid (clichés, overly formal language, etc.)

Output a compact style guide (300-500 words)."""

        user_prompt_1 = """Based on the provided blog corpus, create a style profile that captures the author's unique voice and writing patterns."""

        self._log(db, agent_run.id, 0, "system", system_prompt_1)
        self._log(db, agent_run.id, 0, "user", user_prompt_1)

        style_profile, tokens_1 = self._call_llm(system_prompt_1, user_prompt_1, context_string)

        self._log(db, agent_run.id, 0, "assistant", style_profile, tokens_1)

        # Pass 2: Apply style to current draft
        system_prompt_2 = f"""You are a skilled editor adjusting a blog post to match the author's established style.

STYLE PROFILE:
{style_profile}

CRITICAL RULES:
- Rewrite ONLY where necessary to match the style
- Do NOT remove specific details, examples, or code snippets
- Do NOT remove personal anecdotes or idiosyncratic phrasing
- Preserve all factual content and technical accuracy
- Avoid generic "AI voice" - maintain the human author's personality"""

        user_prompt_2 = f"""Adjust this draft to better match the style profile.

CURRENT DRAFT:
{current_content}

{user_instruction}

Output the complete styled blog post in markdown format."""

        self._log(db, agent_run.id, 1, "system", system_prompt_2)
        self._log(db, agent_run.id, 1, "user", user_prompt_2)

        styled_draft, tokens_2 = self._call_llm(system_prompt_2, user_prompt_2)

        self._log(db, agent_run.id, 1, "assistant", styled_draft, tokens_2)

        # Pass 3: Reflection - check for content loss
        system_prompt_3 = """You are a careful reviewer comparing two versions of a blog post.

Your task is to:
1. List the main style changes made
2. Check if any important content was lost
3. If content was lost, restore it
4. Output the final version"""

        user_prompt_3 = f"""Compare the original and styled versions.

ORIGINAL:
{current_content}

STYLED:
{styled_draft}

Check:
1. Are style changes appropriate?
2. Was any important content removed?

If content was lost, restore it. Output the final complete blog post in markdown format."""

        self._log(db, agent_run.id, 2, "system", system_prompt_3)
        self._log(db, agent_run.id, 2, "user", user_prompt_3)

        final_draft, tokens_3 = self._call_llm(system_prompt_3, user_prompt_3)

        self._log(db, agent_run.id, 2, "assistant", final_draft, tokens_3)

        # Create new version
        version = self._create_version(
            db=db,
            artefact_id=artefact_id,
            content=final_draft,
            prompt_summary=f"Style editor: Matched to author's style"
        )

        return version
