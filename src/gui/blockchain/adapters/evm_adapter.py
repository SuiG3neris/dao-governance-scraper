# src/gui/blockchain/adapters/evm_adapter.py

from typing import Dict, List, Optional, Union, Any
from web3 import Web3
from web3.types import BlockData, TxData, LogReceipt
from eth_typing import Address, HexStr, BlockNumber
import json
import logging
from datetime import datetime
from dataclasses import dataclass

@dataclass
class EVMTransaction:
    """Container for EVM transaction data."""
    hash: str
    from_address: str
    to_address: Optional[str]
    value: int
    gas_price: int
    gas_used: Optional[int]
    block_number: int
    timestamp: datetime
    status: bool
    function_name: Optional[str] = None
    function_args: Optional[Dict] = None
    raw_data: Optional[Dict] = None

@dataclass
class EVMEvent:
    """Container for EVM event data."""
    contract_address: str
    event_name: str
    block_number: int
    transaction_hash: str
    log_index: int
    args: Dict[str, Any]
    timestamp: datetime
    raw_data: Optional[Dict] = None

class EVMAdapter:
    """Adapter for interacting with EVM-compatible blockchains."""
    
    def __init__(self, network_config: Dict):
        """
        Initialize EVM adapter.
        
        Args:
            network_config: Network configuration dictionary
        """
        self.config = network_config
        self.network_id = network_config['id']
        self.rpc_url = network_config['rpc_url']
        
        # Initialize Web3 connection
        self.web3 = Web3(Web3.HTTPProvider(
            self.rpc_url,
            request_kwargs=self._get_request_kwargs()
        ))
        
        # Cache for contract ABIs and function signatures
        self.contract_abis: Dict[str, List] = {}
        self.function_sigs: Dict[str, Dict] = {}
        
        # Initialize commonly used contracts
        self.erc20_abi = self._load_standard_abi('ERC20')
        self.erc721_abi = self._load_standard_abi('ERC721')
        
    def _get_request_kwargs(self) -> Dict:
        """Get request configuration for Web3."""
        kwargs = {}
        
        # Add API key if provided
        if self.config.get('api_key'):
            kwargs['headers'] = {
                'Authorization': f"Bearer {self.config['api_key']}"
            }
            
        return kwargs
        
    def _load_standard_abi(self, contract_type: str) -> List:
        """Load standard ABI definition."""
        try:
            with open(f"data/abis/{contract_type.lower()}.json") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading {contract_type} ABI: {e}")
            return []

    async def get_block(self, block_number: Union[str, int]) -> Optional[BlockData]:
        """
        Get block information.
        
        Args:
            block_number: Block number or 'latest'
            
        Returns:
            Block data or None if not found
        """
        try:
            block = await self.web3.eth.get_block(block_number, full_transactions=True)
            return block
        except Exception as e:
            logging.error(f"Error getting block {block_number}: {e}")
            return None

    async def get_transaction(self, tx_hash: str) -> Optional[EVMTransaction]:
        """
        Get transaction information.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction data or None if not found
        """
        try:
            # Get transaction data
            tx = await self.web3.eth.get_transaction(tx_hash)
            receipt = await self.web3.eth.get_transaction_receipt(tx_hash)
            block = await self.get_block(tx['blockNumber'])
            
            # Extract function call data if present
            function_name = None
            function_args = None
            if tx['input'] and len(tx['input']) >= 10:
                function_sig = tx['input'][:10]
                if function_sig in self.function_sigs:
                    function_info = self.function_sigs[function_sig]
                    function_name = function_info['name']
                    # TODO: Decode function arguments
            
            return EVMTransaction(
                hash=tx_hash,
                from_address=tx['from'],
                to_address=tx['to'],
                value=tx['value'],
                gas_price=tx['gasPrice'],
                gas_used=receipt['gasUsed'],
                block_number=tx['blockNumber'],
                timestamp=datetime.fromtimestamp(block['timestamp']),
                status=receipt['status'],
                function_name=function_name,
                function_args=function_args,
                raw_data={
                    'transaction': dict(tx),
                    'receipt': dict(receipt)
                }
            )
            
        except Exception as e:
            logging.error(f"Error getting transaction {tx_hash}: {e}")
            return None

    async def get_contract_events(
        self,
        contract_address: str,
        event_name: str,
        from_block: int,
        to_block: Union[int, str] = 'latest'
    ) -> List[EVMEvent]:
        """
        Get contract events.
        
        Args:
            contract_address: Contract address
            event_name: Name of event to fetch
            from_block: Starting block
            to_block: Ending block or 'latest'
            
        Returns:
            List of events
        """
        try:
            # Get contract ABI
            if contract_address not in self.contract_abis:
                await self._load_contract_abi(contract_address)
                
            abi = self.contract_abis.get(contract_address)
            if not abi:
                return []
                
            # Create contract instance
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=abi
            )
            
            # Get event logs
            event_filter = contract.events[event_name].create_filter(
                fromBlock=from_block,
                toBlock=to_block
            )
            logs = await event_filter.get_all_entries()
            
            events = []
            for log in logs:
                block = await self.get_block(log['blockNumber'])
                
                events.append(EVMEvent(
                    contract_address=contract_address,
                    event_name=event_name,
                    block_number=log['blockNumber'],
                    transaction_hash=log['transactionHash'].hex(),
                    log_index=log['logIndex'],
                    args=dict(log['args']),
                    timestamp=datetime.fromtimestamp(block['timestamp']),
                    raw_data=dict(log)
                ))
                
            return events
            
        except Exception as e:
            logging.error(
                f"Error getting events for {contract_address}.{event_name}: {e}"
            )
            return []

    async def _load_contract_abi(self, contract_address: str):
        """Load and cache contract ABI."""
        try:
            # Try standard contracts first
            code = await self.web3.eth.get_code(
                Web3.to_checksum_address(contract_address)
            )
            
            # Try ERC20
            if self._matches_erc20(code):
                self.contract_abis[contract_address] = self.erc20_abi
                return
                
            # Try ERC721
            if self._matches_erc721(code):
                self.contract_abis[contract_address] = self.erc721_abi
                return
                
            # Try fetching from blockchain explorer
            abi = await self._fetch_abi_from_explorer(contract_address)
            if abi:
                self.contract_abis[contract_address] = abi
                return
                
        except Exception as e:
            logging.error(f"Error loading ABI for {contract_address}: {e}")

    def _matches_erc20(self, code: HexStr) -> bool:
        """Check if contract bytecode matches ERC20."""
        # TODO: Implement ERC20 detection
        return False

    def _matches_erc721(self, code: HexStr) -> bool:
        """Check if contract bytecode matches ERC721."""
        # TODO: Implement ERC721 detection
        return False

    async def _fetch_abi_from_explorer(self, contract_address: str) -> Optional[List]:
        """Fetch ABI from blockchain explorer API."""
        # TODO: Implement explorer API calls
        return None

    async def get_token_info(self, token_address: str) -> Optional[Dict]:
        """
        Get ERC20/ERC721 token information.
        
        Args:
            token_address: Token contract address
            
        Returns:
            Token information dictionary
        """
        try:
            # Create contract instance
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=self.erc20_abi
            )
            
            # Try ERC20 first
            try:
                info = {
                    'type': 'ERC20',
                    'name': await contract.functions.name().call(),
                    'symbol': await contract.functions.symbol().call(),
                    'decimals': await contract.functions.decimals().call(),
                    'total_supply': await contract.functions.totalSupply().call()
                }
                return info
            except Exception:
                pass
                
            # Try ERC721
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=self.erc721_abi
            )
            try:
                info = {
                    'type': 'ERC721',
                    'name': await contract.functions.name().call(),
                    'symbol': await contract.functions.symbol().call(),
                    'total_supply': await contract.functions.totalSupply().call()
                }
                return info
            except Exception:
                pass
                
            return None
            
        except Exception as e:
            logging.error(f"Error getting token info for {token_address}: {e}")
            return None

    async def get_token_balance(
        self,
        token_address: str,
        wallet_address: str
    ) -> Optional[int]:
        """
        Get token balance for address.
        
        Args:
            token_address: Token contract address
            wallet_address: Wallet address
            
        Returns:
            Token balance or None if error
        """
        try:
            contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=self.erc20_abi
            )
            
            balance = await contract.functions.balanceOf(
                Web3.to_checksum_address(wallet_address)
            ).call()
            
            return balance
            
        except Exception as e:
            logging.error(
                f"Error getting balance for {wallet_address} in {token_address}: {e}"
            )
            return None