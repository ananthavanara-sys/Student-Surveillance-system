"""Initial database schema for face recognition system

Revision ID: 001_initial
Revises: 
Create Date: 2025-10-16 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables."""
    # Create persons table
    op.create_table(
        'persons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_persons_id'), 'persons', ['id'], unique=False)
    op.create_index(op.f('ix_persons_name'), 'persons', ['name'], unique=True)
    
    # Create face_embeddings table
    op.create_table(
        'face_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column('quality_score', sa.Float(), nullable=False),
        sa.Column('det_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_face_embeddings_id'), 'face_embeddings', ['id'], unique=False)
    op.create_index(op.f('ix_face_embeddings_person_id'), 'face_embeddings', ['person_id'], unique=False)
    op.create_index('idx_person_embeddings', 'face_embeddings', ['person_id', 'quality_score'], unique=False)
    
    # Create attendance_log table
    op.create_table(
        'attendance_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('recognized_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='Present'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('person_id', 'recognized_at', name='uq_person_date')
    )
    op.create_index(op.f('ix_attendance_log_id'), 'attendance_log', ['id'], unique=False)
    op.create_index(op.f('ix_attendance_log_person_id'), 'attendance_log', ['person_id'], unique=False)
    op.create_index(op.f('ix_attendance_log_recognized_at'), 'attendance_log', ['recognized_at'], unique=False)
    op.create_index('idx_person_date', 'attendance_log', ['person_id', 'recognized_at'], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index('idx_person_date', table_name='attendance_log')
    op.drop_index(op.f('ix_attendance_log_recognized_at'), table_name='attendance_log')
    op.drop_index(op.f('ix_attendance_log_person_id'), table_name='attendance_log')
    op.drop_index(op.f('ix_attendance_log_id'), table_name='attendance_log')
    op.drop_table('attendance_log')
    
    op.drop_index('idx_person_embeddings', table_name='face_embeddings')
    op.drop_index(op.f('ix_face_embeddings_person_id'), table_name='face_embeddings')
    op.drop_index(op.f('ix_face_embeddings_id'), table_name='face_embeddings')
    op.drop_table('face_embeddings')
    
    op.drop_index(op.f('ix_persons_name'), table_name='persons')
    op.drop_index(op.f('ix_persons_id'), table_name='persons')
    op.drop_table('persons')
