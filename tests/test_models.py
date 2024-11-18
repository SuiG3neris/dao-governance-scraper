"""
Unit tests for data models.
"""

import pytest
from datetime import datetime
from src.database.models import SnapshotSpace, SnapshotProposal, SnapshotVote

def test_snapshot_space_creation():
    """Test SnapshotSpace model creation and serialization."""
    space_data = {
        'id': 'test-dao',
        'name': 'Test DAO',
        'about': 'A test DAO',
        'network': 'ethereum',
        'symbol': 'TEST',
        'members': 100,
        'proposalsCount': 10,
        'followers': 50,
        'created': 1633027200  # 2021-10-01
    }
    
    space = SnapshotSpace.from_json(space_data)
    
    assert space.id == 'test-dao'
    assert space.name == 'Test DAO'
    assert space.members == 100
    assert space.proposals_count == 10
    
    # Test serialization
    json_data = space.to_json()
    assert json_data['id'] == space.id
    assert json_data['name'] == space.name
    assert isinstance(json_data['created_at'], int)

def test_snapshot_proposal_creation():
    """Test SnapshotProposal model creation."""
    proposal_data = {
        'id': 'proposal-1',
        'space': {'id': 'test-dao'},
        'title': 'Test Proposal',
        'body': 'Test proposal body',
        'choices': ['Yes', 'No'],
        'start': 1633027200,
        'end': 1633113600,
        'state': 'active',
        'author': '0x123...',
        'votes': 5,
        'scores_total': 1000.0
    }
    
    proposal = SnapshotProposal.from_json(proposal_data)
    
    assert proposal.id == 'proposal-1'
    assert proposal.space_id == 'test-dao'
    assert proposal.title == 'Test Proposal'
    assert len(proposal.choices) == 2
    assert proposal.state == 'active'

def test_snapshot_vote_creation():
    """Test SnapshotVote model creation."""
    vote_data = {
        'id': 'vote-1',
        'proposal': {'id': 'proposal-1'},
        'voter': '0x123...',
        'choice': 1,
        'vp': 100.5,
        'created': 1633027200
    }
    
    vote = SnapshotVote.from_json(vote_data)
    
    assert vote.id == 'vote-1'
    assert vote.proposal_id == 'proposal-1'
    assert vote.choice == 1
    assert vote.voting_power == 100.5
    
    # Test serialization
    json_data = vote.to_json()
    assert json_data['id'] == vote.id
    assert json_data['proposal_id'] == vote.proposal_id
    assert isinstance(json_data['timestamp'], int)

def test_invalid_data_handling():
    """Test handling of invalid or missing data."""
    # Test with missing required fields
    invalid_space_data = {'name': 'Test DAO'}
    with pytest.raises(Exception):
        SnapshotSpace.from_json(invalid_space_data)
    
    # Test with invalid types
    invalid_vote_data = {
        'id': 'vote-1',
        'proposal': {'id': 'proposal-1'},
        'voter': '0x123...',
        'choice': 'invalid',  # Should be int
        'vp': '100.5',  # Should be float
        'created': '1633027200'  # Should be int
    }
    
    with pytest.raises(ValueError):
        SnapshotVote.from_json(invalid_vote_data)