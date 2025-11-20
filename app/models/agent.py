"""Agent run models."""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class AgentRun(Base):
    """Agent run entity.

    Per spec section 5.6:
    - id
    - project_id
    - artefact_id
    - agent_type (writer, style_editor, detail_editor, fact_checker)
    - started_at, completed_at
    - status: running, completed, failed
    - iteration_count: how many passes
    """

    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    artefact_id = Column(Integer, ForeignKey("artefacts.id"), nullable=True)
    agent_type = Column(String, nullable=False)  # writer, style_editor, etc.
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="running")  # running, completed, failed
    iteration_count = Column(Integer, default=0)

    # Relationships
    logs = relationship("AgentRunLog", back_populates="agent_run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AgentRun(id={self.id}, type='{self.agent_type}', status='{self.status}')>"


class AgentRunLog(Base):
    """Agent run log entity.

    Per spec section 5.6:
    - id
    - agent_run_id
    - iteration_index
    - role: system, user, assistant, tool
    - content: text exchanged
    - tokens_used (if available)
    """

    __tablename__ = "agent_run_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False)
    iteration_index = Column(Integer, nullable=False)
    role = Column(String, nullable=False)  # system, user, assistant, tool
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    agent_run = relationship("AgentRun", back_populates="logs")

    def __repr__(self):
        return f"<AgentRunLog(id={self.id}, run_id={self.agent_run_id}, role='{self.role}')>"
