"""create_users_table

Revision ID: 912ab51a9dcd
Revises:
Create Date: 2025-10-22 12:49:20.201986

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "912ab51a9dcd"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table with avatar support."""
    op.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            avatar_path TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)


def downgrade() -> None:
    """Drop users table."""
    op.execute("DROP TABLE IF EXISTS users")
