"""Load .env file at import time so all modules see the variables."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass
