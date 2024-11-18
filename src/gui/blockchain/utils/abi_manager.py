# src/gui/blockchain/utils/abi_manager.py

from typing import Dict, List, Optional
import json
import requests
import logging
from pathlib import Path
import hashlib

class ABIManager:
    """Manages contract ABI fetching, caching, and analysis."""
    
    def __init__(self):
        self.cache_dir = Path("cache/abis")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_keys: Dict[str, str] = {}
        
        # Load standard ABIs
        self.standard_abis = self._load_standard_abis()
        
    def fetch_abi(self, address: str, network: str) -> List[Dict]:
        """
        Fetch ABI for a contract address.
        
        Args:
            address: Contract address
            network: Network name
            
        Returns:
            List of ABI entries
            
        Raises:
            Exception: If ABI cannot be fetched
        """
        # Check cache first
        cached = self._get_cached_abi(address)
        if cached:
            return cached
            
        try:
            # Try etherscan-like APIs first
            if self._is_etherscan_compatible(network):
                abi = self._fetch_from_etherscan(address, network)
                if abi:
                    self._cache_abi(address, abi)
                    return abi
            
            # Try blockchain RPC
            abi = self._fetch_from_rpc(address, network)
            if abi:
                self._cache_abi(address, abi)
                return abi
                
            raise Exception("Unable to fetch ABI from any source")
            
        except Exception as e:
            logging.error(f"Error fetching ABI for {address}: {e}")
            raise
    
    def detect_contract_type(self, abi: List[Dict]) -> Optional[str]:
        """
        Detect standard contract type from ABI.
        
        Args:
            abi: Contract ABI
            
        Returns:
            Contract type string or None if unknown
        """
        # Check for standard interfaces
        if self._matches_erc20(abi):
            return "ERC20"
        elif self._matches_erc721(abi):
            return "ERC721"
        elif self._matches_erc1155(abi):
            return "ERC1155"
            
        # Check for other common patterns
        functions = set(item['name'] for item in abi if item.get('type') == 'function')
        
        if {'pause', 'unpause'}.issubset(functions):
            return "Pausable Contract"
        elif {'owner', 'transferOwnership'}.issubset(functions):
            return "Ownable Contract"
        elif {'proposal', 'vote'}.issubset(functions):
            return "Governance Contract"
            
        return None
    
    def _load_standard_abis(self) -> Dict[str, List[Dict]]:
        """Load standard ABI definitions."""
        standard_dir = Path("data/standard_abis")
        abis = {}
        
        try:
            for file in standard_dir.glob("*.json"):
                with open(file, 'r') as f:
                    abis[file.stem] = json.load(f)
            return abis
        except Exception as e:
            logging.error(f"Error loading standard ABIs: {e}")
            return {}
    
    def _get_cached_abi(self, address: str) -> Optional[List[Dict]]:
        """Get ABI from cache if available."""
        cache_file = self.cache_dir / f"{address.lower()}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    def _cache_abi(self, address: str, abi: List[Dict]):
        """Cache ABI for future use."""
        cache_file = self.cache_dir / f"{address.lower()}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(abi, f, indent=2)
        except Exception as e:
            logging.error(f"Error caching ABI: {e}")
    
    def _is_etherscan_compatible(self, network: str) -> bool:
        """Check if network has etherscan-compatible API."""
        return network.lower() in {
            'ethereum', 'ropsten', 'rinkeby', 'goerli',
            'bsc', 'polygon', 'optimism', 'arbitrum'
        }
    
    def _fetch_from_etherscan(self, address: str, network: str) -> Optional[List[Dict]]:
        """Fetch ABI from Etherscan-like API."""
        # Network-specific API configuration
        api_configs = {
            'ethereum': 'https://api.etherscan.io/api',
            'bsc': 'https://api.bscscan.com/api',
            'polygon': 'https://api.polygonscan.com/api',
            'optimism': 'https://api-optimistic.etherscan.io/api',
            'arbitrum': 'https://api.arbiscan.io/api'
        }
        
        api_url = api_configs.get(network.lower())
        if not api_url:
            return None
            
        try:
            params = {
                'module': 'contract',
                'action': 'getabi',
                'address': address,
                'apikey': self.api_keys.get(network, '')
            }
            
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == '1' and data['message'] == 'OK':
                return json.loads(data['result'])
                
        except Exception as e:
            logging.error(f"Error fetching from {network} explorer: {e}")
            
        return None
    
    def _fetch_from_rpc(self, address: str, network: str) -> Optional[List[Dict]]:
        """Fetch ABI using RPC calls (for verified contracts)."""
        # TODO: Implement RPC-based ABI fetching
        return None
    
    def _matches_erc20(self, abi: List[Dict]) -> bool:
        """Check if ABI matches ERC20 interface."""
        required = {
            'transfer', 'transferFrom', 'approve',
            'totalSupply', 'balanceOf', 'allowance'
        }
        functions = {item['name'] for item in abi if item.get('type') == 'function'}
        return required.issubset(functions)
    
    def _matches_erc721(self, abi: List[Dict]) -> bool:
        """Check if ABI matches ERC721 interface."""
        required = {
            'balanceOf', 'ownerOf', 'safeTransferFrom',
            'transferFrom', 'approve', 'setApprovalForAll'
        }
        functions = {item['name'] for item in abi if item.get('type') == 'function'}
        return required.issubset(functions)
    
    def _matches_erc1155(self, abi: List[Dict]) -> bool:
        """Check if ABI matches ERC1155 interface."""
        required = {
            'balanceOf', 'balanceOfBatch', 'setApprovalForAll',
            'safeTransferFrom', 'safeBatchTransferFrom'
        }
        functions = {item['name'] for item in abi if item.get('type') == 'function'}
        return required.issubset(functions)