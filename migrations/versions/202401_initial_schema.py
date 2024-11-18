"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create spaces table
    op.create_table(
        'space',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('about', sa.Text(), nullable=True),
        sa.Column('network', sa.String(50), nullable=False, server_default='ethereum'),
        sa.Column('symbol', sa.String(20), nullable=True),
        sa.Column('members', sa.Integer(), server_default='0'),
        sa.Column('proposals_count', sa.Integer(), server_default='0'),
        sa.Column('followers', sa.Integer(), server_default='0'),
        sa.Column('raw_data', sqlite.JSON, nullable=True)
    )
    op.create_index('ix_space_name', 'space', ['name'])
    op.create_index('ix_space_network', 'space', ['network'])
    
    # Create proposals table
    op.create_table(
        'proposal',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('space_id', sa.String(100), sa.ForeignKey('space.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('choices', sqlite.JSON, nullable=False),
        sa.Column('author', sa.String(100), nullable=False),
        sa.Column('start', sa.DateTime(), nullable=False),
        sa.Column('end', sa.DateTime(), nullable=False),
        sa.Column('state', sa.String(50), server_default='pending'),
        sa.Column('votes_count', sa.Integer(), server_default='0'),
        sa.Column('scores_total', sa.Float(), server_default='0.0'),
        sa.Column('raw_data', sqlite.JSON, nullable=True)
    )
    op.create_index('ix_proposal_space_id', 'proposal', ['space_id'])
    op.create_index('ix_proposal_state', 'proposal', ['state'])
    op.create_index('ix_proposal_start', 'proposal', ['start'])
    op.create_index('ix_proposal_end', 'proposal', ['end'])
    
    # Create votes table
    op.create_table(
        'vote',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('proposal_id', sa.String(100), sa.ForeignKey('proposal.id'), nullable=False),
        sa.Column('voter', sa.String(100), nullable=False),
        sa.Column('choice', sa.Integer(), nullable=False),
        sa.Column('voting_power', sa.Float(), server_default='0.0'),
        sa.Column('raw_data', sqlite.JSON, nullable=True)
    )
    op.create_index('ix_vote_proposal_id', 'vote', ['proposal_id'])
    op.create_index('ix_vote_voter', 'vote', ['voter'])

def downgrade() -> None:
    op.drop_table('vote')
    op.drop_table('proposal')
    op.drop_table('space')