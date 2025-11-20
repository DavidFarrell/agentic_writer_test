"""Context management service.

Per spec section 6.3, handles:
- Collecting active resources for a project
- Managing token budgets
- Creating context plans for LLM calls with prioritization
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Resource, Artefact
from app.services.tokenization import count_tokens, max_context_tokens


class ContextPlan:
    """Represents a plan for including resources in context."""

    def __init__(self, model_id: str, max_tokens: int):
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.included_resources: List[Dict[str, Any]] = []
        self.total_tokens = 0
        self.artefact_tokens = 0
        self.prompt_tokens = 0

    def add_resource(self, resource_id: int, label: str, content: str, tokens: int, priority: int):
        """Add a resource to the context plan.

        Args:
            resource_id: Resource ID
            label: Resource label
            content: Text content
            tokens: Token count
            priority: Priority level (lower is higher priority)
        """
        self.included_resources.append({
            "resource_id": resource_id,
            "label": label,
            "content": content,
            "tokens": tokens,
            "priority": priority
        })
        self.total_tokens += tokens

    def set_artefact(self, content: str, tokens: int):
        """Set artefact content and token count.

        Args:
            content: Artefact markdown content
            tokens: Token count
        """
        self.artefact_tokens = tokens
        self.total_tokens += tokens

    def set_prompt(self, prompt: str, tokens: int):
        """Set prompt content and token count.

        Args:
            prompt: Prompt text
            tokens: Token count
        """
        self.prompt_tokens = tokens
        self.total_tokens += tokens

    def get_remaining_tokens(self) -> int:
        """Get remaining tokens in budget.

        Returns:
            Remaining token count
        """
        return self.max_tokens - self.total_tokens

    def build_context_string(self) -> str:
        """Build the full context string for LLM.

        Returns:
            Formatted context string
        """
        parts = []

        # Add resources in priority order
        sorted_resources = sorted(self.included_resources, key=lambda x: x['priority'])

        for res in sorted_resources:
            parts.append(f"## {res['label']}\n\n{res['content']}\n")

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging.

        Returns:
            Dictionary representation
        """
        return {
            "model_id": self.model_id,
            "max_tokens": self.max_tokens,
            "total_tokens": self.total_tokens,
            "artefact_tokens": self.artefact_tokens,
            "prompt_tokens": self.prompt_tokens,
            "remaining_tokens": self.get_remaining_tokens(),
            "included_resources": [
                {
                    "resource_id": r["resource_id"],
                    "label": r["label"],
                    "tokens": r["tokens"],
                    "priority": r["priority"]
                }
                for r in self.included_resources
            ]
        }


class ContextManager:
    """Service for managing context selection and token budgets."""

    PRIORITY_MAP = {
        "audio_notes": 1,  # Highest priority
        "source_transcript": 2,
        "article": 2,
        "book": 2,
        "blog_corpus": 3,  # Style corpus
        "other": 4
    }

    def create_context_plan(
        self,
        db: Session,
        project_id: int,
        model_id: str,
        prompt: str = "",
        artefact_id: Optional[int] = None,
        reserve_tokens: int = 2000  # Reserve for response
    ) -> ContextPlan:
        """Create a context plan for an LLM call.

        Per spec section 6.3, prioritizes:
        1. User's audio notes and current artefact
        2. Source materials
        3. Style corpus

        Args:
            db: Database session
            project_id: Project ID
            model_id: Model ID
            prompt: User prompt
            artefact_id: Optional artefact ID
            reserve_tokens: Tokens to reserve for response

        Returns:
            ContextPlan object
        """
        max_tokens = max_context_tokens(model_id)
        plan = ContextPlan(model_id, max_tokens - reserve_tokens)

        # Add prompt
        if prompt:
            prompt_tokens = count_tokens(prompt, model_id)
            plan.set_prompt(prompt, prompt_tokens)

        # Add current artefact if specified
        if artefact_id:
            artefact = db.query(Artefact).filter(Artefact.id == artefact_id).first()
            if artefact and artefact.current_version_id:
                from app.models import ArtefactVersion
                version = db.query(ArtefactVersion).filter(
                    ArtefactVersion.id == artefact.current_version_id
                ).first()
                if version:
                    artefact_tokens = count_tokens(version.content_markdown, model_id)
                    plan.set_artefact(version.content_markdown, artefact_tokens)

        # Get all active resources for project
        resources = db.query(Resource).filter(
            Resource.project_id == project_id,
            Resource.active == True
        ).all()

        # Sort by priority (type-based)
        resources_with_priority = []
        for resource in resources:
            priority = self.PRIORITY_MAP.get(resource.type, 4)
            resources_with_priority.append((resource, priority))

        resources_with_priority.sort(key=lambda x: x[1])

        # Add resources while we have budget
        for resource, priority in resources_with_priority:
            if resource.text_content:
                resource_tokens = count_tokens(resource.text_content, model_id)

                # Check if we have budget
                if plan.get_remaining_tokens() >= resource_tokens:
                    plan.add_resource(
                        resource_id=resource.id,
                        label=resource.label,
                        content=resource.text_content,
                        tokens=resource_tokens,
                        priority=priority
                    )
                else:
                    # Try to include a summary or partial content
                    available = plan.get_remaining_tokens()
                    if available > 500:  # Only if meaningful space
                        # Take first portion of content
                        # Rough estimate: 4 chars per token
                        char_limit = available * 4
                        truncated = resource.text_content[:char_limit]
                        truncated_tokens = count_tokens(truncated, model_id)

                        plan.add_resource(
                            resource_id=resource.id,
                            label=f"{resource.label} (truncated)",
                            content=truncated + "\n\n[Content truncated due to token limit]",
                            tokens=truncated_tokens,
                            priority=priority
                        )

        return plan

    def get_active_resources(self, db: Session, project_id: int) -> List[Resource]:
        """Get all active resources for a project.

        Args:
            db: Database session
            project_id: Project ID

        Returns:
            List of active Resource objects
        """
        return db.query(Resource).filter(
            Resource.project_id == project_id,
            Resource.active == True
        ).all()

    def toggle_resource(self, db: Session, resource_id: int) -> bool:
        """Toggle a resource's active state.

        Args:
            db: Database session
            resource_id: Resource ID

        Returns:
            New active state
        """
        resource = db.query(Resource).filter(Resource.id == resource_id).first()
        if resource:
            resource.active = not resource.active
            db.commit()
            return resource.active
        return False

    def get_token_summary(
        self,
        db: Session,
        project_id: int,
        model_id: str
    ) -> Dict[str, Any]:
        """Get summary of token usage for a project.

        Args:
            db: Database session
            project_id: Project ID
            model_id: Model ID

        Returns:
            Dictionary with token usage summary
        """
        resources = db.query(Resource).filter(
            Resource.project_id == project_id
        ).all()

        total_tokens = 0
        active_tokens = 0
        resource_breakdown = []

        for resource in resources:
            tokens = resource.total_tokens
            total_tokens += tokens

            if resource.active:
                active_tokens += tokens

            resource_breakdown.append({
                "id": resource.id,
                "label": resource.label,
                "type": resource.type,
                "tokens": tokens,
                "active": resource.active
            })

        max_tokens = max_context_tokens(model_id)

        return {
            "model_id": model_id,
            "max_tokens": max_tokens,
            "total_tokens": total_tokens,
            "active_tokens": active_tokens,
            "utilization": active_tokens / max_tokens if max_tokens > 0 else 0,
            "resources": resource_breakdown
        }
