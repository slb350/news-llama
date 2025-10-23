# News Llama Web Application Architecture

Technical architecture documentation for the News Llama web application.

## Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Patterns](#architecture-patterns)
4. [Data Layer](#data-layer)
5. [Service Layer](#service-layer)
6. [API Layer](#api-layer)
7. [Background Jobs](#background-jobs)
8. [Performance Optimizations](#performance-optimizations)
9. [Error Handling](#error-handling)
10. [Security](#security)
11. [Testing Strategy](#testing-strategy)
12. [Deployment Architecture](#deployment-architecture)

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Browser                       │
│                     (HTML, CSS, JavaScript)                  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Nginx (Reverse Proxy)                   │
│              SSL Termination, Static Files, Caching          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Routes     │  │   Services   │  │   Models     │      │
│  │   (API)      │◄─┤   (Logic)    │◄─┤ (SQLAlchemy) │      │
│  └──────────────┘  └──────────────┘  └──────┬───────┘      │
│                                               │              │
│  ┌──────────────┐  ┌──────────────┐         │              │
│  │  Scheduler   │  │Rate Limiter  │         │              │
│  │ (APScheduler)│  │ (In-Memory)  │         │              │
│  └──────────────┘  └──────────────┘         │              │
└───────────────────────────────────────────┬──┼──────────────┘
                                            │  │
                         ┌──────────────────┘  │
                         ▼                      ▼
              ┌──────────────────┐   ┌──────────────────┐
              │  NewsLlama CLI   │   │  SQLite Database │
              │   (Generation)   │   │  (WAL Mode)      │
              └──────────────────┘   └──────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  Output HTML     │
              │  (Newsletters)   │
              └──────────────────┘
```

### Key Components

1. **Web Interface**: FastAPI-based REST API with Jinja2 templates
2. **Database**: SQLite with SQLAlchemy ORM (WAL mode for concurrency)
3. **Scheduler**: APScheduler for daily newsletter generation
4. **Generation Engine**: Reuses CLI NewsLlama class for content aggregation
5. **Reverse Proxy**: Nginx for SSL, static files, and load balancing

### Request Flow

**User Creates Profile:**
```
Browser → POST /profile/create → UserService.create_user()
    → InterestService.add_user_interest() (N times)
    → GenerationService.queue_newsletter_generation()
    → SchedulerService.queue_immediate_generation()
    → [Background] NewsLlama.run() → HTML output
```

**Daily Scheduled Generation:**
```
APScheduler (6 AM) → SchedulerService.generate_daily_newsletters()
    → For each user: GenerationService.queue_newsletter_generation()
    → [Background] NewsLlama.run() → HTML output
    → Database status updated (pending → generating → completed/failed)
```

**User Views Newsletter:**
```
Browser → GET /newsletters/{guid} → NewsletterService.get_newsletter_by_guid()
    → Check status → If completed: FileCache.read_newsletter_file()
    → Return HTML (cached or from disk)
```

## Technology Stack

### Core Framework

- **FastAPI 0.109+**: Modern async web framework
  - Native async/await support
  - Automatic OpenAPI documentation
  - Pydantic integration for validation
  - Dependency injection system

### Database

- **SQLite 3.x**: Lightweight, serverless database
  - Single-file database (news_llama.db)
  - WAL (Write-Ahead Logging) mode for concurrency
  - Suitable for 1-100 users per instance

- **SQLAlchemy 2.0+**: ORM and database toolkit
  - Declarative models with type hints
  - Relationship management (User ↔ UserInterests, User ↔ Newsletters)
  - Query builder with eager loading support

- **Alembic**: Database migration management
  - Version-controlled schema changes
  - Upgrade/downgrade support
  - Duplicate-safe index creation

### Background Processing

- **APScheduler 3.10+**: Background job scheduling
  - CronTrigger for daily generation (6 AM default)
  - ThreadPoolExecutor for async job execution
  - Job persistence and monitoring

### Template Engine

- **Jinja2**: HTML template rendering
  - Template inheritance (base.html)
  - Macros for reusable components
  - Auto-escaping for security

### Validation & Configuration

- **Pydantic 2.x**: Data validation and settings
  - Request/response schema validation
  - Environment variable parsing
  - Type checking at runtime

### Testing

- **Pytest**: Testing framework
  - Fixture-based test setup
  - Parametrized tests
  - Coverage reporting (pytest-cov)

### Performance

- **functools.lru_cache**: In-memory caching
  - Newsletter HTML file caching (100 files max)
  - O(1) lookups for frequently accessed newsletters

### Server

- **Uvicorn**: ASGI server
  - Multiple workers for concurrency
  - Fast HTTP/1.1 and HTTP/2 support
  - Graceful shutdown handling

## Architecture Patterns

### Layered Architecture

```
┌─────────────────────────────────────────────┐
│           Presentation Layer                │  Routes (app.py)
│  - HTTP endpoints                           │  Templates (Jinja2)
│  - Request/response handling                │
│  - Template rendering                       │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│            Business Logic Layer             │  Services (services/*.py)
│  - User management (user_service)           │
│  - Interest management (interest_service)   │
│  - Newsletter orchestration (generation)    │
│  - NewsLlama CLI bridge (llama_wrapper)     │
│  - Scheduling (scheduler_service)           │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│             Data Access Layer               │  Models (models.py)
│  - SQLAlchemy models                        │  Database (database.py)
│  - Database session management              │
│  - Query building and execution             │
└─────────────────────────────────────────────┘
```

### Service-Oriented Design

Each service encapsulates business logic for a domain:

```python
# Example: InterestService
class InterestService:
    def add_user_interest(db: Session, user_id: int, interest_name: str, is_predefined: bool) -> UserInterest:
        """
        Add interest to user profile.

        Business rules:
        - Validate interest name (length, characters)
        - Prevent duplicate interests (case-insensitive)
        - Mark as predefined if from curated list
        - Trigger newsletter regeneration if needed

        Raises:
            DuplicateInterestError: Interest already exists
            InterestValidationError: Invalid interest name
        """
```

Benefits:
- **Testability**: Services are easily mocked/stubbed
- **Reusability**: Same logic used in API endpoints and background jobs
- **Maintainability**: Business logic isolated from HTTP/database concerns

### Dependency Injection

FastAPI's dependency injection used throughout:

```python
@app.get("/calendar")
async def calendar_view(
    request: Request,
    user: User = Depends(get_current_user),  # Injected dependency
    db: Session = Depends(get_db),           # Injected dependency
):
    # user and db are automatically provided
    newsletters = newsletter_service.get_newsletters_by_month(db, user.id, year, month)
    return templates.TemplateResponse(request, "calendar.html", {...})
```

Benefits:
- **Testability**: Easy to override dependencies in tests
- **Clarity**: Explicit declaration of what each endpoint needs
- **Lifecycle Management**: DB sessions automatically closed after request

## Data Layer

### Database Schema

#### Users Table

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(100) NOT NULL,
    avatar_path VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Stores user profiles. Simple design with extensibility for future fields (last_name, email, settings).

#### UserInterests Table

```sql
CREATE TABLE user_interests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    interest_name VARCHAR(200) NOT NULL,
    is_predefined BOOLEAN NOT NULL DEFAULT FALSE,
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, interest_name)  -- Prevent duplicate interests per user
);

CREATE INDEX idx_user_interests_user_id ON user_interests(user_id);
```

Many-to-many relationship between users and interests:
- `is_predefined`: Distinguishes curated interests from custom user inputs
- `added_at`: Enables "recently added" features
- Composite unique constraint prevents duplicates

#### Newsletters Table

```sql
CREATE TABLE newsletters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    guid VARCHAR(100) NOT NULL UNIQUE,
    file_path VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    generated_at TIMESTAMP,
    retry_count INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT check_status CHECK (status IN ('pending', 'generating', 'completed', 'failed'))
);

-- Performance indexes (O(log n) lookups)
CREATE INDEX idx_newsletters_user_id ON newsletters(user_id);
CREATE INDEX idx_newsletters_date ON newsletters(date);
CREATE INDEX idx_newsletters_status ON newsletters(status);
CREATE UNIQUE INDEX idx_newsletters_user_date ON newsletters(user_id, date);
```

Tracks newsletter generation:
- `guid`: Public identifier (URL-safe, e.g., "news-2025-10-22")
- `status`: State machine (pending → generating → completed/failed)
- `retry_count`: Automatic retry tracking (max 3 attempts)
- Composite unique index on (user_id, date) ensures one newsletter per user per day

### SQLAlchemy Models

#### User Model

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    avatar_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships (lazy loaded by default)
    interests = relationship(
        "UserInterest",
        back_populates="user",
        cascade="all, delete-orphan"  # Delete interests when user deleted
    )
    newsletters = relationship(
        "Newsletter",
        back_populates="user",
        cascade="all, delete-orphan"  # Delete newsletters when user deleted
    )
```

**Design Decisions:**
- `cascade="all, delete-orphan"`: When user is deleted, all related data is automatically cleaned up
- `back_populates`: Bidirectional relationship (user.interests, interest.user)
- `lazy="select"`: Relationships loaded on access (use joinedload() for eager loading)

#### UserInterest Model

```python
class UserInterest(Base):
    __tablename__ = "user_interests"
    __table_args__ = (
        UniqueConstraint("user_id", "interest_name", name="uq_user_interest"),
        Index("idx_user_interests_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    interest_name = Column(String(200), nullable=False)
    is_predefined = Column(Boolean, default=False, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="interests")
```

**Design Decisions:**
- Composite unique constraint prevents duplicate interests per user
- `ondelete="CASCADE"`: Interest is deleted when user is deleted (redundant with relationship cascade, but explicit at DB level)
- `is_predefined`: Enables UI to differentiate curated vs custom interests

#### Newsletter Model

```python
class Newsletter(Base):
    __tablename__ = "newsletters"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'generating', 'completed', 'failed')", name="check_status"),
        Index("idx_newsletters_user_id", "user_id"),
        Index("idx_newsletters_date", "date"),
        Index("idx_newsletters_status", "status"),
        Index("idx_newsletters_user_date", "user_id", "date", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    guid = Column(String(100), unique=True, nullable=False)
    file_path = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    generated_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="newsletters")
```

**Design Decisions:**
- `CheckConstraint`: Database-level validation of status enum
- Multiple indexes for common queries (see Performance Optimizations)
- `guid`: Public identifier (vs internal `id` for security)
- `file_path`: Nullable because it's only set after successful generation

### Database Session Management

```python
# database.py
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific
    pool_pre_ping=True,  # Verify connections before use
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency injection: provides DB session to endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # Always close session, even if exception
```

**WAL Mode Configuration:**

```python
# Enable WAL mode for better concurrency
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")  # 5 second timeout
    cursor.close()
```

Benefits:
- **WAL Mode**: Multiple readers + one writer concurrently (no blocking)
- **busy_timeout**: Waits 5 seconds if database is locked (prevents immediate failures)
- **pool_pre_ping**: Detects stale connections and reconnects automatically

## Service Layer

### Service Design Pattern

Each service follows a consistent pattern:

```python
class ServiceName:
    """
    Domain-specific business logic.

    Responsibilities:
    - Validate inputs
    - Enforce business rules
    - Coordinate database operations
    - Raise custom exceptions on errors

    Does NOT:
    - Handle HTTP concerns (status codes, headers)
    - Render templates
    - Parse request bodies
    """
```

### UserService

**Responsibilities:**
- CRUD operations for users
- Validate user data (name length, character restrictions)

**Key Methods:**

```python
def create_user(db: Session, first_name: str) -> User:
    """Create new user with validation."""

def get_user(db: Session, user_id: int) -> Optional[User]:
    """Retrieve user by ID."""

def get_all_users(db: Session) -> List[User]:
    """Retrieve all users for profile selection."""

def update_user(db: Session, user_id: int, first_name: Optional[str] = None) -> User:
    """Update user fields."""

def delete_user(db: Session, user_id: int) -> None:
    """Delete user and all related data (CASCADE)."""
```

**Design Decisions:**
- Returns domain models (User), not dictionaries
- Raises `UserNotFoundError` instead of returning None (explicit error handling)
- Accepts `db: Session` as first parameter (dependency injection)

### InterestService

**Responsibilities:**
- Manage user interests
- Provide predefined interest list
- Validate interest names
- Prevent duplicates (case-insensitive)

**Key Methods:**

```python
def add_user_interest(db: Session, user_id: int, interest_name: str, is_predefined: bool) -> UserInterest:
    """
    Add interest to user profile.

    Validation:
    - 1-200 characters
    - No special characters (alphanumeric + spaces only)
    - Case-insensitive duplicate check

    Raises:
        DuplicateInterestError
        InterestValidationError
    """

def remove_user_interest(db: Session, user_id: int, interest_name: str) -> None:
    """Remove interest (case-insensitive lookup)."""

def get_user_interests(db: Session, user_id: int) -> List[UserInterest]:
    """Get all interests for user."""

def get_predefined_interests() -> List[str]:
    """Get curated list of popular interests."""
```

**Business Rules:**
- Interest names are case-insensitive ("AI" == "ai")
- Cannot have duplicate interests per user
- Predefined interests are curated for best source discovery

### NewsletterService

**Responsibilities:**
- CRUD operations for newsletters
- Retrieve newsletters by date/month/guid
- Update newsletter status
- Retry failed newsletters

**Key Methods:**

```python
def create_newsletter(db: Session, user_id: int, newsletter_date: date) -> Newsletter:
    """Create newsletter with unique GUID."""

def get_newsletter_by_guid(db: Session, guid: str) -> Newsletter:
    """Retrieve newsletter by public GUID."""

def get_newsletters_by_month(db: Session, user_id: int, year: int, month: int) -> List[Newsletter]:
    """
    Get all newsletters for user in specified month.

    Uses eager loading to avoid N+1 queries.
    """

def update_newsletter_status(db: Session, newsletter_id: int, status: str, file_path: Optional[str] = None) -> Newsletter:
    """Update status and optional file_path."""

def retry_newsletter(db: Session, guid: str) -> Newsletter:
    """
    Reset failed newsletter to pending status.

    Increments retry_count.
    Max retries: 3 (enforced in generation_service).
    """
```

**Design Decisions:**
- Uses GUID (public) instead of ID (internal) for URL endpoints
- `get_newsletters_by_month` uses joinedload() for eager loading
- Raises custom exceptions (NewsletterNotFoundError, NewsletterValidationError)

### GenerationService

**Responsibilities:**
- Orchestrate newsletter generation pipeline
- Queue newsletters for background processing
- Update newsletter status during generation
- Handle retries and error logging
- Track generation metrics

**Key Methods:**

```python
def queue_newsletter_generation(db: Session, user_id: int, newsletter_date: date) -> Newsletter:
    """
    Queue newsletter for generation.

    Checks:
    - User exists
    - User has interests
    - Newsletter doesn't already exist for this date

    Creates newsletter with status='pending'.
    Returns newsletter for scheduler to process.

    Raises:
        UserNotFoundError
        NoInterestsError
        NewsletterAlreadyExistsError
    """

def process_newsletter(db: Session, newsletter_id: int) -> None:
    """
    Process newsletter (called by scheduler in background).

    Pipeline:
    1. Load user and interests
    2. Update status to 'generating'
    3. Initialize NewsLlama with user interests
    4. Run aggregation/summarization
    5. Generate HTML output
    6. Update status to 'completed' (or 'failed')
    7. Record metrics (duration, success/failure)

    Handles:
    - Retries (up to 3 attempts)
    - Error logging
    - Status updates
    """

def requeue_newsletter_for_today(db: Session, user_id: int) -> bool:
    """
    Requeue today's newsletter for regeneration (when interests change).

    Only requeues if newsletter exists and is completed.
    Resets status to 'pending' and clears file_path.
    """
```

**Integration with NewsLlama CLI via LlamaWrapper:**

```python
# generation_service.py
from src.web.services.llama_wrapper import generate_newsletter_for_interests

def process_newsletter_generation(db: Session, newsletter_id: int):
    # ... load user and interests ...

    # Use wrapper to bridge web app and CLI
    file_path = generate_newsletter_for_interests(
        interests=interest_names,
        output_date=newsletter.date
    )

    # Wrapper handles:
    # - Async context for NewsLlama
    # - Output directory creation
    # - File path generation
    # - Error handling

    # Update newsletter with file path
    newsletter_service.mark_newsletter_completed(db, newsletter_id, file_path)
```

**Metrics Tracking:**

```python
class GenerationMetrics:
    """Thread-safe metrics tracking for newsletter generation."""

    def __init__(self):
        self._lock = threading.Lock()
        self._metrics = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "durations": []  # List of generation durations in seconds
        }

    def record_success(self, duration_seconds: float):
        with self._lock:
            self._metrics["total"] += 1
            self._metrics["successful"] += 1
            self._metrics["durations"].append(duration_seconds)

    def get_stats(self) -> dict:
        """Return success rate, avg duration, etc."""
```

Benefits:
- Monitoring generation performance
- Identifying slow generations
- Alerting on high failure rates

### LlamaWrapperService

**Responsibilities:**
- Bridge web application and CLI NewsLlama engine
- Handle async context for newsletter generation
- Manage output directory and file paths
- Provide error handling and validation

**Key Methods:**

```python
def generate_newsletter_for_interests(interests: list[str], output_date: date) -> str:
    """
    Generate newsletter for given interests and date.

    Process:
    1. Get output file path based on date
    2. Ensure output directory exists
    3. Initialize NewsLlama with user interests
    4. Run generation (asyncio.run for sync context)
    5. Verify output file created
    6. Return absolute file path

    Raises:
        NewsLlamaWrapperError: If generation fails
    """

def get_output_file_path(output_date: date, guid: str = None) -> str:
    """Build absolute path to output HTML file."""

def ensure_output_directory(directory_path: str):
    """Create output directory if missing."""
```

**Design Decisions:**
- Wraps CLI in sync interface (uses asyncio.run internally)
- Separates web app concerns from CLI concerns
- Centralizes file path logic
- Provides clean error messages for web context

### SchedulerService

**Responsibilities:**
- Manage APScheduler lifecycle
- Schedule daily newsletter generation
- Queue immediate generation requests
- Provide health check information

**Key Methods:**

```python
def start_scheduler(config: dict) -> None:
    """
    Start APScheduler with daily job.

    Config:
    - SCHEDULER_ENABLED: bool
    - SCHEDULER_HOUR: int (0-23)
    - SCHEDULER_MINUTE: int (0-59)
    - SCHEDULER_TIMEZONE: str
    """

def stop_scheduler() -> None:
    """Gracefully shutdown scheduler (called on app shutdown)."""

def schedule_daily_generation() -> None:
    """Job function: generate newsletters for all users."""

def queue_immediate_generation(newsletter_id: int) -> None:
    """Queue single newsletter for immediate processing."""
```

**Implementation:**

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from concurrent.futures import ThreadPoolExecutor

# Async scheduler for FastAPI compatibility
scheduler = AsyncIOScheduler()

# Thread pool for long-running newsletter generation
# Max 3 concurrent generations for family-sized deployment
executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="newsletter_gen")

def start_scheduler(config):
    if not config["SCHEDULER_ENABLED"]:
        return

    scheduler.add_job(
        func=generate_daily_newsletters,
        trigger=CronTrigger(
            hour=config["SCHEDULER_HOUR"],
            minute=config["SCHEDULER_MINUTE"],
            timezone=config["SCHEDULER_TIMEZONE"]
        ),
        id="daily_newsletter_generation",
        name="Generate daily newsletters for all users",
        replace_existing=True
    )

    scheduler.start()

def generate_daily_newsletters():
    """Called by scheduler at configured time."""
    db = SessionLocal()
    try:
        users = user_service.get_all_users(db)
        for user in users:
            # Queue newsletter for each user
            newsletter = generation_service.queue_newsletter_generation(db, user.id, date.today())
            # Queue for immediate processing via scheduler + thread pool
            scheduler_service.queue_immediate_generation(newsletter.id)
    finally:
        db.close()

def queue_immediate_generation(newsletter_id: int):
    """Queue newsletter for background processing using thread pool."""
    def _process_with_db():
        db = SessionLocal()
        try:
            generation_service.process_newsletter_generation(db, newsletter_id)
        finally:
            db.close()

    def _schedule_in_thread_pool():
        future = executor.submit(_process_with_db)
        # Log completion when done

    # Add immediate job that submits to thread pool
    scheduler.add_job(
        func=_schedule_in_thread_pool,
        id=f"newsletter_{newsletter_id}",
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period
    )
```

## API Layer

### Route Organization

```python
# app.py
app = FastAPI(title="News Llama", lifespan=lifespan)

# HTML pages (return templates)
@app.get("/", response_class=HTMLResponse)
@app.get("/calendar", response_class=HTMLResponse)
@app.get("/profile/new", response_class=HTMLResponse)
@app.get("/profile/settings", response_class=HTMLResponse)

# API endpoints (return JSON)
@app.post("/profile/create")
@app.post("/profile/settings")
@app.post("/profile/settings/interests/add")
@app.post("/newsletters/generate", response_model=NewsletterResponse)

# Health checks
@app.get("/health/scheduler")
@app.get("/health/generation")
```

### Authentication

**Cookie-Based Sessions:**

```python
def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Dependency: extracts user from cookie.

    Checks:
    - user_id cookie exists
    - user_id is valid integer
    - user exists in database

    Returns None if no session (endpoints must handle this).
    """
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None

    try:
        return user_service.get_user(db, int(user_id))
    except (ValueError, user_service.UserNotFoundError):
        return None
```

**Setting Session Cookie:**

```python
@app.post("/profile/create")
async def profile_create(profile_data: ProfileCreateRequest, response: Response, db: Session = Depends(get_db)):
    user = user_service.create_user(db, first_name=profile_data.first_name)
    # ... add interests, queue newsletter ...

    redirect = RedirectResponse(url="/calendar", status_code=303)
    redirect.set_cookie(key="user_id", value=str(user.id))  # Session cookie
    return redirect
```

**Security Considerations:**
- No HttpOnly flag: JavaScript can access cookie (consider adding for production)
- No SameSite: Consider `SameSite=Lax` to prevent CSRF
- No expiration: Session cookie (cleared when browser closes)
- No encryption: Consider signing cookies with `itsdangerous` library

### Request/Response Schemas

**Pydantic Models (schemas.py):**

```python
class ProfileCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    interests: List[str] = Field(..., min_items=1, max_items=50)

    @validator("first_name")
    def validate_first_name(cls, v):
        if not v.strip():
            raise ValueError("First name cannot be empty")
        return v.strip()

class NewsletterResponse(BaseModel):
    id: int
    user_id: int
    date: str  # ISO format
    guid: str
    file_path: Optional[str]
    status: str
    generated_at: Optional[str]
    retry_count: int

    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)
```

Benefits:
- Automatic validation before handler executes
- Auto-generated OpenAPI documentation
- Type safety with editor autocomplete
- Consistent error responses (422 Unprocessable Entity)

### Error Handling

**Global Exception Handlers (error_handlers.py):**

```python
ERROR_MESSAGES = {
    "user_not_found": "We couldn't find your profile. Please select or create one.",
    "newsletter_duplicate": "You already have a newsletter for this date. Check your calendar!",
    "generation_failed": "Newsletter generation failed. We'll automatically retry in a few minutes.",
    # ... 21 total predefined messages covering all service exceptions
}

def get_friendly_message(exception: Exception) -> str:
    """Map exception to user-friendly message."""
    exception_name = type(exception).__name__
    return ERROR_MESSAGES.get(exception_name, "An unexpected error occurred. Please try again.")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions.

    Returns user-friendly message, logs full stack trace server-side.
    Never exposes stack traces to clients.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": get_friendly_message(exc)}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors.

    Returns specific field errors in user-friendly format.
    """
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append(f"{field}: {message}")

    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "errors": errors}
    )
```

**Exception Hierarchy:**

```python
# Base exception
class NewsLlamaWebError(Exception):
    """Base exception for all web application errors."""

# Service-specific exceptions
class UserNotFoundError(NewsLlamaWebError): pass
class DuplicateInterestError(NewsLlamaWebError): pass
class NewsletterAlreadyExistsError(NewsLlamaWebError): pass
class GenerationServiceError(NewsLlamaWebError): pass
```

Benefits:
- Consistent error messages across the application
- Stack traces never exposed to clients (security)
- Specific HTTP status codes for different error types
- Centralized error handling (DRY principle)

## Background Jobs

### APScheduler Integration

**Lifecycle Management:**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup/shutdown)."""
    # Startup
    logger.info("Starting News Llama web application")

    is_testing = os.getenv("TESTING", "false").lower() == "true"
    if not is_testing:
        config = {
            "SCHEDULER_ENABLED": os.getenv("SCHEDULER_ENABLED", "true").lower() == "true",
            "SCHEDULER_HOUR": int(os.getenv("SCHEDULER_HOUR", "6")),
            "SCHEDULER_MINUTE": int(os.getenv("SCHEDULER_MINUTE", "0")),
            "SCHEDULER_TIMEZONE": os.getenv("SCHEDULER_TIMEZONE", "America/Los_Angeles"),
        }
        scheduler_service.start_scheduler(config)

    yield

    # Shutdown
    if not is_testing:
        logger.info("Shutting down News Llama web application")
        scheduler_service.stop_scheduler()

app = FastAPI(title="News Llama", lifespan=lifespan)
```

**Daily Generation Job:**

```python
def generate_daily_newsletters():
    """
    Called by APScheduler at configured time (default: 6 AM).

    Process:
    1. Get all users from database
    2. For each user:
       - Check if newsletter already exists for today
       - If not, queue new newsletter
       - Start background thread for processing
    3. Log success/failure per user
    """
    db = SessionLocal()
    try:
        users = user_service.get_all_users(db)
        logger.info(f"Starting daily generation for {len(users)} users")

        for user in users:
            try:
                # Queue newsletter (checks for existing)
                newsletter = generation_service.queue_newsletter_generation(db, user.id, date.today())

                # Process in background thread (non-blocking)
                thread = threading.Thread(
                    target=generation_service.process_newsletter,
                    args=(SessionLocal(), newsletter.id),  # New session for thread
                    daemon=True
                )
                thread.start()

                logger.info(f"Queued newsletter for user {user.id} (newsletter {newsletter.id})")
            except generation_service.NewsletterAlreadyExistsError:
                logger.info(f"Newsletter already exists for user {user.id}")
            except Exception as e:
                logger.error(f"Failed to queue newsletter for user {user.id}: {e}")
    finally:
        db.close()
```

**Immediate Generation (User-Triggered):**

```python
def queue_immediate_generation(newsletter_id: int):
    """
    Queue single newsletter for immediate processing.

    Called when:
    - User creates profile (first newsletter)
    - User manually generates newsletter for a date
    - Newsletter is retried after failure
    """
    thread = threading.Thread(
        target=generation_service.process_newsletter,
        args=(SessionLocal(), newsletter_id),
        daemon=True
    )
    thread.start()
```

**Design Decisions:**
- **Background Threads**: Newsletter generation is slow (10-15 min), must not block HTTP requests
- **Separate DB Sessions**: Each thread gets its own session to avoid conflicts
- **Daemon Threads**: Threads don't prevent application shutdown
- **Error Isolation**: If one user's generation fails, others continue

## Performance Optimizations

### Database Indexes

**Purpose**: Reduce query time from O(n) to O(log n)

**Indexes Created:**

```python
# newsletters table
Index("idx_newsletters_user_id", "user_id")              # Filter by user
Index("idx_newsletters_date", "date")                    # Filter by date
Index("idx_newsletters_status", "status")                # Filter by status
Index("idx_newsletters_user_date", "user_id", "date", unique=True)  # Composite lookup

# user_interests table
Index("idx_user_interests_user_id", "user_id")           # Filter by user
```

**Query Optimization Example:**

```python
# WITHOUT index: O(n) table scan
SELECT * FROM newsletters WHERE user_id = 1 AND date BETWEEN '2025-10-01' AND '2025-10-31';
# Scans all rows, checks user_id and date for each

# WITH indexes: O(log n) B-tree lookup
# Uses idx_newsletters_user_id to find user's newsletters (log n)
# Then filters by date range (already sorted by index)
```

**Performance Benchmarks (from tests):**

```python
# test_performance.py::TestQueryPerformance
def test_monthly_newsletter_query_performance(db, user):
    """Query 100 newsletters for a month should be <100ms."""
    # Create 100 newsletters
    for i in range(100):
        newsletter_service.create_newsletter(db, user.id, date(2025, 10, i+1))

    start = time.time()
    result = newsletter_service.get_newsletters_by_month(db, user.id, 2025, 10)
    duration = (time.time() - start) * 1000  # Convert to milliseconds

    assert duration < 100, f"Query took {duration}ms (expected <100ms)"
    assert len(result) == 100
```

### Eager Loading

**Problem: N+1 Queries**

```python
# BAD: Causes N+1 queries
users = db.query(User).all()  # 1 query
for user in users:
    interests = user.interests  # N queries (1 per user)
```

**Solution: joinedload()**

```python
# GOOD: Single query with JOIN
from sqlalchemy.orm import joinedload

users = db.query(User).options(joinedload(User.interests)).all()  # 1 query
for user in users:
    interests = user.interests  # No additional query (already loaded)
```

**Implementation in newsletter_service:**

```python
def get_newsletters_by_month(db: Session, user_id: int, year: int, month: int) -> List[Newsletter]:
    """Get newsletters with eager loading."""
    start_date = date(year, month, 1)
    end_date = date(year, month, calendar.monthrange(year, month)[1])

    return (
        db.query(Newsletter)
        .options(joinedload(Newsletter.user))  # Eager load user
        .filter(Newsletter.user_id == user_id)
        .filter(Newsletter.date >= start_date)
        .filter(Newsletter.date <= end_date)
        .order_by(Newsletter.date.asc())
        .all()
    )
```

### Rate Limiting

**Implementation (rate_limiter.py):**

```python
class RateLimiter:
    """Sliding window rate limiter."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if request is allowed.

        Algorithm:
        1. Remove timestamps outside current window
        2. Count remaining requests
        3. If under limit, add current timestamp and allow
        4. Otherwise, reject

        Returns: (is_allowed, remaining_requests)
        """
        now = time.time()
        window_start = now - self.window_seconds

        request_queue = self._requests[identifier]

        # Remove old timestamps
        while request_queue and request_queue[0] < window_start:
            request_queue.popleft()

        current_count = len(request_queue)
        remaining = max(0, self.max_requests - current_count)

        if current_count < self.max_requests:
            request_queue.append(now)
            return True, remaining - 1

        return False, 0
```

**Decorator Usage:**

```python
@app.post("/newsletters/generate")
@rate_limit(lambda user: user.id if user else None)
async def generate_newsletter(user: User = Depends(get_current_user), ...):
    # Only execute if rate limit allows
    ...
```

**Configuration:**
- Default: 10 requests per 60 seconds per user
- In-memory tracking (consider Redis for multi-instance deployments)
- Automatically cleans up old entries

### File Caching

**Implementation (file_cache.py):**

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def read_newsletter_file(file_path: str) -> Optional[bytes]:
    """
    LRU cache for newsletter HTML files.

    Benefits:
    - Avoids disk I/O for frequently accessed newsletters
    - Automatic eviction (LRU policy)
    - Thread-safe (functools.lru_cache is thread-safe)

    Memory Usage:
    - Average newsletter: ~100KB
    - Max cache size: 100 files
    - Total: ~10MB max memory
    """
    path = Path(file_path)
    if not path.exists():
        return None

    try:
        with open(path, "rb") as f:
            return f.read()
    except (IOError, OSError):
        return None
```

**Usage:**

```python
@app.get("/newsletters/{guid}")
async def view_newsletter(guid: str, db: Session = Depends(get_db)):
    newsletter = newsletter_service.get_newsletter_by_guid(db, guid)

    if newsletter.status == "completed" and newsletter.file_path:
        # Try cache first (fast), then disk (slow)
        content = read_newsletter_file(newsletter.file_path)
        if content:
            return Response(content=content, media_type="text/html")

    # ... handle other statuses ...
```

**Performance Impact:**
- Cache hit: <1ms (memory read)
- Cache miss: ~10ms (disk read + cache insertion)
- Subsequent hits: <1ms (90% reduction for popular newsletters)

## Error Handling

### Exception Hierarchy

```
Exception
│
└── NewsLlamaWebError (base for all application exceptions)
    │
    ├── UserServiceError
    │   ├── UserNotFoundError
    │   ├── UserValidationError
    │   └── DuplicateUserError
    │
    ├── InterestServiceError
    │   ├── InterestNotFoundError
    │   ├── InterestValidationError
    │   └── DuplicateInterestError
    │
    ├── NewsletterServiceError
    │   ├── NewsletterNotFoundError
    │   ├── NewsletterValidationError
    │   └── NewsletterAlreadyExistsError
    │
    └── GenerationServiceError
        ├── NoInterestsError
        └── GenerationFailedError
```

### User-Friendly Error Messages

**Design Principle**: Never expose technical details to end users

**Examples:**

| Technical Exception | User-Friendly Message |
|--------------------|-----------------------|
| `UserNotFoundError` | "We couldn't find your profile. Please select or create one." |
| `DuplicateInterestError` | "You already have this interest! Try adding a different one." |
| `NewsletterAlreadyExistsError` | "You already have a newsletter for this date. Check your calendar!" |
| `GenerationFailedError` | "Newsletter generation failed. We'll automatically retry in a few minutes." |
| `SQLAlchemyError` | "Database error. Please try again in a few moments." |
| `Exception` (unknown) | "An unexpected error occurred. Please try again." |

**Implementation:**

```python
# error_handlers.py
ERROR_MESSAGES = {
    "UserNotFoundError": "We couldn't find your profile. Please select or create one.",
    "DuplicateInterestError": "You already have this interest! Try adding a different one.",
    # ... 21 total mappings covering user, interest, newsletter, and generation errors
}

def get_friendly_message(exception: Exception) -> str:
    """Get user-friendly message for any exception."""
    exception_name = type(exception).__name__
    return ERROR_MESSAGES.get(exception_name, "An unexpected error occurred. Please try again.")
```

### Logging Strategy

**Levels:**

```python
# INFO: Normal operations
logger.info("User 123 created newsletter 456")

# WARNING: Recoverable issues
logger.warning("Newsletter generation failed (attempt 1/3), will retry")

# ERROR: Unrecoverable issues
logger.error("Failed to generate newsletter after 3 attempts", exc_info=True)

# DEBUG: Detailed troubleshooting (disabled in production)
logger.debug(f"Query executed: {query}")
```

**Log Rotation (logrotate):**

```
/var/log/news-llama/*.log {
    daily           # Rotate daily
    rotate 14       # Keep 14 days
    compress        # Compress old logs
    delaycompress   # Compress on next rotation (not immediately)
    notifempty      # Don't rotate if empty
    missingok       # Don't error if log missing
}
```

## Security

### Input Validation

**Pydantic Schemas:**

```python
class ProfileCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    interests: List[str] = Field(..., min_items=1, max_items=50)

    @validator("first_name")
    def validate_first_name(cls, v):
        # Strip whitespace
        v = v.strip()
        # Check length
        if len(v) == 0:
            raise ValueError("First name cannot be empty")
        # Check characters (alphanumeric + spaces only)
        if not all(c.isalnum() or c.isspace() for c in v):
            raise ValueError("First name can only contain letters, numbers, and spaces")
        return v
```

**Database Constraints:**

```sql
-- Prevent invalid status values
CHECK (status IN ('pending', 'generating', 'completed', 'failed'))

-- Ensure required fields
NOT NULL constraints on critical columns

-- Prevent duplicates
UNIQUE constraints on (user_id, interest_name) and (user_id, date)
```

### SQL Injection Prevention

**SQLAlchemy ORM:**

```python
# SAFE: SQLAlchemy automatically parameterizes queries
user = db.query(User).filter(User.id == user_id).first()

# UNSAFE (if we were using raw SQL):
# cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")  # NEVER DO THIS
```

**Parameterized Queries:**

```python
# Even with raw SQL, SQLAlchemy parameterizes:
result = db.execute(
    text("SELECT * FROM users WHERE id = :user_id"),
    {"user_id": user_id}  # Safely parameterized
)
```

### XSS Prevention

**Jinja2 Auto-Escaping:**

```html
<!-- Jinja2 automatically escapes HTML by default -->
<h1>Welcome, {{ user.first_name }}</h1>
<!-- If first_name is "<script>alert('XSS')</script>", it renders as: -->
<!-- &lt;script&gt;alert('XSS')&lt;/script&gt; (harmless text) -->

<!-- To output raw HTML (use sparingly): -->
{{ content|safe }}
```

**Content Security Policy (CSP):**

```nginx
# nginx configuration
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'";
```

### CSRF Protection

**Current State**: Not implemented (consider adding for production)

**Recommended:**

```python
from starlette.middleware.csrf import CSRFMiddleware

app.add_middleware(CSRFMiddleware, secret_key="your-secret-key")
```

### Authentication & Authorization

**Current Implementation**: Cookie-based sessions (simple, stateless)

**Limitations:**
- No password protection (anyone can select any profile)
- No token expiration
- No HttpOnly flag (JavaScript can access cookie)

**Production Recommendations:**

1. **Add Password Authentication:**
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

2. **Use JWT Tokens:**
```python
from jose import jwt

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
```

3. **Implement OAuth2 (Optional):**
```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
```

## Testing Strategy

### Test Structure

```
tests/web/unit/
├── conftest.py              # Shared fixtures (db, user, newsletters)
├── test_models.py           # SQLAlchemy model tests (4 test classes, 13 tests)
├── test_database.py         # Database setup tests (4 tests)
├── test_services.py         # Service layer tests (5 test classes, 52 tests)
├── test_routes.py           # API endpoint tests (6 test classes, 48 tests)
├── test_generation_service.py  # Generation orchestration (4 test classes, 30 tests)
├── test_error_handlers.py   # Error handling (3 test classes, 13 tests)
├── test_performance.py      # Indexes, caching, rate limiting (3 test classes, 14 tests)
└── test_ui_states.py        # Empty states, loading states (3 test classes, 10 tests)

Total: 281 tests (as of latest run)
```

### Testing Approach

**Unit Tests**: Test individual functions in isolation

```python
def test_create_user(db):
    """Test user creation with valid data."""
    user = user_service.create_user(db, first_name="Alice")
    assert user.id is not None
    assert user.first_name == "Alice"
    assert user.created_at is not None
```

**Integration Tests**: Test multiple components together

```python
def test_newsletter_generation_workflow(db, user):
    """Test complete generation workflow."""
    # 1. Add interests
    interest_service.add_user_interest(db, user.id, "AI", is_predefined=True)

    # 2. Queue newsletter
    newsletter = generation_service.queue_newsletter_generation(db, user.id, date.today())
    assert newsletter.status == "pending"

    # 3. Process newsletter (mock NewsLlama)
    with mock.patch("generation_service.NewsLlama") as mock_llama:
        generation_service.process_newsletter(db, newsletter.id)

    # 4. Verify status updated
    db.refresh(newsletter)
    assert newsletter.status == "completed"
    assert newsletter.file_path is not None
```

**Performance Tests**: Verify optimization goals

```python
def test_rate_limiter_allows_10_requests_per_minute(user):
    """Rate limiter should allow exactly 10 requests per user per 60 seconds."""
    limiter = RateLimiter(max_requests=10, window_seconds=60)

    # First 10 requests should succeed
    for i in range(10):
        allowed, remaining = limiter.is_allowed(str(user.id))
        assert allowed is True

    # 11th request should fail
    allowed, remaining = limiter.is_allowed(str(user.id))
    assert allowed is False
    assert remaining == 0
```

### Test Fixtures

**conftest.py** (shared fixtures):

```python
@pytest.fixture
def db():
    """Create in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()

@pytest.fixture
def user(db):
    """Create test user."""
    return user_service.create_user(db, first_name="TestUser")

@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before each test (prevents interference)."""
    from src.web.rate_limiter import newsletter_rate_limiter
    newsletter_rate_limiter._requests.clear()
    yield
    newsletter_rate_limiter._requests.clear()
```

### Coverage Target

**Current Coverage**: 281 tests, 88% overall for src/web/

**Coverage by Module:**
- `models.py`: 100% (all models tested)
- `services/`: 95%+ (comprehensive service tests)
- `app.py`: 90%+ (most endpoints tested)
- `rate_limiter.py`: 100% (all edge cases)
- `error_handlers.py`: 100% (all exceptions)

**Target**: 80%+ overall coverage for `src/web/`

**Run Coverage:**

```bash
TESTING=true PYTHONPATH=. pytest tests/web/unit/ --cov=src/web --cov-report=html
```

## Deployment Architecture

### Single-Server Deployment

```
┌─────────────────────────────────────────────────────────────┐
│                      Production Server                       │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Nginx (Port 80/443)                                   │ │
│  │  - SSL termination                                     │ │
│  │  - Static file serving                                 │ │
│  │  - Reverse proxy to Uvicorn                           │ │
│  └──────────────────────┬─────────────────────────────────┘ │
│                         │                                    │
│  ┌──────────────────────▼─────────────────────────────────┐ │
│  │  Uvicorn (Port 8001)                                   │ │
│  │  - FastAPI application                                 │ │
│  │  - 2-4 workers (multi-process)                        │ │
│  │  - APScheduler (daily jobs)                           │ │
│  └──────────────────────┬─────────────────────────────────┘ │
│                         │                                    │
│  ┌──────────────────────▼─────────────────────────────────┐ │
│  │  SQLite (WAL mode)                                     │ │
│  │  - news_llama.db                                       │ │
│  │  - Multiple readers + 1 writer                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Systemd                                               │ │
│  │  - news-llama.service (auto-restart)                  │ │
│  │  - Resource limits (2GB memory)                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Cron Jobs                                             │ │
│  │  - Database backup (daily 3 AM)                       │ │
│  │  - Log rotation (daily)                               │ │
│  │  - Health checks (every 5 min)                        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Multi-Server Deployment (Future)

For scaling beyond 100 users:

```
                    ┌─────────────┐
                    │ Load Balancer│
                    │   (Nginx)    │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌─────────┐      ┌─────────┐     ┌─────────┐
    │ Server 1│      │ Server 2│     │ Server 3│
    │ (Uvicorn│      │ (Uvicorn│     │ (Uvicorn│
    │  + App) │      │  + App) │     │  + App) │
    └────┬────┘      └────┬────┘     └────┬────┘
         │                │               │
         └────────────────┼───────────────┘
                          ▼
                  ┌──────────────┐
                  │  PostgreSQL  │
                  │  (Shared DB) │
                  └──────────────┘
                          │
                  ┌──────────────┐
                  │   Redis      │
                  │ (Rate Limit) │
                  └──────────────┘
```

**Changes Required:**
- Replace SQLite with PostgreSQL (multi-writer support)
- Replace in-memory rate limiter with Redis
- Shared file storage (NFS, S3) for newsletter HTML files
- Centralized scheduler (only one instance runs daily jobs)

---

## Summary

The News Llama web application is built on a solid architectural foundation:

- **Layered Architecture**: Clear separation between routes, services, and data access
- **Service-Oriented**: Reusable business logic isolated from HTTP/database concerns
- **Performance-Optimized**: Database indexes, eager loading, rate limiting, LRU caching
- **Error Handling**: User-friendly messages, no stack trace exposure
- **Testable**: 88% test coverage (281 tests) with comprehensive unit/integration tests
- **Secure**: Input validation, SQL injection prevention, XSS protection
- **Scalable**: Single-server design supports 1-100 users, multi-server path available

For deployment details, see [deployment.md](deployment.md).
For user documentation, see [user-guide.md](user-guide.md).
For application overview, see [../README.md](../README.md).
