"""initial schema with permissions_json

Revision ID: f5b0feccbc5d
Revises:
Create Date: 2026-02-20 08:11:23.410406
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5b0feccbc5d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline migration — all tables already exist in production.
    pass


def downgrade() -> None:
    pass
