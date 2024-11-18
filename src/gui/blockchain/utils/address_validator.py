# src/gui/blockchain/utils/address_validator.py

import re
from typing import Dict, Optional
from eth_utils import is_address, to_checksum_address

class AddressValidator:
    """Validates blockchain addresses for different chain types."""
    
    # Regex patterns for different address formats
    PATTERNS = {
        'evm': r'^0x[a-fA-F0-9]{40}$',
        'solana': r'^[1-9A-HJ-NP-Za-km-z]{32,44}$',
        'cosmos': r'^cosmos[0-9a-zA-Z]{39}$',
        'polkadot': r'^[1-9A-HJ-NP-Za-km-z]{47,48}$',
        'bitcoin': r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[ac-hj-np-z02-9]{11,71}$',
        'near': r'^[a-z0-9_-]{2,64}\.near$',
        'tezos': r'^tz[1-3][1-9A-HJ-NP-Za-km-z]{33}$'
    }

    @staticmethod
    def validate_address(address: str, chain_type: str = 'evm') -> bool:
        """
        Validate a blockchain address.
        
        Args:
            address: Address to validate
            chain_type: Type of blockchain (evm, solana, etc.)
            
        Returns:
            bool: True if address is valid
        """
        if not address or not isinstance(address, str):
            return False
            
        # Handle EVM addresses with special validation
        if chain_type.lower() == 'evm':
            try:
                return is_address(address)
            except Exception:
                return False
        
        # Use regex patterns for other chains
        pattern = AddressValidator.PATTERNS.get(chain_type.lower())
        if not pattern:
            return False
            
        return bool(re.match(pattern, address))

    @staticmethod
    def normalize_address(address: str, chain_type: str = 'evm') -> Optional[str]:
        """
        Normalize an address to its standard format.
        
        Args:
            address: Address to normalize
            chain_type: Type of blockchain
            
        Returns:
            Normalized address or None if invalid
        """
        if not AddressValidator.validate_address(address, chain_type):
            return None
            
        try:
            # Handle EVM checksum addresses
            if chain_type.lower() == 'evm':
                return to_checksum_address(address)
                
            # For other chains, just return lowercase
            return address.lower()
            
        except Exception:
            return None

    @staticmethod
    def validate_batch(addresses: list, chain_type: str = 'evm') -> Dict[str, bool]:
        """
        Validate multiple addresses.
        
        Args:
            addresses: List of addresses to validate
            chain_type: Type of blockchain
            
        Returns:
            Dict mapping addresses to validation results
        """
        return {
            addr: AddressValidator.validate_address(addr, chain_type)
            for addr in addresses
        }

    @staticmethod
    def detect_chain_type(address: str) -> Optional[str]:
        """
        Attempt to detect chain type from address format.
        
        Args:
            address: Address to analyze
            
        Returns:
            Chain type string or None if unknown
        """
        if not address:
            return None
            
        # Try each pattern
        for chain_type, pattern in AddressValidator.PATTERNS.items():
            if re.match(pattern, address):
                return chain_type
                
        return None

    @staticmethod
    def get_address_info(address: str) -> Dict[str, Optional[str]]:
        """
        Get detailed information about an address.
        
        Args:
            address: Address to analyze
            
        Returns:
            Dictionary containing address information
        """
        chain_type = AddressValidator.detect_chain_type(address)
        is_valid = AddressValidator.validate_address(address, chain_type) if chain_type else False
        
        return {
            'address': address,
            'chain_type': chain_type,
            'is_valid': is_valid,
            'normalized': AddressValidator.normalize_address(address, chain_type) if is_valid else None
        }

def validate_address(address: str, chain_type: str = 'evm') -> bool:
    """
    Convenience function for simple address validation.
    
    Args:
        address: Address to validate
        chain_type: Type of blockchain
        
        Returns:
            bool: True if address is valid
    """
    return AddressValidator.validate_address(address, chain_type)

# Common chain prefixes for reference
CHAIN_PREFIXES = {
    'ethereum': '0x',
    'cosmos': 'cosmos',
    'solana': None,  # No specific prefix, base58 encoded
    'polkadot': None,  # No specific prefix, SS58 encoded
    'bitcoin': ['1', '3', 'bc1'],
    'near': '.near',
    'tezos': 'tz'
}