"""SQLAlchemy ORM models for News Llama web application.

Implemented following TDD methodology (GREEN phase).
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    """User model - represents a profile in the system."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    avatar_path = Column(String, nullable=True)
    created_at = Column(String, nullable=False, server_default="(datetime('now'))")

    # Relationships
    newsletters = relationship(
        "Newsletter", back_populates="user", cascade="all, delete-orphan"
    )
    interests = relationship(
        "UserInterest", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, first_name='{self.first_name}')>"


class Newsletter(Base):
    """Newsletter model - tracks generated newsletters for users."""

    __tablename__ = "newsletters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date = Column(String, nullable=False)
    guid = Column(String, nullable=False, unique=True)
    file_path = Column(String, nullable=True)  # Nullable until newsletter is generated
    status = Column(String, nullable=False, server_default="pending")
    generated_at = Column(String, nullable=True)
    retry_count = Column(Integer, nullable=False, server_default="0")

    # Status constraint and indexes
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'generating', 'completed', 'failed')",
            name="check_newsletter_status",
        ),
        # Performance indexes for common query patterns
        Index("idx_newsletters_user_id", "user_id"),
        Index("idx_newsletters_date", "date"),
        Index("idx_newsletters_status", "status"),
        Index("idx_newsletters_user_date", "user_id", "date"),  # Composite index
    )

    # Relationships
    user = relationship("User", back_populates="newsletters")
    source_contributions = relationship(
        "SourceContribution", back_populates="newsletter", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Newsletter(id={self.id}, user_id={self.user_id}, guid='{self.guid}', status='{self.status}')>"


class UserInterest(Base):
    """UserInterest model - tracks user's selected interests/categories."""

    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    interest_name = Column(String, nullable=False)
    is_predefined = Column(Boolean, nullable=False, server_default="0")
    added_at = Column(String, nullable=False, server_default="(datetime('now'))")

    # Unique constraint and performance indexes
    __table_args__ = (
        UniqueConstraint("user_id", "interest_name", name="idx_user_interests"),
        # Performance index for user interests lookups
        Index("idx_user_interests_user_id", "user_id"),
    )

    # Relationships
    user = relationship("User", back_populates="interests")

    def __repr__(self):
        return f"<UserInterest(id={self.id}, user_id={self.user_id}, interest_name='{self.interest_name}')>"


class Tier1Source(Base):
    """Dynamic Tier 1 sources (auto-populated via weekly discovery)."""

    __tablename__ = "tier1_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(Text, nullable=False)
    source_key = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    interests = Column(Text, nullable=False)  # JSON array string
    quality_score = Column(Float, nullable=False)
    discovered_at = Column(Text, nullable=False)
    discovered_via = Column(Text, nullable=False)
    last_health_check = Column(Text, nullable=True)
    is_healthy = Column(Boolean, default=True)
    avg_posts_per_day = Column(Float, nullable=True)
    domain_age_years = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("source_type", "source_key", name="uq_tier1_source_type_key"),
        Index("idx_tier1_healthy", "is_healthy", "source_type"),
        Index("idx_tier1_interests", "interests"),
    )

    def __repr__(self):
        return f"<Tier1Source(id={self.id}, source_type='{self.source_type}', source_key='{self.source_key}')>"


class SourceBlacklist(Base):
    """Blacklisted sources (auto-populated from failures)."""

    __tablename__ = "source_blacklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(Text, nullable=False)
    source_key = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    blacklisted_at = Column(Text, nullable=False)
    blacklisted_reason = Column(Text, nullable=False)
    failure_count = Column(Integer, default=1)
    last_failure_at = Column(Text, nullable=False)
    last_attempted_resurrection = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "source_type", "source_key", name="uq_blacklist_source_type_key"
        ),
        Index("idx_blacklist_type", "source_type"),
    )

    def __repr__(self):
        return f"<SourceBlacklist(id={self.id}, source_type='{self.source_type}', source_key='{self.source_key}')>"


class DiscoveredSource(Base):
    """Discovery candidates (all sources found by weekly job)."""

    __tablename__ = "discovered_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(Text, nullable=False)
    source_key = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    discovered_at = Column(Text, nullable=False)
    discovered_via = Column(Text, nullable=False)
    discovery_count = Column(Integer, default=1)
    quality_score = Column(Float, nullable=True)
    health_check_passed = Column(Boolean, nullable=True)
    promoted_to_tier1 = Column(Boolean, default=False)
    interests = Column(Text, nullable=False)  # JSON array string
    source_metadata = Column(Text, nullable=True)  # JSON object string

    __table_args__ = (
        UniqueConstraint(
            "source_type", "source_key", name="uq_discovered_source_type_key"
        ),
        Index("idx_discovered_promoted", "promoted_to_tier1"),
    )

    def __repr__(self):
        return f"<DiscoveredSource(id={self.id}, source_type='{self.source_type}', source_key='{self.source_key}')>"


class SourceHealth(Base):
    """Health check results (per source, updated weekly)."""

    __tablename__ = "source_health"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(Text, nullable=False)
    source_key = Column(Text, nullable=False)
    last_check_at = Column(Text, nullable=False)
    last_success_at = Column(Text, nullable=True)
    last_failure_at = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    consecutive_successes = Column(Integer, default=0)
    is_healthy = Column(Boolean, default=True)
    failure_reason = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    articles_found = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("source_type", "source_key", name="uq_health_source_type_key"),
        Index("idx_health_status", "is_healthy", "consecutive_failures"),
    )

    def __repr__(self):
        return f"<SourceHealth(id={self.id}, source_type='{self.source_type}', source_key='{self.source_key}')>"


class SourceContribution(Base):
    """Usage tracking (per newsletter generation)."""

    __tablename__ = "source_contributions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    newsletter_id = Column(
        Integer, ForeignKey("newsletters.id", ondelete="CASCADE"), nullable=False
    )
    source_type = Column(Text, nullable=False)
    source_key = Column(Text, nullable=False)
    articles_collected = Column(Integer, default=0)
    articles_included = Column(Integer, default=0)
    collected_at = Column(Text, nullable=False)

    # Relationship
    newsletter = relationship("Newsletter", back_populates="source_contributions")

    __table_args__ = (
        Index("idx_contributions_newsletter", "newsletter_id"),
        Index("idx_contributions_source", "source_type", "source_key"),
        Index("idx_contributions_date", "collected_at"),
    )

    def __repr__(self):
        return f"<SourceContribution(id={self.id}, newsletter_id={self.newsletter_id}, source_type='{self.source_type}')>"
