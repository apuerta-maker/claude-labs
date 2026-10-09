"""FastAPI application factory."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build the app. A factory lets tests create isolated instances."""
    app = FastAPI(title="Lab01 Invoice Extraction API")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
