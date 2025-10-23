"""create_user_interests_table

Revision ID: 65db8e7f1268
Revises: 06cd333f221c
Create Date: 2025-10-22 12:50:14.039250

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "65db8e7f1268"
down_revision: Union[str, Sequence[str], None] = "06cd333f221c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_interests table (categories = interests, renamed for UI clarity)."""
    op.execute("""
        CREATE TABLE user_interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            interest_name TEXT NOT NULL,
            is_predefined BOOLEAN NOT NULL DEFAULT 0,
            added_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Unique constraint: each user can only have each interest once
    op.execute(
        "CREATE UNIQUE INDEX idx_user_interests ON user_interests(user_id, interest_name)"
    )


def downgrade() -> None:
    """Drop user_interests table and indexes."""
    op.execute("DROP INDEX IF EXISTS idx_user_interests")
    op.execute("DROP TABLE IF EXISTS user_interests")
