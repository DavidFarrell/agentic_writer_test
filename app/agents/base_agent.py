"""Base agent class.

Per spec section 9.1, agents:
1. Build a context plan from active resources and current artefact
2. Call LLM one or more times in a loop
3. Evaluate whether another pass is needed
4. Produce a new artefact version and log all steps
"""

from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import google.generativeai as genai

from app.config import Config
from app.models import AgentRun, AgentRunLog, Artefact, ArtefactVersion
from app.services.context_manager import ContextManager
from app.services.tokenization import count_tokens


class BaseAgent:
    """Base class for all agents."""

    def __init__(self, agent_type: str, model_id: str = None):
        """Initialize agent.

        Args:
            agent_type: Type identifier (writer, style_editor, etc.)
            model_id: Model to use (defaults to config default)
        """
        self.agent_type = agent_type
        self.model_id = model_id or Config.DEFAULT_MODEL
        self.context_manager = ContextManager()

        # Configure Gemini
        genai.configure(api_key=Config.GEMINI_API_KEY)

    def run(
        self,
        db: Session,
        project_id: int,
        artefact_id: int,
        user_instruction: str = ""
    ) -> ArtefactVersion:
        """Run the agent.

        Args:
            db: Database session
            project_id: Project ID
            artefact_id: Artefact ID
            user_instruction: Optional user instruction

        Returns:
            New ArtefactVersion
        """
        # Create agent run record
        agent_run = AgentRun(
            project_id=project_id,
            artefact_id=artefact_id,
            agent_type=self.agent_type,
            status="running"
        )
        db.add(agent_run)
        db.commit()
        db.refresh(agent_run)

        try:
            # Execute agent workflow
            new_version = self._execute(db, project_id, artefact_id, user_instruction, agent_run)

            # Update agent run status
            agent_run.status = "completed"
            agent_run.completed_at = datetime.utcnow()
            db.commit()

            return new_version

        except Exception as e:
            # Mark as failed
            agent_run.status = "failed"
            agent_run.completed_at = datetime.utcnow()
            db.commit()

            # Log error
            self._log(db, agent_run.id, 0, "system", f"Error: {str(e)}")

            raise

    def _execute(
        self,
        db: Session,
        project_id: int,
        artefact_id: int,
        user_instruction: str,
        agent_run: AgentRun
    ) -> ArtefactVersion:
        """Execute agent workflow. To be implemented by subclasses.

        Args:
            db: Database session
            project_id: Project ID
            artefact_id: Artefact ID
            user_instruction: User instruction
            agent_run: AgentRun record

        Returns:
            New ArtefactVersion
        """
        raise NotImplementedError("Subclasses must implement _execute")

    def _create_version(
        self,
        db: Session,
        artefact_id: int,
        content: str,
        prompt_summary: str
    ) -> ArtefactVersion:
        """Create a new artefact version.

        Args:
            db: Database session
            artefact_id: Artefact ID
            content: Markdown content
            prompt_summary: Short description

        Returns:
            New ArtefactVersion
        """
        version = ArtefactVersion(
            artefact_id=artefact_id,
            content_markdown=content,
            created_by_agent=self.agent_type,
            prompt_summary=prompt_summary
        )
        db.add(version)
        db.commit()
        db.refresh(version)

        # Update artefact's current version
        artefact = db.query(Artefact).filter(Artefact.id == artefact_id).first()
        if artefact:
            artefact.current_version_id = version.id
            db.commit()

        return version

    def _log(
        self,
        db: Session,
        agent_run_id: int,
        iteration: int,
        role: str,
        content: str,
        tokens: Optional[int] = None
    ):
        """Log an agent interaction.

        Args:
            db: Database session
            agent_run_id: AgentRun ID
            iteration: Iteration index
            role: Role (system, user, assistant, tool)
            content: Message content
            tokens: Optional token count
        """
        log = AgentRunLog(
            agent_run_id=agent_run_id,
            iteration_index=iteration,
            role=role,
            content=content,
            tokens_used=tokens
        )
        db.add(log)
        db.commit()

        # Update iteration count
        agent_run = db.query(AgentRun).filter(AgentRun.id == agent_run_id).first()
        if agent_run and iteration >= agent_run.iteration_count:
            agent_run.iteration_count = iteration + 1
            db.commit()

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str = ""
    ) -> tuple[str, Optional[int]]:
        """Call Gemini LLM.

        Args:
            system_prompt: System instructions
            user_prompt: User prompt
            context: Optional context string

        Returns:
            Tuple of (response_text, token_count)
        """
        model = genai.GenerativeModel(
            self.model_id,
            system_instruction=system_prompt
        )

        # Build full prompt
        if context:
            full_prompt = f"{context}\n\n---\n\n{user_prompt}"
        else:
            full_prompt = user_prompt

        # Generate response
        response = model.generate_content(full_prompt)

        # Extract token usage if available
        tokens = None
        if hasattr(response, 'usage_metadata'):
            tokens = getattr(response.usage_metadata, 'total_token_count', None)

        return response.text, tokens

    def _get_current_content(self, db: Session, artefact_id: int) -> str:
        """Get current artefact content.

        Args:
            db: Database session
            artefact_id: Artefact ID

        Returns:
            Current markdown content (or empty string)
        """
        artefact = db.query(Artefact).filter(Artefact.id == artefact_id).first()
        if artefact and artefact.current_version_id:
            version = db.query(ArtefactVersion).filter(
                ArtefactVersion.id == artefact.current_version_id
            ).first()
            if version:
                return version.content_markdown
        return ""
