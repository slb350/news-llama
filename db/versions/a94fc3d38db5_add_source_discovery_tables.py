"""add_source_discovery_tables

Revision ID: a94fc3d38db5
Revises: 530f841606fd
Create Date: 2025-10-23 16:15:26.607510

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a94fc3d38db5"
down_revision: Union[str, Sequence[str], None] = "530f841606fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source discovery tables for autonomous discovery system."""
    # tier1_sources
    op.create_table(
        "tier1_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("interests", sa.Text(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("discovered_at", sa.Text(), nullable=False),
        sa.Column("discovered_via", sa.Text(), nullable=False),
        sa.Column("last_health_check", sa.Text(), nullable=True),
        sa.Column("is_healthy", sa.Boolean(), server_default="1", nullable=True),
        sa.Column("avg_posts_per_day", sa.Float(), nullable=True),
        sa.Column("domain_age_years", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type", "source_key", name="uq_tier1_source_type_key"
        ),
    )
    op.create_index("idx_tier1_healthy", "tier1_sources", ["is_healthy", "source_type"])
    op.create_index("idx_tier1_interests", "tier1_sources", ["interests"])

    # source_blacklist
    op.create_table(
        "source_blacklist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("blacklisted_at", sa.Text(), nullable=False),
        sa.Column("blacklisted_reason", sa.Text(), nullable=False),
        sa.Column("failure_count", sa.Integer(), server_default="1", nullable=True),
        sa.Column("last_failure_at", sa.Text(), nullable=False),
        sa.Column("last_attempted_resurrection", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type", "source_key", name="uq_blacklist_source_type_key"
        ),
    )
    op.create_index("idx_blacklist_type", "source_blacklist", ["source_type"])

    # discovered_sources
    op.create_table(
        "discovered_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("discovered_at", sa.Text(), nullable=False),
        sa.Column("discovered_via", sa.Text(), nullable=False),
        sa.Column("discovery_count", sa.Integer(), server_default="1", nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("health_check_passed", sa.Boolean(), nullable=True),
        sa.Column("promoted_to_tier1", sa.Boolean(), server_default="0", nullable=True),
        sa.Column("interests", sa.Text(), nullable=False),
        sa.Column("source_metadata", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type", "source_key", name="uq_discovered_source_type_key"
        ),
    )
    op.create_index(
        "idx_discovered_promoted", "discovered_sources", ["promoted_to_tier1"]
    )

    # source_health
    op.create_table(
        "source_health",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("last_check_at", sa.Text(), nullable=False),
        sa.Column("last_success_at", sa.Text(), nullable=True),
        sa.Column("last_failure_at", sa.Text(), nullable=True),
        sa.Column(
            "consecutive_failures", sa.Integer(), server_default="0", nullable=True
        ),
        sa.Column(
            "consecutive_successes", sa.Integer(), server_default="0", nullable=True
        ),
        sa.Column("is_healthy", sa.Boolean(), server_default="1", nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("articles_found", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type", "source_key", name="uq_health_source_type_key"
        ),
    )
    op.create_index(
        "idx_health_status", "source_health", ["is_healthy", "consecutive_failures"]
    )

    # source_contributions
    op.create_table(
        "source_contributions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("newsletter_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column(
            "articles_collected", sa.Integer(), server_default="0", nullable=True
        ),
        sa.Column("articles_included", sa.Integer(), server_default="0", nullable=True),
        sa.Column("collected_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["newsletter_id"], ["newsletters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_contributions_newsletter", "source_contributions", ["newsletter_id"]
    )
    op.create_index(
        "idx_contributions_source",
        "source_contributions",
        ["source_type", "source_key"],
    )
    op.create_index("idx_contributions_date", "source_contributions", ["collected_at"])


def downgrade() -> None:
    """Remove source discovery tables."""
    op.drop_table("source_contributions")
    op.drop_table("source_health")
    op.drop_table("discovered_sources")
    op.drop_table("source_blacklist")
    op.drop_table("tier1_sources")
