"""Vercel Serverless ASGI entrypoint for NetBill Assist FastAPI application."""

import sys
from pathlib import Path

# Add project root to sys.path so 'app' imports resolve cleanly on Vercel
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app  # noqa: E402
