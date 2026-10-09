"""Entrypoint: Vercel and uvicorn look for a FastAPI instance named `app` here."""

from lab01_invoice_extraction.api.app import create_app

app = create_app()
