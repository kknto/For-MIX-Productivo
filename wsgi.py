from pathlib import Path

from app import create_app


app = create_app(base_dir=Path(__file__).resolve().parent)
