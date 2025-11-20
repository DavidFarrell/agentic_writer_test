"""Artefact models."""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Artefact(Base):
    """Artefact entity.

    Per spec section 5.4, represents the current working document:
    - id
    - project_id
    - title
    - current_version_id
    """

    __tablename__ = "artefacts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    current_version_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    versions = relationship("ArtefactVersion", back_populates="artefact", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Artefact(id={self.id}, title='{self.title}')>"


class ArtefactVersion(Base):
    """Artefact version entity.

    Per spec section 5.5:
    - id
    - artefact_id
    - created_at
    - created_by_agent: nullable (writer, style_editor, detail_editor, fact_checker, user)
    - prompt_summary: short description
    - content_markdown: full markdown content
    """

    __tablename__ = "artefact_versions"

    id = Column(Integer, primary_key=True, index=True)
    artefact_id = Column(Integer, ForeignKey("artefacts.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_agent = Column(String, nullable=True)  # writer, style_editor, user, etc.
    prompt_summary = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=False)

    # Relationships
    artefact = relationship("Artefact", back_populates="versions")

    def __repr__(self):
        return f"<ArtefactVersion(id={self.id}, artefact_id={self.artefact_id}, by={self.created_by_agent})>"
