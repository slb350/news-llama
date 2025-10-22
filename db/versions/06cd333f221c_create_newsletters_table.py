"""create_newsletters_table

Revision ID: 06cd333f221c
Revises: 912ab51a9dcd
Create Date: 2025-10-22 12:49:45.789136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06cd333f221c'
down_revision: Union[str, Sequence[str], None] = '912ab51a9dcd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create newsletters table with status tracking and retry logic."""
    op.execute("""
        CREATE TABLE newsletters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            guid TEXT NOT NULL UNIQUE,
            file_path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            generated_at TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CHECK (status IN ('pending', 'generating', 'completed', 'failed'))
        )
    """)

    # Create indexes for performance
    op.execute("CREATE INDEX idx_newsletters_user_date ON newsletters(user_id, date DESC)")
    op.execute("CREATE INDEX idx_newsletters_status ON newsletters(status)")


def downgrade() -> None:
    """Drop newsletters table and indexes."""
    op.execute("DROP INDEX IF EXISTS idx_newsletters_status")
    op.execute("DROP INDEX IF EXISTS idx_newsletters_user_date")
    op.execute("DROP TABLE IF EXISTS newsletters")
