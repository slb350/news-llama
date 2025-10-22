"""
Database session management for News Llama web application.

Provides SQLAlchemy engine, session factory, and FastAPI dependencies
with SQLite-specific optimizations (WAL mode, foreign keys enforcement).
"""
from typing import Generator
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pathlib import Path


# Database configuration
DATABASE_DIR = Path(__file__).parent.parent.parent / "data"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "news_llama.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine with connection pooling appropriate for SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Allow multi-threading
    poolclass=StaticPool,  # Reuse single connection for SQLite
    echo=False,  # Set to True for SQL debugging
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    Set SQLite pragmas for optimal performance and data integrity.

    Called automatically when a new connection is established.

    Pragmas:
    - foreign_keys=ON: Enforce foreign key constraints
    - journal_mode=WAL: Write-Ahead Logging for better concurrency
    - synchronous=NORMAL: Balance between safety and performance
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Yields a database session and ensures it's closed after use.
    Use in route functions with Depends(get_db).

    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_test_db() -> Generator[Session, None, None]:
    """
    Test database session factory.

    Creates an in-memory SQLite database for testing.
    Each test gets a fresh database with all tables created.

    Example:
        @pytest.fixture
        def db():
            yield from get_test_db()
    """
    from src.web.models import Base

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Set pragmas for test database
    @event.listens_for(test_engine, "connect")
    def set_test_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )

    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)
