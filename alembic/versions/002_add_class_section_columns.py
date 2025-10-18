"""Add class_name and section_name columns to persons table

Revision ID: 002_class_section
Revises: 001_initial
Create Date: 2025-01-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_class_section'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add class_name and section_name columns to persons table for filtering optimization."""
    # Add class_name column
    op.add_column('persons', sa.Column('class_name', sa.String(length=50), nullable=True))
    
    # Add section_name column
    op.add_column('persons', sa.Column('section_name', sa.String(length=10), nullable=True))
    
    # Create indexes for efficient filtering
    op.create_index(op.f('ix_persons_class_name'), 'persons', ['class_name'], unique=False)
    op.create_index(op.f('ix_persons_section_name'), 'persons', ['section_name'], unique=False)
    
    # Optional: Create composite index for combined class+section queries
    op.create_index('idx_persons_class_section', 'persons', ['class_name', 'section_name'], unique=False)


def downgrade() -> None:
    """Remove class_name and section_name columns from persons table."""
    # Drop indexes first
    op.drop_index('idx_persons_class_section', table_name='persons')
    op.drop_index(op.f('ix_persons_section_name'), table_name='persons')
    op.drop_index(op.f('ix_persons_class_name'), table_name='persons')
    
    # Drop columns
    op.drop_column('persons', 'section_name')
    op.drop_column('persons', 'class_name')
