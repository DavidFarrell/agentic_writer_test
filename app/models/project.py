"""Project model."""

from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from .base import Base


class Project(Base):
    """Project entity.

    Per spec section 5.1, represents a writing project with:
    - id: unique identifier
    - name: string
    - created_at, updated_at
    - default_model_id: reference to a model configuration
    - description: optional
    """

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    default_model_id = Column(String, nullable=False, default="gemini-2.0-flash-exp")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"
