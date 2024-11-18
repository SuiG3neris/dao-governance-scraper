"""
Unit tests for Snapshot scraper.
"""

import pytest
from unittest.mock import Mock, patch
from src.scraper.snapshot_scraper import SnapshotScraper
from src.database.models import SnapshotSpace, SnapshotProposal, SnapshotVote

@pytest.fixture
def mock_config():
    """Provide test configuration."""
    return {
        'scraping': {
            'snapshot': {
                'api_endpoint': 'https://hub.snapshot.org/graphql',
                'batch_size': 100,
                'rate_limits': {
                    'proposals_per_minute': 30,
                    'votes_per_minute': 60,
                    'spaces_per_minute': 20
                }
            }
        },
        'storage': {
            'raw_data_path': 'tests/data/raw',
            'processed_data_path': 'tests/data/processed'
        }
    }

@pytest.fixture
def scraper(mock_config):
    """Provide configured scraper instance."""
    return SnapshotScraper(mock_config)

def test_make_request(scraper):
    """Test API request functionality."""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {'data': {'test': 'value'}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = scraper._make_request('test query')
        
        assert result == {'data': {'test': 'value'}}
        mock_post.assert_called_once()

def test_get_spaces(scraper):
    """Test space fetching functionality."""
    mock_response = {
        'data': {
            'spaces': [
                {
                    'id': 'test-dao',
                    'name': 'Test DAO',
                    'about': 'Test description',
                    'network': 'ethereum',
                    'symbol': 'TEST',
                    'members': 100,
                    'proposalsCount': 10,
                    'followers': 50,
                    'created': 1633027200
                }
            ]
        }
    }
    
    with patch.object(scraper, '_make_request') as mock_request:
        mock_request.return_value = mock_response
        spaces = list(scraper.get_spaces())
        
        assert len(spaces) == 1
        assert isinstance(spaces[0], SnapshotSpace)
        assert spaces[0].id == 'test-dao'
        assert spaces[0].name == 'Test DAO'

def test_get_proposals(scraper):
    """Test proposal fetching functionality."""
    mock_response = {
        'data': {
            'proposals': [
                {
                    'id': 'proposal-1',
                    'space': {'id': 'test-dao'},
                    'title': 'Test Proposal',
                    'body': 'Test body',
                    'choices': ['Yes', 'No'],
                    'start': 1633027200,
                    'end': 1633113600,
                    'state': 'active',
                    'author': '0x123...',
                    'votes': 5,
                    'scores_total': 1000.0
                }
            ]
        }
    }
    
    with patch.object(scraper, '_make_request') as mock_request:
        mock_request.return_value = mock_response
        proposals = list(scraper.get_proposals('test-dao'))
        
        assert len(proposals) == 1
        assert isinstance(proposals[0], SnapshotProposal)
        assert proposals[0].id == 'proposal-1'
        assert proposals[0].space_id == 'test-dao'

@pytest.mark.skip(reason="Integration test requiring API access")
def test_full_scrape_integration(scraper):
    """Integration test for full scraping process."""
    space_id = 'test-dao'
    result = scraper.scrape_space(space_id)
    
    assert 'proposals' in result
    assert 'votes' in result
    assert all(isinstance(p, SnapshotProposal) for p in result['proposals'])
    assert all(isinstance(v, SnapshotVote) for v in result['votes'])