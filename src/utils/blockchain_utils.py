"""
Utility functions for blockchain data handling.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import requests
from web3 import Web3
from web3.exceptions import TransactionNotFound, BadFunctionCallOutput
from eth_utils import is_checksum_address, to_checksum_address

class BlockchainUtils:
    """Utilities for blockchain data handling."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize blockchain utilities."""
        self.config = config['blockchain']
        self.abi_cache_dir = Path(self.config['abi']['cache_dir'])
        self.abi_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(
            self.config['web3']['provider_url'],
            request_kwargs={'timeout': self.config['web3']['timeout']}
        ))
        
        # Validate connection
        if not self.w3.is_connected():
            raise ConnectionError("Could not connect to Ethereum node")
    
    def validate_address(self, address: str) -> str:
        """
        Validate and convert Ethereum address to checksum format.
        
        Args:
            address: Ethereum address to validate
            
        Returns:
            Checksum address
            
        Raises:
            ValueError: If address is invalid
        """
        try:
            if not is_checksum_address(address):
                address = to_checksum_address(address)
            return address
        except Exception as e:
            raise ValueError(f"Invalid Ethereum address: {address}") from e
    
    def get_contract_abi(self, address: str, force_update: bool = False) -> Dict:
        """
        Get contract ABI from cache or Etherscan.
        
        Args:
            address: Contract address
            force_update: Whether to force fetch from Etherscan
            
        Returns:
            Contract ABI dictionary
        """
        address = self.validate_address(address)
        cache_file = self.abi_cache_dir / f"{address}.json"
        
        # Check cache if not forcing update
        if not force_update and cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age < timedelta(hours=self.config['abi']['update_frequency_hours']):
                with open(cache_file) as f:
                    return json.load(f)
        
        # Fetch from Etherscan
        url = f"{self.config['etherscan']['api_url']}"
        params = {
            'module': 'contract',
            'action': 'getabi',
            'address': address,
            'apikey': self._get_etherscan_api_key()
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != '1':
            raise ValueError(f"Could not fetch ABI: {data['message']}")
            
        abi = json.loads(data['result'])
        
        # Cache the ABI
        with open(cache_file, 'w') as f:
            json.dump(abi, f)
        
        return abi
    
    def get_contract(self, address: str, abi: Optional[Dict] = None) -> Any:
        """
        Get Web3 contract instance.
        
        Args:
            address: Contract address
            abi: Contract ABI (optional, will fetch if not provided)
            
        Returns:
            Web3 contract instance
        """
        address = self.validate_address(address)
        if abi is None:
            abi = self.get_contract_abi(address)
        return self.w3.eth.contract(address=address, abi=abi)
    
    def decode_event_log(
        self,
        contract: Any,
        event_log: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Decode event log data.
        
        Args:
            contract: Web3 contract instance
            event_log: Raw event log
            
        Returns:
            Decoded event data
        """
        try:
            decoded = {}
            event = contract.events[event_log['event']]()
            decoded_data = event.process_log(event_log)
            
            # Extract useful information
            decoded['event'] = event_log['event']
            decoded['block_number'] = event_log['blockNumber']
            decoded['transaction_hash'] = event_log['transactionHash'].hex()
            decoded['args'] = {k: self._format_event_arg(v) for k, v in 
                              decoded_data['args'].items()}
            
            return decoded
            
        except Exception as e:
            logging.error(f"Error decoding event log: {e}")
            return event_log
    
    def _format_event_arg(self, value: Any) -> Any:
        """Format event argument for storage."""
        if isinstance(value, bytes):
            return value.hex()
        if isinstance(value, (bytes, bytearray)):
            return Web3.to_hex(value)
        return value
    
    def estimate_gas(
        self,
        contract: Any,
        fn_name: str,
        *args,
        **kwargs
    ) -> int:
        """
        Estimate gas for contract function call.
        
        Args:
            contract: Web3 contract instance
            fn_name: Function name
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Estimated gas amount
        """
        try:
            fn = getattr(contract.functions, fn_name)
            return fn(*args).estimate_gas(**kwargs)
        except Exception as e:
            logging.error(f"Error estimating gas: {e}")
            raise
    
    @staticmethod
    def _get_etherscan_api_key() -> str:
        """Get Etherscan API key from environment."""
        import os
        api_key = os.getenv('ETHERSCAN_API_KEY')
        if not api_key:
            raise ValueError("ETHERSCAN_API_KEY environment variable not set")
        return api_key