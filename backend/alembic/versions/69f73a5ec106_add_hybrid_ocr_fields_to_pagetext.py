"""add_hybrid_ocr_fields_to_pagetext

Revision ID: 69f73a5ec106
Revises: c6d7e8f9a0b1
Create Date: 2025-11-20 17:15:09.571008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69f73a5ec106'
down_revision: Union[str, Sequence[str], None] = 'c6d7e8f9a0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add hybrid OCR fields to pagetext table."""
    # Add columns for storing dual OCR results
    op.add_column('pagetext', sa.Column('ocr_source', sa.String(), nullable=True))
    op.add_column('pagetext', sa.Column('tesseract_text', sa.String(), nullable=True))
    op.add_column('pagetext', sa.Column('ollama_text', sa.String(), nullable=True))
    op.add_column('pagetext', sa.Column('tesseract_confidence', sa.Float(), nullable=True))
    op.add_column('pagetext', sa.Column('ollama_confidence', sa.Float(), nullable=True))
    op.add_column('pagetext', sa.Column('selected_source', sa.String(), nullable=True))

    # Migrate existing data: copy 'text' to 'tesseract_text' and set ocr_source
    op.execute("""
        UPDATE pagetext
        SET tesseract_text = text,
            ocr_source = 'tesseract',
            tesseract_confidence = confidence,
            selected_source = 'tesseract'
        WHERE tesseract_text IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema: Remove hybrid OCR fields from pagetext table."""
    op.drop_column('pagetext', 'selected_source')
    op.drop_column('pagetext', 'ollama_confidence')
    op.drop_column('pagetext', 'tesseract_confidence')
    op.drop_column('pagetext', 'ollama_text')
    op.drop_column('pagetext', 'tesseract_text')
    op.drop_column('pagetext', 'ocr_source')
