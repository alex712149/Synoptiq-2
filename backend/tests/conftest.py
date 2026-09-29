import os
import sys
import pathlib

os.environ.setdefault("SYNOPTIQ_MODE", "real")
os.environ.setdefault("SYNOPTIQ_DATABASE_ROLE", "TRAINING")
os.environ.setdefault("TRAINING_DATABASE_URL", "sqlite:///./data/real/training.sqlite3")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:password@host:5432/synoptiq")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
