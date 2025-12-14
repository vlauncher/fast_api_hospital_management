import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.core.config import settings
import hashlib


class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self):
        self._key = None
        self._cipher = None
        self._initialize_cipher()
    
    def _initialize_cipher(self):
        """Initialize the encryption cipher"""
        # Convert the encryption key to bytes
        key_bytes = settings.ENCRYPTION_KEY.encode()
        
        # Generate a proper Fernet key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'hospital_management_salt',  # In production, use a proper salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        self._cipher = Fernet(key)
        self._key = key
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt a string value"""
        if not data:
            return data
        
        # Convert to bytes if string
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = str(data).encode('utf-8')
        
        # Encrypt the data
        encrypted_data = self._cipher.encrypt(data_bytes)
        
        # Return as base64 string for storage
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt a string value"""
        if not encrypted_data:
            return encrypted_data
        
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Decrypt the data
            decrypted_data = self._cipher.decrypt(encrypted_bytes)
            
            # Return as string
            return decrypted_data.decode('utf-8')
        except Exception:
            # If decryption fails, return the original data
            # This handles cases where data might not be encrypted
            return encrypted_data
    
    def encrypt_dict(self, data: dict) -> dict:
        """Encrypt specific fields in a dictionary"""
        if not data:
            return data
        
        encrypted_data = {}
        for key, value in data.items():
            if self._should_encrypt_field(key):
                if isinstance(value, (dict, list)):
                    # For complex objects, serialize first
                    json_str = json.dumps(value)
                    encrypted_data[key] = self.encrypt_data(json_str)
                else:
                    encrypted_data[key] = self.encrypt_data(str(value))
            else:
                encrypted_data[key] = value
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict) -> dict:
        """Decrypt specific fields in a dictionary"""
        if not data:
            return data
        
        decrypted_data = {}
        for key, value in data.items():
            if self._should_encrypt_field(key):
                decrypted_value = self.decrypt_data(str(value))
                try:
                    # Try to parse as JSON for complex objects
                    decrypted_data[key] = json.loads(decrypted_value)
                except (json.JSONDecodeError, ValueError):
                    decrypted_data[key] = decrypted_value
            else:
                decrypted_data[key] = value
        
        return decrypted_data
    
    def _should_encrypt_field(self, field_name: str) -> bool:
        """Determine if a field should be encrypted based on its name"""
        sensitive_fields = {
            'first_name', 'last_name', 'middle_name', 'date_of_birth',
            'phone_primary', 'phone_secondary', 'email', 'address',
            'national_id', 'ssn', 'passport_number', 'medical_record_number'
        }
        
        return field_name.lower() in sensitive_fields
    
    def generate_hash(self, data: str) -> str:
        """Generate SHA-256 hash for data"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def verify_hash(self, data: str, hash_value: str) -> bool:
        """Verify data against its hash"""
        return self.generate_hash(data) == hash_value


# Global encryption manager instance
encryption_manager = EncryptionManager()


# Convenience functions
def encrypt_data(data: str) -> str:
    """Encrypt data using the global encryption manager"""
    return encryption_manager.encrypt_data(data)


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt data using the global encryption manager"""
    return encryption_manager.decrypt_data(encrypted_data)


def encrypt_sensitive_fields(data: dict) -> dict:
    """Encrypt sensitive fields in a dictionary"""
    return encryption_manager.encrypt_dict(data)


def decrypt_sensitive_fields(data: dict) -> dict:
    """Decrypt sensitive fields in a dictionary"""
    return encryption_manager.decrypt_dict(data)


def generate_data_hash(data: str) -> str:
    """Generate hash for data"""
    return encryption_manager.generate_hash(data)


def verify_data_hash(data: str, hash_value: str) -> bool:
    """Verify data against hash"""
    return encryption_manager.verify_hash(data, hash_value)
