"""
Secure API credential management system for DAO analysis tool.
"""

import os
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .models import APICredential, APIType
from .validators import APIValidator, EtherscanValidator, GitLabValidator, AnthropicValidator

class APIManager:
    """Manages secure storage and access to API credentials."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize API manager.
        
        Args:
            config_dir: Directory for configuration files (optional)
        """
        # Set default config directory if none provided
        config_dir = config_dir or str(Path.home() / '.dao_scraper' / 'api')
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage
        self.credentials: Dict[str, APICredential] = {}
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        try:
            # Initialize encryption and validators
            self.cipher_suite = self._initialize_encryption()
            self.validators = self._initialize_validators()
            
            # Load existing credentials
            self.load_credentials()
            
            self.logger.info("API Manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing API Manager: {e}")
            raise

    def _initialize_encryption(self) -> Fernet:
        """Initialize encryption for secure storage."""
        key_file = self.config_dir / ".secret_key"
        salt_file = self.config_dir / ".salt"
        
        try:
            if not key_file.exists() or not salt_file.exists():
                # Generate new key and salt
                salt = os.urandom(16)
                salt_file.write_bytes(salt)
                
                # Use PBKDF2 to derive key
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000
                )
                key = base64.urlsafe_b64encode(kdf.derive(os.urandom(32)))
                key_file.write_bytes(key)
                
                self.logger.info("New encryption key generated")
            else:
                # Load existing key and salt
                salt = salt_file.read_bytes()
                key = key_file.read_bytes()
                
                self.logger.info("Loaded existing encryption key")
                
            return Fernet(key)
            
        except Exception as e:
            self.logger.error(f"Error initializing encryption: {e}")
            raise

    def _initialize_validators(self) -> Dict[APIType, APIValidator]:
        """Initialize API validators."""
        return {
            APIType.ETHERSCAN: EtherscanValidator(),
            APIType.GITLAB: GitLabValidator(),
            APIType.ANTHROPIC: AnthropicValidator()
        }

    def add_credential(self, credential: APICredential) -> None:
        """Add new API credential."""
        try:
            # Validate if validator exists
            if credential.api_type in self.validators:
                credential.is_valid = self.validators[credential.api_type].validate(credential)
            
            # Encrypt key
            encrypted_key = self.cipher_suite.encrypt(credential.key.encode())
            credential.key = encrypted_key.decode()
            
            # Save credential
            self.credentials[credential.name] = credential
            self.save_credentials()
            
            self.logger.info(f"Added credential: {credential.name}")
            
        except Exception as e:
            self.logger.error(f"Error adding credential {credential.name}: {e}")
            raise

    def get_credential(self, name: str) -> Optional[APICredential]:
        """Get decrypted credential."""
        try:
            if name in self.credentials:
                credential = self.credentials[name]
                
                # Decrypt the key
                encrypted_key = credential.key.encode()
                decrypted_key = self.cipher_suite.decrypt(encrypted_key).decode()
                
                # Return new instance with decrypted key
                credential_dict = credential.to_dict()
                credential_dict['key'] = decrypted_key
                return APICredential.from_dict(credential_dict)
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving credential {name}: {e}")
            raise

    def remove_credential(self, name: str) -> bool:
        """Remove credential."""
        try:
            if name in self.credentials:
                del self.credentials[name]
                self.save_credentials()
                self.logger.info(f"Removed credential: {name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing credential {name}: {e}")
            raise

    def validate_credential(self, name: str) -> bool:
        """Test if API credential is valid."""
        try:
            credential = self.get_credential(name)
            if not credential:
                return False
                
            if credential.api_type in self.validators:
                is_valid = self.validators[credential.api_type].validate(credential)
                
                # Update validation status
                self.credentials[name].is_valid = is_valid
                self.credentials[name].last_used = datetime.now()
                self.save_credentials()
                
                return is_valid
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error validating credential {name}: {e}")
            return False

    def save_credentials(self) -> None:
        """Save credentials to encrypted file."""
        try:
            credentials_file = self.config_dir / "credentials.enc"
            
            # Convert to dictionary format
            data = {
                name: cred.to_dict()
                for name, cred in self.credentials.items()
            }
            
            # Encrypt and save
            encrypted_data = self.cipher_suite.encrypt(json.dumps(data).encode())
            credentials_file.write_bytes(encrypted_data)
            
            self.logger.info("Credentials saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving credentials: {e}")
            raise

    def load_credentials(self) -> None:
        """Load credentials from encrypted file."""
        try:
            credentials_file = self.config_dir / "credentials.enc"
            
            if credentials_file.exists():
                # Decrypt and load
                encrypted_data = credentials_file.read_bytes()
                data = json.loads(self.cipher_suite.decrypt(encrypted_data).decode())
                
                # Convert to APICredential objects
                self.credentials = {
                    name: APICredential.from_dict(cred_data)
                    for name, cred_data in data.items()
                }
                
                self.logger.info(f"Loaded {len(self.credentials)} credentials")
            else:
                self.logger.info("No existing credentials found")
            
        except Exception as e:
            self.logger.error(f"Error loading credentials: {e}")
            raise

    def list_credentials(self) -> List[Dict]:
        """Get list of credential summaries."""
        return [{
            'name': cred.name,
            'api_type': cred.api_type.name,
            'endpoint': cred.endpoint,
            'rate_limit': cred.rate_limit,
            'is_valid': cred.is_valid,
            'created_at': cred.created_at.isoformat(),
            'last_used': cred.last_used.isoformat()
        } for cred in self.credentials.values()]

    def update_credential(self, name: str, **kwargs) -> bool:
        """Update credential fields."""
        try:
            if name not in self.credentials:
                return False
                
            credential = self.credentials[name]
            
            for field, value in kwargs.items():
                if hasattr(credential, field):
                    setattr(credential, field, value)
                    
            self.save_credentials()
            self.logger.info(f"Updated credential: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating credential {name}: {e}")
            raise