"""Fact Checker Agent.

Per spec section 9.5, checks draft for factual accuracy against
provided source materials.

Workflow:
1. Cross-reference claims against sources
2. Flag unsupported or contradicted claims
3. Create annotated version with corrections
"""

from sqlalchemy.orm import Session
from app.models import AgentRun, ArtefactVersion
from .base_agent import BaseAgent


class FactCheckerAgent(BaseAgent):
    """Agent for fact-checking against source materials."""

    def __init__(self, model_id: str = None):
        super().__init__("fact_checker", model_id)

    def _execute(
        self,
        db: Session,
        project_id: int,
        artefact_id: int,
        user_instruction: str,
        agent_run: AgentRun
    ) -> ArtefactVersion:
        """Execute fact checker workflow.

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

        # Pass 1: Identify and verify factual claims
        system_prompt_1 = """You are a meticulous fact-checker.

Your task is to:
1. Identify factual claims in the blog post (numbers, technical details, named entities, etc.)
2. Cross-reference each claim against the provided source materials ONLY
3. Mark each claim as:
   - CONFIRMED: Supported by sources
   - UNSUPPORTED: Not mentioned in sources (may still be correct, just not verifiable from given sources)
   - CONTRADICTED: Sources say something different

Be precise and cite specific parts of the sources."""

        user_prompt_1 = f"""Check the factual claims in this blog post against the source materials.

BLOG POST:
{current_content}

{user_instruction}

For each claim, indicate whether it's confirmed, unsupported, or contradicted by the sources."""

        self._log(db, agent_run.id, 0, "system", system_prompt_1)
        self._log(db, agent_run.id, 0, "user", user_prompt_1)

        fact_check_report, tokens_1 = self._call_llm(system_prompt_1, user_prompt_1, context_string)

        self._log(db, agent_run.id, 0, "assistant", fact_check_report, tokens_1)

        # Pass 2: Create corrected version
        system_prompt_2 = """You are an editor correcting factual issues.

Based on the fact-check report:
1. Fix any CONTRADICTED claims using accurate information from sources
2. Add a note for UNSUPPORTED claims (e.g., "[Note: Not verified in sources]") if significant
3. Keep CONFIRMED claims as-is

Preserve the author's voice and style while ensuring accuracy."""

        user_prompt_2 = f"""Based on this fact-check report:

FACT CHECK REPORT:
{fact_check_report}

Update this blog post to correct any factual issues:

BLOG POST:
{current_content}

Output the complete corrected blog post in markdown format.

Also append a "Fact Check Summary" section at the end listing any corrections made."""

        self._log(db, agent_run.id, 1, "system", system_prompt_2)
        self._log(db, agent_run.id, 1, "user", user_prompt_2)

        corrected_draft, tokens_2 = self._call_llm(system_prompt_2, user_prompt_2, context_string)

        self._log(db, agent_run.id, 1, "assistant", corrected_draft, tokens_2)

        # Create new version
        version = self._create_version(
            db=db,
            artefact_id=artefact_id,
            content=corrected_draft,
            prompt_summary=f"Fact checker: Verified against sources"
        )

        return version
