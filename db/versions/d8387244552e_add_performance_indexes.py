"""add_performance_indexes

Revision ID: d8387244552e
Revises: 65db8e7f1268
Create Date: 2025-10-22 23:12:40.676395

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d8387244552e"
down_revision: Union[str, Sequence[str], None] = "65db8e7f1268"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by adding performance indexes."""
    # Get database connection to check for existing indexes
    conn = op.get_bind()

    # Helper function to check if index exists
    def index_exists(index_name: str) -> bool:
        result = conn.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type='index' AND name=:name"),
            {"name": index_name},
        ).fetchone()
        return result is not None

    # Index on newsletters.user_id for efficient user filtering
    if not index_exists("idx_newsletters_user_id"):
        op.create_index(
            "idx_newsletters_user_id", "newsletters", ["user_id"], unique=False
        )

    # Index on newsletters.date for month-based queries
    if not index_exists("idx_newsletters_date"):
        op.create_index("idx_newsletters_date", "newsletters", ["date"], unique=False)

    # Index on newsletters.status for status filtering
    if not index_exists("idx_newsletters_status"):
        op.create_index(
            "idx_newsletters_status", "newsletters", ["status"], unique=False
        )

    # Composite index on (user_id, date) for common query pattern
    # This optimizes queries like "get all newsletters for user X in month Y"
    if not index_exists("idx_newsletters_user_date"):
        op.create_index(
            "idx_newsletters_user_date",
            "newsletters",
            ["user_id", "date"],
            unique=False,
        )

    # Index on user_interests.user_id for efficient lookups
    if not index_exists("idx_user_interests_user_id"):
        op.create_index(
            "idx_user_interests_user_id", "user_interests", ["user_id"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema by removing performance indexes."""
    # Drop indexes in reverse order
    op.drop_index("idx_user_interests_user_id", table_name="user_interests")
    op.drop_index("idx_newsletters_user_date", table_name="newsletters")
    op.drop_index("idx_newsletters_status", table_name="newsletters")
    op.drop_index("idx_newsletters_date", table_name="newsletters")
    op.drop_index("idx_newsletters_user_id", table_name="newsletters")
