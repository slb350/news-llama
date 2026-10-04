"""Shared Jinja2 template renderer for the HTML routes."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
