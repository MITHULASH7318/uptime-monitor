import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Default to a local sqlite file inside a mounted /app/data folder
# so the data survives container restarts.
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./data/monitor.db")

# check_same_thread=False because the scheduler runs pings on a
# background thread separate from the FastAPI request thread.
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
