# src/gui/blockchain/adapters/base_adapter.py

from typing import Dict, List, Optional, Union, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class NetworkStatus:
    """Base network status information."""
    connected: bool
    chain_id: Optional[str]
    latest_block: int
    sync_percentage: float
    peer_count: int
    last_update: datetime
    network_type: str
    extra_info: Dict[str, Any]

@dataclass
class TransactionBase:
    """Base transaction information."""
    hash: str
    from_address: str
    to_address: Optional[str]
    value: Union[int, float]
    block_number: int
    timestamp: datetime
    status: bool
    raw_data: Optional[Dict] = None

@dataclass
class EventBase:
    """Base event information."""
    contract_address: str
    event_name: str
    block_number: int
    transaction_hash: str
    timestamp: datetime
    args: Dict[str, Any]
    raw_data: Optional[Dict] = None

class BaseAdapter(ABC):
    """Base class for blockchain network adapters."""
    
    def __init__(self, network_config: Dict):
        """
        Initialize network adapter.
        
        Args:
            network_config: Network configuration dictionary
        """
        self.config = network_config
        self.network_id = network_config['id']
        self.network_type = network_config['type']
        
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to network.
        
        Returns:
            bool: True if connection successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close network connection."""
        pass
    
    @abstractmethod
    async def get_status(self) -> NetworkStatus:
        """
        Get current network status.
        
        Returns:
            NetworkStatus object
        """
        pass
    
    @abstractmethod
    async def get_balance(self, address: str) -> Optional[Union[int, float]]:
        """
        Get native token balance for address.
        
        Args:
            address: Wallet/contract address
            
        Returns:
            Balance amount or None if error
        """
        pass
    
    @abstractmethod
    async def get_transaction(self, tx_hash: str) -> Optional[TransactionBase]:
        """
        Get transaction information.
        
        Args:
            tx_hash: Transaction hash/ID
            
        Returns:
            Transaction info or None if not found
        """
        pass
    
    @abstractmethod
    async def get_transactions(
        self,
        address: str,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None
    ) -> List[TransactionBase]:
        """
        Get transactions for address.
        
        Args:
            address: Wallet/contract address
            start_block: Starting block number
            end_block: Ending block number
            
        Returns:
            List of transactions
        """
        pass
    
    @abstractmethod
    async def get_contract_events(
        self,
        contract_address: str,
        event_name: str,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None
    ) -> List[EventBase]:
        """
        Get contract events.
        
        Args:
            contract_address: Contract address
            event_name: Name of event to fetch
            from_block: Starting block number
            to_block: Ending block number
            
        Returns:
            List of events
        """
        pass
    
    @abstractmethod
    async def validate_address(self, address: str) -> bool:
        """
        Validate address format.
        
        Args:
            address: Address to validate
            
        Returns:
            bool: True if address is valid
        """
        pass
    
    @abstractmethod
    async def estimate_fee(
        self,
        from_address: str,
        to_address: str,
        value: Union[int, float],
        data: Optional[str] = None
    ) -> Optional[Union[int, float]]:
        """
        Estimate transaction fee.
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            value: Transaction value
            data: Optional transaction data
            
        Returns:
            Estimated fee or None if error
        """
        pass
    
    @abstractmethod
    async def get_code(self, address: str) -> Optional[str]:
        """
        Get contract bytecode.
        
        Args:
            address: Contract address
            
        Returns:
            Contract bytecode or None if error
        """
        pass
    
    @abstractmethod
    async def call_contract(
        self,
        contract_address: str,
        function_name: str,
        args: List[Any] = None
    ) -> Optional[Any]:
        """
        Call contract read function.
        
        Args:
            contract_address: Contract address
            function_name: Function to call
            args: Function arguments
            
        Returns:
            Function result or None if error
        """
        pass
    
    @property
    @abstractmethod
    def explorer_url(self) -> Optional[str]:
        """Get block explorer URL for network."""
        pass
    
    def get_transaction_url(self, tx_hash: str) -> Optional[str]:
        """Get block explorer URL for transaction."""
        if self.explorer_url:
            return f"{self.explorer_url}/tx/{tx_hash}"
        return None
    
    def get_address_url(self, address: str) -> Optional[str]:
        """Get block explorer URL for address."""
        if self.explorer_url:
            return f"{self.explorer_url}/address/{address}"
        return None
    
    def get_block_url(self, block_number: Union[int, str]) -> Optional[str]:
        """Get block explorer URL for block."""
        if self.explorer_url:
            return f"{self.explorer_url}/block/{block_number}"
        return None
    
    async def get_contract_info(self, address: str) -> Optional[Dict]:
        """
        Get basic contract information.
        
        Args:
            address: Contract address
            
        Returns:
            Contract info dictionary or None if error
        """
        try:
            code = await self.get_code(address)
            if not code or code == '0x':
                return None
                
            return {
                'address': address,
                'has_code': True,
                'code_size': len(code) // 2 - 1,  # Convert hex to bytes
                'network': self.network_id,
                'type': self.network_type
            }
        except Exception:
            return None
    
    def format_value(self, value: Union[int, float]) -> str:
        """
        Format native token value for display.
        
        Args:
            value: Token value
            
        Returns:
            Formatted value string
        """
        # Should be overridden by specific adapters to handle decimals
        return str(value)
    
    def format_address(self, address: str) -> str:
        """
        Format address for display.
        
        Args:
            address: Blockchain address
            
        Returns:
            Formatted address string
        """
        # Basic truncation, should be overridden if needed
        if len(address) > 12:
            return f"{address[:6]}...{address[-4:]}"
        return address