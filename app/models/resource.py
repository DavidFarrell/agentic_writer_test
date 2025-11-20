"""Resource models."""

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Resource(Base):
    """Resource entity.

    Per spec section 5.2, represents a logical item the user has added:
    - id
    - project_id
    - label: user-facing name
    - type: enum (audio_notes, source_transcript, article, book, blog_corpus, other)
    - origin: enum (file_upload, url, youtube, manual)
    - raw_path: filesystem path for stored original file
    - url: original URL if applicable
    - total_tokens: token count for the full resource
    - active: whether currently included in context
    """

    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    label = Column(String, nullable=False)
    type = Column(String, nullable=False)  # audio_notes, source_transcript, article, etc.
    origin = Column(String, nullable=False)  # file_upload, url, youtube, manual
    raw_path = Column(String, nullable=True)
    url = Column(String, nullable=True)
    total_tokens = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    model_id = Column(String, nullable=False)  # Model used for tokenization
    created_at = Column(DateTime, default=datetime.utcnow)
    text_content = Column(Text, nullable=True)  # Extracted text content

    # Relationships
    chunks = relationship("ResourceChunk", back_populates="resource", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Resource(id={self.id}, label='{self.label}', type='{self.type}')>"


class ResourceChunk(Base):
    """Resource chunk for oversized resources.

    Per spec section 5.3, for resources exceeding context window:
    - id
    - resource_id
    - sequence_index
    - text: chunk text
    - token_count
    """

    __tablename__ = "resource_chunks"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    sequence_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)

    # Relationships
    resource = relationship("Resource", back_populates="chunks")

    def __repr__(self):
        return f"<ResourceChunk(id={self.id}, resource_id={self.resource_id}, index={self.sequence_index})>"
