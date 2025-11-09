"""add stage to source

Revision ID: c6d7e8f9a0b1
Revises: b1f2e3d4c5a6
Create Date: 2025-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6d7e8f9a0b1'
down_revision: Union[str, None] = 'b1f2e3d4c5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add stage column with default value
    op.add_column('source', sa.Column('stage', sa.String(), nullable=True))

    # Set default value for existing rows
    op.execute("UPDATE source SET stage = 'uploaded' WHERE stage IS NULL")

    # Make column non-nullable after setting defaults
    op.alter_column('source', 'stage', nullable=False, server_default='uploaded')


def downgrade() -> None:
    op.drop_column('source', 'stage')
