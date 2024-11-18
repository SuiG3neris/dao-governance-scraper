"""
Blockchain data scraper for Ethereum networks.
"""

import logging
from typing import Dict, Any, List, Optional, Generator, Union
from datetime import datetime
import time

from web3 import Web3
from web3.exceptions import TransactionNotFound, ContractLogicError
import requests
from eth_utils import is_checksum_address, to_checksum_address

from src.utils.blockchain_utils import BlockchainUtils
from src.utils.helpers import RateLimiter, retry_with_backoff

class ChainScraper:
    """Scraper for blockchain data."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize chain scraper with configuration."""
        self.config = config['blockchain']
        self.utils = BlockchainUtils(config)
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(
            self.config['web3']['provider_url'],
            request_kwargs={'timeout': self.config['web3']['timeout']}
        ))
        
        # Validate connection
        if not self.w3.is_connected():
            raise ConnectionError("Could not connect to Ethereum node")
            
        # Initialize rate limiters
        self.etherscan_limiter = RateLimiter(
            calls=self.config['etherscan']['rate_limit']['calls_per_second'],
            period=1
        )
    
    @retry_with_backoff(retries=3)
    def _make_etherscan_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make rate-limited request to Etherscan API.
        
        Args:
            params: Request parameters
            
        Returns:
            API response data
            
        Raises:
            requests.exceptions.RequestException: If request fails
        """
        @self.etherscan_limiter
        def _request():
            url = self.config['etherscan']['api_url']
            params['apikey'] = self.utils._get_etherscan_api_key()
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data['status'] != '1':
                raise Exception(f"Etherscan API error: {data.get('message', 'Unknown error')}")
                
            return data['result']
            
        return _request()
    
    def get_token_holders(
        self,
        token_address: str,
        min_balance: float = 0,
        page: int = 1,
        offset: int = 1000
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Get token holder data.
        
        Args:
            token_address: Token contract address
            min_balance: Minimum token balance to include
            page: Page number for pagination
            offset: Number of results per page
            
        Yields:
            Token holder information
        """
        token_address = self.utils.validate_address(token_address)
        token_contract = self.utils.get_contract(token_address)
        
        try:
            # Get token metadata
            decimals = token_contract.functions.decimals().call()
            symbol = token_contract.functions.symbol().call()
            name = token_contract.functions.name().call()
            
            # Get holders from Etherscan
            params = {
                'module': 'token',
                'action': 'tokenholderlist',
                'contractaddress': token_address,
                'page': page,
                'offset': offset
            }
            
            holders = self._make_etherscan_request(params)
            
            for holder in holders:
                balance = float(holder['TokenHolderQuantity']) / (10 ** decimals)
                if balance >= min_balance:
                    # Get delegation info if available
                    delegated_to = None
                    delegated_balance = 0
                    try:
                        if hasattr(token_contract.functions, 'delegates'):
                            delegated_to = token_contract.functions.delegates(
                                holder['TokenHolderAddress']
                            ).call()
                            
                            if delegated_to != '0x' + '0' * 40:
                                delegated_balance = token_contract.functions.getVotes(
                                    holder['TokenHolderAddress']
                                ).call() / (10 ** decimals)
                    except ContractLogicError:
                        logging.debug(f"Contract does not support delegation for {holder['TokenHolderAddress']}")
                    
                    yield {
                        'address': holder['TokenHolderAddress'],
                        'balance': balance,
                        'delegated_to': delegated_to,
                        'delegated_balance': delegated_balance,
                        'timestamp': datetime.now(),
                        'token_address': token_address,
                        'token_symbol': symbol,
                        'token_name': name
                    }
                    
        except Exception as e:
            logging.error(f"Error fetching token holders: {e}")
            raise
    
    def get_token_transfers(
        self,
        token_address: str,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Get token transfer events.
        
        Args:
            token_address: Token contract address
            start_block: Starting block number
            end_block: Ending block number
            
        Yields:
            Transfer event information
        """
        token_address = self.utils.validate_address(token_address)
        token_contract = self.utils.get_contract(token_address)
        
        try:
            # Get token metadata
            decimals = token_contract.functions.decimals().call()
            symbol = token_contract.functions.symbol().call()
            name = token_contract.functions.name().call()
            
            # Get transfer events
            transfer_filter = token_contract.events.Transfer.create_filter(
                fromBlock=start_block or 'earliest',
                toBlock=end_block or 'latest'
            )
            
            try:
                events = transfer_filter.get_all_entries()
                
                for event in events:
                    block = self.w3.eth.get_block(event['blockNumber'])
                    
                    yield {
                        'transaction_hash': event['transactionHash'].hex(),
                        'block_number': event['blockNumber'],
                        'from_address': event['args']['from'],
                        'to_address': event['args']['to'],
                        'amount': float(event['args']['value']) / (10 ** decimals),
                        'timestamp': datetime.fromtimestamp(block['timestamp']),
                        'token_address': token_address,
                        'token_symbol': symbol,
                        'token_name': name
                    }
            finally:
                transfer_filter.uninstall()
                
        except Exception as e:
            logging.error(f"Error fetching token transfers: {e}")
            raise
    
    def get_governance_events(
        self,
        contract_address: str,
        event_names: Optional[List[str]] = None,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Get governance contract events.
        
        Args:
            contract_address: Governance contract address
            event_names: List of event names to filter
            start_block: Starting block number
            end_block: Ending block number
            
        Yields:
            Event information
        """
        contract_address = self.utils.validate_address(contract_address)
        contract = self.utils.get_contract(contract_address)
        
        try:
            # Get all events if no specific events requested
            if not event_names:
                event_names = [e for e in contract.events]
                
            # Create filters for each event
            filters = []
            for name in event_names:
                if hasattr(contract.events, name):
                    event = getattr(contract.events, name)
                    filters.append(event.create_filter(
                        fromBlock=start_block or 'earliest',
                        toBlock=end_block or 'latest'
                    ))
                else:
                    logging.warning(f"Event {name} not found in contract")
            
            try:
                # Process all events
                for filter in filters:
                    events = filter.get_all_entries()
                    
                    for event in events:
                        block = self.w3.eth.get_block(event['blockNumber'])
                        decoded = self.utils.decode_event_log(contract, event)
                        
                        yield {
                            'transaction_hash': event['transactionHash'].hex(),
                            'block_number': event['blockNumber'],
                            'log_index': event['logIndex'],
                            'event_name': decoded['event'],
                            'args': decoded['args'],
                            'timestamp': datetime.fromtimestamp(block['timestamp']),
                            'contract_address': contract_address
                        }
            finally:
                for filter in filters:
                    filter.uninstall()
                    
        except Exception as e:
            logging.error(f"Error fetching governance events: {e}")
            raise
    
    def verify_proposal_votes(
        self,
        proposal_id: str
    ) -> List[Dict[str, Any]]:
        """
        Verify votes for a proposal on-chain.
        
        Args:
            proposal_id: Proposal ID to verify
            
        Returns:
            List of verified vote information
        """
        try:
            # Get proposal from database first
            # This would require database integration
            ...  # TODO: Implement database lookup
            
            # Get vote events from contract
            governor_address = self.config['contracts']['governor_contract']
            governor = self.utils.get_contract(governor_address)
            
            vote_cast_filter = governor.events.VoteCast.create_filter(
                fromBlock='earliest',
                toBlock='latest'
            )
            
            verified_votes = []
            try:
                events = vote_cast_filter.get_all_entries()
                
                for event in events:
                    if event['args']['proposalId'] == proposal_id:
                        block = self.w3.eth.get_block(event['blockNumber'])
                        
                        verified_votes.append({
                            'proposal_id': proposal_id,
                            'voter': event['args']['voter'],
                            'support': event['args']['support'],
                            'votes': float(event['args']['votes']),
                            'transaction_hash': event['transactionHash'].hex(),
                            'block_number': event['blockNumber'],
                            'timestamp': datetime.fromtimestamp(block['timestamp']),
                            'verified': True
                        })
                        
            finally:
                vote_cast_filter.uninstall()
                
            return verified_votes
            
        except Exception as e:
            logging.error(f"Error verifying proposal votes: {e}")
            raise