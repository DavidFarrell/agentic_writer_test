"""Tests for database models."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.project import Project
from app.models.resource import Resource
from app.models.artefact import Artefact, ArtefactVersion


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_project(db_session):
    """Test creating a project."""
    project = Project(
        name="Test Project",
        description="A test project",
        default_model_id="gemini-2.0-flash-exp"
    )
    db_session.add(project)
    db_session.commit()

    assert project.id is not None
    assert project.name == "Test Project"


def test_create_resource(db_session):
    """Test creating a resource."""
    project = Project(name="Test", default_model_id="gemini-2.0-flash-exp")
    db_session.add(project)
    db_session.commit()

    resource = Resource(
        project_id=project.id,
        label="Test Resource",
        type="audio_notes",
        origin="file_upload",
        total_tokens=100,
        model_id="gemini-2.0-flash-exp",
        active=True
    )
    db_session.add(resource)
    db_session.commit()

    assert resource.id is not None
    assert resource.project_id == project.id


def test_create_artefact(db_session):
    """Test creating an artefact."""
    project = Project(name="Test", default_model_id="gemini-2.0-flash-exp")
    db_session.add(project)
    db_session.commit()

    artefact = Artefact(
        project_id=project.id,
        title="Test Artefact"
    )
    db_session.add(artefact)
    db_session.commit()

    assert artefact.id is not None
    assert artefact.project_id == project.id


def test_create_artefact_version(db_session):
    """Test creating an artefact version."""
    project = Project(name="Test", default_model_id="gemini-2.0-flash-exp")
    db_session.add(project)
    db_session.commit()

    artefact = Artefact(project_id=project.id, title="Test")
    db_session.add(artefact)
    db_session.commit()

    version = ArtefactVersion(
        artefact_id=artefact.id,
        content_markdown="# Test\n\nThis is a test.",
        created_by_agent="writer",
        prompt_summary="Test version"
    )
    db_session.add(version)
    db_session.commit()

    assert version.id is not None
    assert version.artefact_id == artefact.id
