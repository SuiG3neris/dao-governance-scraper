"""
API credential validators.
"""

from abc import ABC, abstractmethod
import requests
import logging

from .models import APICredential

class APIValidator(ABC):
    """Base class for API validators."""
    
    @abstractmethod
    def validate(self, credential: APICredential) -> bool:
        """Validate API credential."""
        pass

class EtherscanValidator(APIValidator):
    """Validator for Etherscan API credentials."""
    
    def validate(self, credential: APICredential) -> bool:
        """Validate Etherscan API key."""
        try:
            endpoint = credential.endpoint or "https://api.etherscan.io/api"
            response = requests.get(
                endpoint,
                params={
                    "module": "account",
                    "action": "balance",
                    "address": "0x0000000000000000000000000000000000000000",
                    "apikey": credential.key
                }
            )
            return response.status_code == 200 and response.json().get('status') == '1'
        except Exception as e:
            logging.error(f"Etherscan validation error: {e}")
            return False

class GitLabValidator(APIValidator):
    """Validator for GitLab API credentials."""
    
    def validate(self, credential: APICredential) -> bool:
        """Validate GitLab API token."""
        try:
            endpoint = credential.endpoint or "https://gitlab.com/api/v4"
            response = requests.get(
                f"{endpoint}/user",
                headers={"PRIVATE-TOKEN": credential.key}
            )
            return response.status_code == 200
        except Exception as e:
            logging.error(f"GitLab validation error: {e}")
            return False

class AnthropicValidator(APIValidator):
    """Validator for Anthropic/Claude API credentials."""
    
    def validate(self, credential: APICredential) -> bool:
        """Validate Anthropic API key."""
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": credential.key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-opus-20240229",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}]
                }
            )
            return response.status_code in (200, 401)  # 401 means key format is valid but unauthorized
        except Exception as e:
            logging.error(f"Anthropic validation error: {e}")
            return False