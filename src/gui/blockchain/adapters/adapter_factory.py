# src/gui/blockchain/adapters/adapter_factory.py

from typing import Dict, Optional
from .evm_adapter import EVMAdapter
from .base_adapter import BaseAdapter

class NetworkAdapterFactory:
    """Factory for creating blockchain network adapters."""
    
    # Map of network types to adapter classes
    ADAPTERS = {
        'evm': EVMAdapter,
        # Add other adapters as they're implemented:
        # 'solana': SolanaAdapter,
        # 'cosmos': CosmosAdapter,
        # 'polkadot': PolkadotAdapter,
    }
    
    @classmethod
    def create_adapter(cls, network_config: Dict) -> Optional[BaseAdapter]:
        """
        Create appropriate network adapter based on configuration.
        
        Args:
            network_config: Network configuration dictionary
            
        Returns:
            Network adapter instance or None if unsupported
        """
        network_type = network_config.get('type', '').lower()
        
        # Get adapter class
        adapter_class = cls.ADAPTERS.get(network_type)
        if not adapter_class:
            return None
            
        # Create and return adapter instance
        try:
            return adapter_class(network_config)
        except Exception as e:
            logging.error(f"Error creating adapter: {e}")
            return None
    
    @classmethod
    def get_supported_networks(cls) -> List[str]:
        """Get list of supported network types."""
        return list(cls.ADAPTERS.keys())
    
    @classmethod
    def is_network_supported(cls, network_type: str) -> bool:
        """Check if network type is supported."""
        return network_type.lower() in cls.ADAPTERS