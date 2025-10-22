"""SQLAlchemy ORM models for News Llama web application.

Implemented following TDD methodology (GREEN phase).
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
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

    # Status constraint
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'generating', 'completed', 'failed')",
            name="check_newsletter_status",
        ),
    )

    # Relationships
    user = relationship("User", back_populates="newsletters")

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

    # Unique constraint: user can't have duplicate interests
    __table_args__ = (
        UniqueConstraint("user_id", "interest_name", name="idx_user_interests"),
    )

    # Relationships
    user = relationship("User", back_populates="interests")

    def __repr__(self):
        return f"<UserInterest(id={self.id}, user_id={self.user_id}, interest_name='{self.interest_name}')>"
