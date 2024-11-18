"""Add blockchain tables and relationships

Revision ID: 003
Revises: 002
Create Date: 2024-01-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create token holders table
    op.create_table(
        'token_holder',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('address', sa.String(42), nullable=False),
        sa.Column('balance', sa.Float(), nullable=False, default=0.0),
        sa.Column('delegated_balance', sa.Float(), nullable=False, default=0.0),
        sa.Column('total_voting_power', sa.Float(), nullable=False, default=0.0),
        sa.Column('delegating_to', sa.String(42), nullable=True),
        sa.Column('delegate_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_transfer_block', sa.Integer(), nullable=True),
        sa.Column('last_delegation_block', sa.Integer(), nullable=True),
        sa.Column('raw_data', sqlite.JSON, nullable=True)
    )
    op.create_index('ix_token_holder_address', 'token_holder', ['address'])
    op.create_index('ix_token_holder_balance', 'token_holder', ['balance'])
    op.create_index('ix_token_holder_voting_power', 'token_holder', ['total_voting_power'])

    # Create token transfers table
    op.create_table(
        'token_transfer',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('transaction_hash', sa.String(66), nullable=False),
        sa.Column('block_number', sa.Integer(), nullable=False),
        sa.Column('from_address', sa.String(42), nullable=False),
        sa.Column('to_address', sa.String(42), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('token_symbol', sa.String(10), nullable=False),
        sa.Column('token_name', sa.String(100), nullable=False),
        sa.Column('raw_data', sqlite.JSON, nullable=True)
    )
    op.create_index('ix_token_transfer_tx_hash', 'token_transfer', ['transaction_hash'])
    op.create_index('ix_token_transfer_block', 'token_transfer', ['block_number'])
    op.create_index('ix_token_transfer_from', 'token_transfer', ['from_address'])
    op.create_index('ix_token_transfer_to', 'token_transfer', ['to_address'])

    # Create governance events table
    op.create_table(
        'governance_event',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('event_name', sa.String(100), nullable=False),
        sa.Column('transaction_hash', sa.String(66), nullable=False),
        sa.Column('block_number', sa.Integer(), nullable=False),
        sa.Column('log_index', sa.Integer(), nullable=False),
        sa.Column('contract_address', sa.String(42), nullable=False),
        sa.Column('proposal_id', sa.String(100), sa.ForeignKey('proposal.id'), nullable=True),
        sa.Column('args', sqlite.JSON, nullable=False),
        sa.Column('raw_data', sqlite.JSON, nullable=True)
    )
    op.create_index('ix_governance_event_tx_hash', 'governance_event', ['transaction_hash'])
    op.create_index('ix_governance_event_block', 'governance_event', ['block_number'])
    op.create_index('ix_governance_event_name', 'governance_event', ['event_name'])
    op.create_index('ix_governance_event_proposal', 'governance_event', ['proposal_id'])

    # Add blockchain verification fields to existing tables
    with op.batch_alter_table('proposal') as batch_op:
        batch_op.add_column(sa.Column('transaction_hash', sa.String(66), nullable=True))
        batch_op.add_column(sa.Column('block_number', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('verified_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('contract_address', sa.String(42), nullable=True))
        batch_op.create_index('ix_proposal_tx_hash', ['transaction_hash'])
        batch_op.create_index('ix_proposal_block', ['block_number'])

    with op.batch_alter_table('vote') as batch_op:
        batch_op.add_column(sa.Column('transaction_hash', sa.String(66), nullable=True))
        batch_op.add_column(sa.Column('block_number', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('verified_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('verified_voter', sa.String(42), nullable=True))
        batch_op.create_index('ix_vote_tx_hash', ['transaction_hash'])
        batch_op.create_index('ix_vote_block', ['block_number'])

def downgrade() -> None:
    # Remove blockchain verification fields
    with op.batch_alter_table('vote') as batch_op:
        batch_op.drop_index('ix_vote_tx_hash')
        batch_op.drop_index('ix_vote_block')
        batch_op.drop_column('transaction_hash')
        batch_op.drop_column('block_number')
        batch_op.drop_column('verified_at')
        batch_op.drop_column('verified_voter')

    with op.batch_alter_table('proposal') as batch_op:
        batch_op.drop_index('ix_proposal_tx_hash')
        batch_op.drop_index('ix_proposal_block')
        batch_op.drop_column('transaction_hash')
        batch_op.drop_column('block_number')
        batch_op.drop_column('verified_at')
        batch_op.drop_column('contract_address')

    # Drop blockchain tables
    op.drop_table('governance_event')
    op.drop_table('token_transfer')
    op.drop_table('token_holder')