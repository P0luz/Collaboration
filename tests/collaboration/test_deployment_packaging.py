"""Deployment packaging checks for the M8 handoff path."""

from pathlib import Path


def test_dockerfile_runs_collaboration_api_on_port_8080():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.10-slim" in dockerfile
    assert "COPY requirements.txt" in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert (
        'CMD ["uvicorn", "backend.collaboration.app:app", "--host", "0.0.0.0", "--port", "8080"]'
        in dockerfile
    )


def test_compose_file_defines_collaboration_service_and_healthcheck():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "collaboration:" in compose
    assert "build: ." in compose
    assert '"8080:8080"' in compose
    assert "COLLABORATION_ROOM" in compose
    assert "healthcheck:" in compose
    assert "http://localhost:8080/" in compose


def test_dockerignore_excludes_local_and_generated_files():
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8").splitlines()

    assert ".git" in dockerignore
    assert ".pytest_cache" in dockerignore
    assert "__pycache__" in dockerignore
    assert "docs/collaboration/secret" in dockerignore


def test_deployment_doc_links_readiness_and_smoke_commands():
    doc = Path("docs/collaboration/DEPLOYMENT.md").read_text(encoding="utf-8")

    assert "docker compose up --build" in doc
    assert "readiness_check.py --with-pytest --json" in doc
    assert "self_hosted_smoke.py" in doc
