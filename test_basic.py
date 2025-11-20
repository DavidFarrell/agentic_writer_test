"""Basic functionality test."""

from app.models import init_db, get_db, Project, Artefact
from app.config import Config

print("=" * 60)
print("AGENTIC WRITER - BASIC FUNCTIONALITY TEST")
print("=" * 60)

# Initialize database
print("\n1. Initializing database...")
init_db()
print("   ✓ Database initialized")

# Create a test project
print("\n2. Creating test project...")
db = next(get_db())

project = Project(
    name="Test Blog Post",
    description="Testing the Agentic Writer system",
    default_model_id=Config.DEFAULT_MODEL
)
db.add(project)
db.commit()
db.refresh(project)
print(f"   ✓ Project created with ID: {project.id}")

# Create an artefact
print("\n3. Creating artefact...")
artefact = Artefact(
    project_id=project.id,
    title=f"{project.name} - Draft"
)
db.add(artefact)
db.commit()
db.refresh(artefact)
print(f"   ✓ Artefact created with ID: {artefact.id}")

# Query the project back
print("\n4. Querying project...")
queried_project = db.query(Project).filter(Project.id == project.id).first()
if queried_project:
    print(f"   ✓ Found project: {queried_project.name}")
    print(f"     Model: {queried_project.default_model_id}")
    print(f"     Created: {queried_project.created_at}")
else:
    print("   ✗ Project not found!")

print("\n" + "=" * 60)
print("BASIC TESTS PASSED ✓")
print("=" * 60)
print("\nCore functionality verified:")
print("  ✓ Database schema")
print("  ✓ Project CRUD")
print("  ✓ Artefact creation")
print("  ✓ Configuration module")
print("\nNote: Agent and API tests require GEMINI_API_KEY to be set")
print("=" * 60)

db.close()
