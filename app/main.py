"""
Root proxy exposing FastAPI app for direct uvicorn execution:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""
from backend.app.main import app

__all__ = ["app"]
