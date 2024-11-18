# src/gui/blockchain/utils/contract_templates.py

from typing import Dict, List, Optional
import json
from pathlib import Path

class ContractTemplates:
    """Provides standard contract templates and configurations."""
    
    def __init__(self):
        self.template_dir = Path("data/contract_templates")
        self.templates = self._load_templates()
        
    def get_template(self, name: str) -> Optional[Dict]:
        """Get a specific contract template."""
        return self.templates.get(name)
    
    def get_all_templates(self) -> Dict[str, Dict]:
        """Get all available templates."""
        return self.templates
    
    def get_template_names(self) -> List[str]:
        """Get list of available template names."""
        return list(self.templates.keys())
    
    def _load_templates(self) -> Dict[str, Dict]:
        """Load contract templates from files."""
        templates = {}
        
        # ERC20 Template
        templates['ERC20'] = {
            'name': 'ERC20 Token',
            'type': 'token',
            'standard': 'ERC20',
            'events': [
                'Transfer(address,address,uint256)',
                'Approval(address,address,uint256)'
            ],
            'functions': [
                'transfer(address,uint256)',
                'transferFrom(address,address,uint256)',
                'approve(address,uint256)',
                'allowance(address,address)',
                'balanceOf(address)',
                'totalSupply()'
            ],
            'common_patterns': {
                'initialization': ['name()', 'symbol()', 'decimals()'],
                'permissions': ['owner()', 'transferOwnership(address)'],
                'minting': ['mint(address,uint256)', 'burn(uint256)']
            }
        }
        
        # ERC721 Template
        templates['ERC721'] = {
            'name': 'ERC721 NFT',
            'type': 'nft',
            'standard': 'ERC721',
            'events': [
                'Transfer(address,address,uint256)',
                'Approval(address,address,uint256)',
                'ApprovalForAll(address,address,bool)'
            ],
            'functions': [
                'balanceOf(address)',
                'ownerOf(uint256)',
                'safeTransferFrom(address,address,uint256)',
                'transferFrom(address,address,uint256)',
                'approve(address,uint256)',
                'setApprovalForAll(address,bool)',
                'getApproved(uint256)',
                'isApprovedForAll(address,address)'
            ],
            'common_patterns': {
                'metadata': ['tokenURI(uint256)'],
                'minting': ['mint(address,uint256)', 'safeMint(address,uint256)'],
                'enumeration': ['totalSupply()', 'tokenByIndex(uint256)']
            }
        }
        
        # Governance Template
        templates['Governance'] = {
            'name': 'Governance Contract',
            'type': 'governance',
            'events': [
                'ProposalCreated(uint256,address,string)',
                'VoteCast(address,uint256,bool,uint256)',
                'ProposalExecuted(uint256)'
            ],
            'functions': [
                'propose(string,bytes[])',
                'castVote(uint256,bool)',
                'execute(uint256)',
                'getProposal(uint256)',
                'getVotes(address)',
                'state(uint256)'
            ],
            'common_patterns': {
                'voting': ['quorum()', 'votingDelay()', 'votingPeriod()'],
                'delegation': ['delegate(address)', 'delegates(address)'],
                'execution': ['queue(uint256)', 'cancel(uint256)']
            }
        }
        
        # Staking Template
        templates['Staking'] = {
            'name': 'Staking Contract',
            'type': 'staking',
            'events': [
                'Staked(address,uint256)',
                'Withdrawn(address,uint256)',
                'RewardPaid(address,uint256)'
            ],
            'functions': [
                'stake(uint256)',
                'withdraw(uint256)',
                'getReward()',
                'totalSupply()',
                'balanceOf(address)',
                'earned(address)'
            ],
            'common_patterns': {
                'rewards': ['rewardPerToken()', 'rewardRate()'],
                'timelock': ['lockedUntil(address)', 'lockDuration()'],
                'emergency': ['pause()', 'unpause()']
            }
        }
        
        # Try loading additional templates from files
        try:
            for file in self.template_dir.glob("*.json"):
                with open(file, 'r') as f:
                    template = json.load(f)
                    if 'name' in template and 'type' in template:
                        templates[file.stem] = template
        except Exception:
            pass
            
        return templates
    
    def get_standard_events(self, template_name: str) -> List[str]:
        """Get standard events for a template."""
        template = self.templates.get(template_name)
        return template.get('events', []) if template else []
    
    def get_standard_functions(self, template_name: str) -> List[str]:
        """Get standard functions for a template."""
        template = self.templates.get(template_name)
        return template.get('functions', []) if template else []
    
    def get_common_patterns(self, template_name: str) -> Dict[str, List[str]]:
        """Get common patterns for a template."""
        template = self.templates.get(template_name)
        return template.get('common_patterns', {}) if template else {}
    