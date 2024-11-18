"""
Unit tests for blockchain scraper functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from web3.exceptions import TransactionNotFound, ContractLogicError

from src.scraper.chain_scraper import ChainScraper
from src.utils.blockchain_utils import BlockchainUtils

@pytest.fixture
def mock_config():
    """Provide test configuration."""
    return {
        'blockchain': {
            'etherscan': {
                'api_url': 'https://api.etherscan.io/api',
                'rate_limit': {
                    'calls_per_second': 5,
                    'max_requests_per_day': 100000
                }
            },
            'web3': {
                'provider_url': 'https://mainnet.infura.io/v3/your-project-id',
                'timeout': 30
            },
            'contracts': {
                'governance_registry': '0x123...',
                'token_contract': '0x456...',
                'governor_contract': '0x789...'
            },
            'abi': {
                'cache_dir': 'tests/data/abi_cache'
            }
        }
    }

@pytest.fixture
def chain_scraper(mock_config):
    """Provide configured chain scraper instance."""
    with patch('web3.Web3.HTTPProvider'), \
         patch('web3.Web3.is_connected', return_value=True):
        return ChainScraper(mock_config)

def test_validate_address(chain_scraper):
    """Test Ethereum address validation."""
    # Valid checksum address
    valid_address = '0x742d35Cc6634C0532925a3b844Bc454e4438f44e'
    assert chain_scraper.utils.validate_address(valid_address) == valid_address
    
    # Valid lowercase address should be converted to checksum
    lowercase = '0x742d35cc6634c0532925a3b844bc454e4438f44e'
    assert chain_scraper.utils.validate_address(lowercase) == valid_address
    
    # Invalid address should raise ValueError
    with pytest.raises(ValueError):
        chain_scraper.utils.validate_address('0xinvalid')

def test_get_token_holders(chain_scraper):
    """Test token holder data fetching."""
    mock_contract = Mock()
    mock_contract.functions.decimals.return_value.call.return_value = 18
    mock_contract.functions.symbol.return_value.call.return_value = 'TEST'
    mock_contract.functions.name.return_value.call.return_value = 'Test Token'
    
    with patch.object(chain_scraper.utils, 'get_contract', return_value=mock_contract), \
         patch.object(chain_scraper, '_make_etherscan_request') as mock_request:
            
        mock_request.return_value = [
            {
                'TokenHolderAddress': '0x123...',
                'TokenHolderQuantity': '1000000000000000000000',  # 1000 tokens
                'Share': '10.5'
            }
        ]
        
        holders = list(chain_scraper.get_token_holders('0x742d35Cc6634C0532925a3b844Bc454e4438f44e'))
        
        assert len(holders) == 1
        assert holders[0]['balance'] == 1000.0
        assert holders[0]['token_symbol'] == 'TEST'

def test_get_token_transfers(chain_scraper):
    """Test token transfer event fetching."""
    mock_contract = Mock()
    mock_contract.functions.decimals.return_value.call.return_value = 18
    mock_contract.functions.symbol.return_value.call.return_value = 'TEST'
    mock_contract.functions.name.return_value.call.return_value = 'Test Token'
    
    mock_event = {
        'args': {
            'from': '0x123...',
            'to': '0x456...',
            'value': 1000000000000000000  # 1 token
        },
        'blockNumber': 1000000,
        'transactionHash': b'123...',
        'logIndex': 0
    }
    
    mock_filter = Mock()
    mock_filter.get_all_entries.return_value = [mock_event]
    mock_contract.events.Transfer.create_filter.return_value = mock_filter
    
    with patch.object(chain_scraper.utils, 'get_contract', return_value=mock_contract), \
         patch.object(chain_scraper.w3.eth, 'get_block') as mock_get_block:
            
        mock_get_block.return_value = {'timestamp': 1600000000}
        
        transfers = list(chain_scraper.get_token_transfers('0x742d35Cc6634C0532925a3b844Bc454e4438f44e'))
        
        assert len(transfers) == 1
        assert transfers[0]['from_address'] == '0x123...'
        assert transfers[0]['to_address'] == '0x456...'
        assert transfers[0]['amount'] == 1.0

def test_get_governance_events(chain_scraper):
    """Test governance event fetching."""
    mock_contract = Mock()
    mock_event = {
        'event': 'ProposalCreated',
        'args': {
            'proposalId': '1',
            'proposer': '0x123...',
            'description': 'Test proposal'
        },
        'blockNumber': 1000000,
        'transactionHash': b'123...',
        'logIndex': 0
    }
    
    mock_filter = Mock()
    mock_filter.get_all_entries.return_value = [mock_event]
    mock_contract.events.ProposalCreated.create_filter.return_value = mock_filter
    
    with patch.object(chain_scraper.utils, 'get_contract', return_value=mock_contract), \
         patch.object(chain_scraper.w3.eth, 'get_block') as mock_get_block, \
         patch.object(chain_scraper.utils, 'decode_event_log') as mock_decode:
            
        mock_get_block.return_value = {'timestamp': 1600000000}
        mock_decode.return_value = {
            'event': 'ProposalCreated',
            'args': mock_event['args'],
            'block_number': mock_event['blockNumber']
        }
        
        events = list(chain_scraper.get_governance_events(
            '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
            event_names=['ProposalCreated']
        ))
        
        assert len(events) == 1
        assert events[0]['event_name'] == 'ProposalCreated'
        assert events[0]['args']['proposalId'] == '1'

def test_error_handling(chain_scraper):
    """Test error handling scenarios."""
    # Test rate limit error
    with patch.object(chain_scraper, '_make_etherscan_request') as mock_request, \
         pytest.raises(Exception) as exc_info:
            
        mock_request.side_effect = Exception("Max rate limit reached")
        list(chain_scraper.get_token_holders('0x742d35Cc6634C0532925a3b844Bc454e4438f44e'))
        assert "rate limit" in str(exc_info.value).lower()
    
    # Test invalid contract error
    with patch.object(chain_scraper.utils, 'get_contract') as mock_get_contract, \
         pytest.raises(ContractLogicError):
            
        mock_get_contract.side_effect = ContractLogicError("Invalid contract")
        list(chain_scraper.get_token_transfers('0x742d35Cc6634C0532925a3b844Bc454e4438f44e'))
    
    # Test network error
    with patch.object(chain_scraper.w3.eth, 'get_block') as mock_get_block, \
         pytest.raises(Exception) as exc_info:
            
        mock_get_block.side_effect = TransactionNotFound("Block not found")
        list(chain_scraper.get_governance_events('0x742d35Cc6634C0532925a3b844Bc454e4438f44e'))
        assert "not found" in str(exc_info.value).lower()

@pytest.mark.integration
def test_full_chain_integration(chain_scraper):
    """Integration test with real blockchain data."""
    # Skip by default as it requires network access
    pytest.skip("Integration test requiring blockchain access")