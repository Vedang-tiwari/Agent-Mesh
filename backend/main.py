"""Application entrypoint for Uvicorn and CLI execution."""

import uvicorn

from backend.api.main import create_app
from backend.config.settings import get_settings

app = create_app()


def run() -> None:
    """Run the AgentMesh API server using configured host and port."""
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()

