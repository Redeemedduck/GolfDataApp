"""
Credential Manager for Uneekor Portal Authentication.

Supports two authentication modes:
1. Cookie Persistence (recommended for development)
   - User logs in interactively once
   - Browser cookies saved to encrypted file
   - Subsequent runs restore session automatically

2. Environment Variables (recommended for Cloud Run)
   - UNEEKOR_USERNAME and UNEEKOR_PASSWORD
   - Full login flow each time

Security:
- Cookies encrypted with Fernet symmetric encryption
- Encryption key from environment or generated locally
- Cookie file excluded from git via .gitignore
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


@dataclass
class StoredCredentials:
    """Container for stored credential data."""
    cookies: list
    storage_state: dict
    created_at: str
    expires_at: str
    username: Optional[str] = None


class CredentialManager:
    """
    Manages Uneekor portal credentials with cookie persistence.

    Usage:
        # Initialize
        cm = CredentialManager()

        # Check if we have valid stored credentials
        if cm.has_valid_credentials():
            storage_state = cm.load_storage_state()
            # Use storage_state with Playwright
        else:
            # Need fresh login
            # After successful login, save:
            cm.save_storage_state(page.context.storage_state())

        # Get credentials for login form
        username, password = cm.get_login_credentials()
    """

    DEFAULT_COOKIE_FILE = '.uneekor_cookies.enc'
    DEFAULT_KEY_FILE = '.uneekor_key'
    COOKIE_VALIDITY_DAYS = 7

    def __init__(
        self,
        cookie_file: Optional[str] = None,
        key_file: Optional[str] = None,
        base_dir: Optional[str] = None
    ):
        """
        Initialize credential manager.

        Args:
            cookie_file: Path to encrypted cookie file (default: .uneekor_cookies.enc)
            key_file: Path to encryption key file (default: .uneekor_key)
            base_dir: Base directory for credential files (default: project root)
        """
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.cookie_file = self.base_dir / (cookie_file or self.DEFAULT_COOKIE_FILE)
        self.key_file = self.base_dir / (key_file or self.DEFAULT_KEY_FILE)

        # Check if running in Cloud Run (ephemeral storage)
        self.is_cloud_run = os.getenv('K_SERVICE') is not None

        # Initialize encryption
        self._fernet: Optional[Fernet] = None
        if HAS_CRYPTOGRAPHY:
            self._init_encryption()

    def _init_encryption(self) -> None:
        """Initialize Fernet encryption with key from env or file.

        Security Note: The encryption key is stored locally in plain text.
        For production use, consider using a secrets manager or key vault.
        The key file is protected with 0o600 permissions (owner read/write only).
        """
        # Try environment variable first (preferred for production)
        key = os.getenv('UNEEKOR_COOKIE_KEY')

        if not key:
            # Try key file
            if self.key_file.exists():
                key = self.key_file.read_text().strip()
            else:
                # Generate new key and save locally
                # Warning: Key stored in plain text - suitable for development only
                key = Fernet.generate_key().decode()
                if not self.is_cloud_run:
                    # Save for future use (not on Cloud Run)
                    self.key_file.write_text(key)
                    self.key_file.chmod(0o600)  # Restrict permissions
                    print(f"Note: Encryption key saved to {self.key_file}")
                    print("For production, set UNEEKOR_COOKIE_KEY environment variable instead.")

        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def get_login_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get login credentials from environment variables.

        Returns:
            Tuple of (username, password) or (None, None) if not configured
        """
        username = os.getenv('UNEEKOR_USERNAME')
        password = os.getenv('UNEEKOR_PASSWORD')
        return username, password

    def has_login_credentials(self) -> bool:
        """Check if login credentials are available in environment."""
        username, password = self.get_login_credentials()
        return bool(username and password)

    def has_valid_credentials(self) -> bool:
        """
        Check if we have valid stored credentials (cookies).

        Returns:
            True if valid cookies exist and haven't expired
        """
        if self.is_cloud_run:
            # Cloud Run has ephemeral storage, cookies won't persist
            return False

        if not self.cookie_file.exists():
            return False

        try:
            creds = self._load_credentials()
            if not creds:
                return False

            # Check expiration
            expires_at = datetime.fromisoformat(creds.expires_at)
            if datetime.utcnow() > expires_at:
                print(f"Stored credentials expired at {expires_at}")
                return False

            return True

        except Exception as e:
            print(f"Error checking credentials: {e}")
            return False

    def _load_credentials(self) -> Optional[StoredCredentials]:
        """Load and decrypt stored credentials."""
        if not HAS_CRYPTOGRAPHY:
            print("cryptography package not installed, cannot decrypt cookies")
            return None

        if not self._fernet:
            return None

        try:
            encrypted_data = self.cookie_file.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode())
            return StoredCredentials(**data)
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None

    def load_storage_state(self) -> Optional[Dict[str, Any]]:
        """
        Load Playwright storage state from encrypted file.

        Returns:
            Storage state dict for Playwright context, or None if not available
        """
        creds = self._load_credentials()
        if creds:
            return creds.storage_state
        return None

    def save_storage_state(
        self,
        storage_state: Dict[str, Any],
        username: Optional[str] = None
    ) -> bool:
        """
        Save Playwright storage state to encrypted file.

        Args:
            storage_state: Playwright storage state from context.storage_state()
            username: Optional username to store for reference

        Returns:
            True if saved successfully
        """
        if self.is_cloud_run:
            print("Running on Cloud Run - cookie persistence not available")
            return False

        if not HAS_CRYPTOGRAPHY:
            print("cryptography package not installed, cannot encrypt cookies")
            return False

        if not self._fernet:
            return False

        try:
            now = datetime.utcnow()
            creds = StoredCredentials(
                cookies=storage_state.get('cookies', []),
                storage_state=storage_state,
                created_at=now.isoformat(),
                expires_at=(now + timedelta(days=self.COOKIE_VALIDITY_DAYS)).isoformat(),
                username=username
            )

            data = json.dumps(asdict(creds)).encode()
            encrypted_data = self._fernet.encrypt(data)

            self.cookie_file.write_bytes(encrypted_data)
            self.cookie_file.chmod(0o600)  # Restrict permissions

            print(f"Saved credentials, valid until {creds.expires_at}")
            return True

        except Exception as e:
            print(f"Error saving credentials: {e}")
            return False

    def clear_credentials(self) -> bool:
        """
        Clear stored credentials.

        Returns:
            True if credentials were cleared
        """
        try:
            if self.cookie_file.exists():
                self.cookie_file.unlink()
                print("Cleared stored credentials")
                return True
            return False
        except Exception as e:
            print(f"Error clearing credentials: {e}")
            return False

    def get_credential_info(self) -> Dict[str, Any]:
        """
        Get information about stored credentials without exposing sensitive data.

        Returns:
            Dict with credential status information
        """
        info = {
            'has_env_credentials': self.has_login_credentials(),
            'has_stored_cookies': False,
            'cookies_valid': False,
            'cookies_expires_at': None,
            'stored_username': None,
            'is_cloud_run': self.is_cloud_run,
        }

        if self.cookie_file.exists():
            info['has_stored_cookies'] = True
            creds = self._load_credentials()
            if creds:
                info['cookies_expires_at'] = creds.expires_at
                info['stored_username'] = creds.username
                info['cookies_valid'] = self.has_valid_credentials()

        return info

    def get_auth_method(self) -> str:
        """
        Determine the best authentication method available.

        Returns:
            'cookies' if valid cookies available
            'credentials' if env credentials available
            'interactive' if manual login required
        """
        if self.has_valid_credentials():
            return 'cookies'
        if self.has_login_credentials():
            return 'credentials'
        return 'interactive'


def ensure_gitignore_entries(force: bool = False) -> bool:
    """Ensure credential files are in .gitignore.

    Args:
        force: If True, add entries even if file doesn't exist (creates new .gitignore)

    Returns:
        True if entries were added, False if already present or skipped
    """
    gitignore_path = Path(__file__).parent.parent / '.gitignore'
    entries_to_add = [
        '.uneekor_cookies.enc',
        '.uneekor_key',
    ]

    existing_content = ''
    if gitignore_path.exists():
        existing_content = gitignore_path.read_text()
    elif not force:
        # Don't create .gitignore on import - let user do it explicitly
        return False

    entries_needed = [e for e in entries_to_add if e not in existing_content]

    if entries_needed:
        with open(gitignore_path, 'a') as f:
            f.write('\n# Uneekor automation credentials\n')
            for entry in entries_needed:
                f.write(f'{entry}\n')
        print(f"Added {len(entries_needed)} entries to .gitignore")
        return True
    return False


def setup_credentials_gitignore() -> None:
    """Explicitly set up .gitignore entries. Call from CLI, not import."""
    ensure_gitignore_entries(force=True)


# Note: Removed auto-run on import to avoid unexpected file mutations
# Call setup_credentials_gitignore() explicitly from CLI if needed
