"""make_file_path_nullable

Revision ID: 530f841606fd
Revises: d8387244552e
Create Date: 2025-10-23 00:16:42.090448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '530f841606fd'
down_revision: Union[str, Sequence[str], None] = 'd8387244552e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make file_path nullable in newsletters table."""
    # SQLite doesn't support ALTER COLUMN, so we need to recreate the table

    # Create new table with nullable file_path
    op.execute("""
        CREATE TABLE newsletters_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            guid TEXT NOT NULL UNIQUE,
            file_path TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            generated_at TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CHECK (status IN ('pending', 'generating', 'completed', 'failed'))
        )
    """)

    # Copy data from old table (only completed newsletters have file_path)
    op.execute("""
        INSERT INTO newsletters_new (id, user_id, date, guid, file_path, status, generated_at, retry_count)
        SELECT id, user_id, date, guid, file_path, status, generated_at, retry_count
        FROM newsletters
    """)

    # Drop old table and indexes
    op.execute("DROP INDEX IF EXISTS idx_newsletters_status")
    op.execute("DROP INDEX IF EXISTS idx_newsletters_user_date")
    op.execute("DROP TABLE newsletters")

    # Rename new table
    op.execute("ALTER TABLE newsletters_new RENAME TO newsletters")

    # Recreate indexes
    op.execute(
        "CREATE INDEX idx_newsletters_user_date ON newsletters(user_id, date DESC)"
    )
    op.execute("CREATE INDEX idx_newsletters_status ON newsletters(status)")


def downgrade() -> None:
    """Revert file_path to NOT NULL."""
    # Create old table with NOT NULL file_path
    op.execute("""
        CREATE TABLE newsletters_old (
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

    # Copy only newsletters that have file_path (completed ones)
    op.execute("""
        INSERT INTO newsletters_old (id, user_id, date, guid, file_path, status, generated_at, retry_count)
        SELECT id, user_id, date, guid, file_path, status, generated_at, retry_count
        FROM newsletters
        WHERE file_path IS NOT NULL
    """)

    # Drop new table and indexes
    op.execute("DROP INDEX IF EXISTS idx_newsletters_status")
    op.execute("DROP INDEX IF EXISTS idx_newsletters_user_date")
    op.execute("DROP TABLE newsletters")

    # Rename old table
    op.execute("ALTER TABLE newsletters_old RENAME TO newsletters")

    # Recreate indexes
    op.execute(
        "CREATE INDEX idx_newsletters_user_date ON newsletters(user_id, date DESC)"
    )
    op.execute("CREATE INDEX idx_newsletters_status ON newsletters(status)")
