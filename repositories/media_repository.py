"""
Media Repository

Handles media storage operations (images and videos).
Supports Supabase Storage for now, with easy migration path to Google Cloud Storage.
"""

import os
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

from .base_repository import SyncBaseRepository

load_dotenv()


class MediaRepository(SyncBaseRepository):
    """
    Repository for media storage operations.

    Handles upload, download, and management of golf shot media
    (impact images, swing images, video frames) to cloud storage.
    """

    def __init__(self):
        """Initialize media repository with cloud storage connection."""
        super().__init__()

        # Supabase Storage setup
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if supabase_url and supabase_key:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            self.storage_enabled = True
            self.logger.info("Supabase Storage connected")
        else:
            self.supabase = None
            self.storage_enabled = False
            self.logger.warning("Supabase credentials not found. Storage disabled.")

        # Default bucket name
        self.bucket_name = "shot-images"

    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Not applicable for media storage."""
        raise NotImplementedError("Use check_exists() instead")

    def find_all(self, filters: Optional[Dict[str, Any]] = None):
        """Not applicable for media storage."""
        raise NotImplementedError("Use list_files() instead")

    def save(self, entity: Dict[str, Any]) -> str:
        """Not applicable for media storage."""
        raise NotImplementedError("Use upload() instead")

    def update(self, id: str, updates: Dict[str, Any]) -> bool:
        """Not applicable for media storage."""
        raise NotImplementedError("Media files are immutable")

    def delete(self, id: str) -> bool:
        """Delete media file by path."""
        return self.delete_file(id)

    def upload(self, file_path: str, destination_path: str, bucket: str = None) -> str:
        """
        Upload file to cloud storage.

        Args:
            file_path: Local file path
            destination_path: Remote path in bucket
            bucket: Optional bucket name (defaults to shot-images)

        Returns:
            Public URL of uploaded file

        Raises:
            FileNotFoundError: If local file doesn't exist
            Exception: If upload fails
        """
        if not self.storage_enabled:
            raise Exception("Storage not enabled")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        bucket = bucket or self.bucket_name

        try:
            # Read file
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # Upload to Supabase Storage
            response = self.supabase.storage.from_(bucket).upload(
                destination_path,
                file_data,
                file_options={"upsert": "true"}  # Replace if exists
            )

            # Get public URL
            public_url = self.supabase.storage.from_(bucket).get_public_url(destination_path)

            self._log_operation(
                "Uploaded file",
                local_path=file_path,
                remote_path=destination_path,
                size_bytes=len(file_data)
            )

            return public_url

        except Exception as e:
            self._log_error("Failed to upload file", e, file_path=file_path)
            raise

    def download(self, remote_path: str, local_path: str, bucket: str = None) -> str:
        """
        Download file from cloud storage.

        Args:
            remote_path: Remote path in bucket
            local_path: Local destination path
            bucket: Optional bucket name

        Returns:
            Local file path

        Raises:
            Exception: If download fails
        """
        if not self.storage_enabled:
            raise Exception("Storage not enabled")

        bucket = bucket or self.bucket_name

        try:
            # Download from Supabase Storage
            response = self.supabase.storage.from_(bucket).download(remote_path)

            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Write to local file
            with open(local_path, 'wb') as f:
                f.write(response)

            self._log_operation(
                "Downloaded file",
                remote_path=remote_path,
                local_path=local_path,
                size_bytes=len(response)
            )

            return local_path

        except Exception as e:
            self._log_error("Failed to download file", e, remote_path=remote_path)
            raise

    def check_exists(self, remote_path: str, bucket: str = None) -> bool:
        """
        Check if file exists in cloud storage.

        Args:
            remote_path: Remote path in bucket
            bucket: Optional bucket name

        Returns:
            True if file exists
        """
        if not self.storage_enabled:
            return False

        bucket = bucket or self.bucket_name

        try:
            # List files in directory
            dir_path = str(Path(remote_path).parent)
            file_name = Path(remote_path).name

            files = self.supabase.storage.from_(bucket).list(dir_path)

            # Check if file exists in list
            return any(f['name'] == file_name for f in files)

        except Exception as e:
            self._log_error("Failed to check file existence", e, remote_path=remote_path)
            return False

    def get_public_url(self, remote_path: str, bucket: str = None) -> str:
        """
        Get public URL for a file.

        Args:
            remote_path: Remote path in bucket
            bucket: Optional bucket name

        Returns:
            Public URL
        """
        if not self.storage_enabled:
            raise Exception("Storage not enabled")

        bucket = bucket or self.bucket_name

        try:
            url = self.supabase.storage.from_(bucket).get_public_url(remote_path)
            return url

        except Exception as e:
            self._log_error("Failed to get public URL", e, remote_path=remote_path)
            raise

    def delete_file(self, remote_path: str, bucket: str = None) -> bool:
        """
        Delete file from cloud storage.

        Args:
            remote_path: Remote path in bucket
            bucket: Optional bucket name

        Returns:
            True if deletion successful
        """
        if not self.storage_enabled:
            return False

        bucket = bucket or self.bucket_name

        try:
            self.supabase.storage.from_(bucket).remove([remote_path])

            self._log_operation("Deleted file", remote_path=remote_path)
            return True

        except Exception as e:
            self._log_error("Failed to delete file", e, remote_path=remote_path)
            return False

    def list_files(self, directory: str = "", bucket: str = None) -> list:
        """
        List files in a directory.

        Args:
            directory: Directory path (empty for root)
            bucket: Optional bucket name

        Returns:
            List of file metadata dictionaries
        """
        if not self.storage_enabled:
            return []

        bucket = bucket or self.bucket_name

        try:
            files = self.supabase.storage.from_(bucket).list(directory)
            return files

        except Exception as e:
            self._log_error("Failed to list files", e, directory=directory)
            return []

    def calculate_checksum(self, file_path: str) -> str:
        """
        Calculate SHA256 checksum for a file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file checksum
        """
        sha256 = hashlib.sha256()

        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)

            checksum = sha256.hexdigest()
            self._log_operation("Calculated checksum", file_path=file_path, checksum=checksum[:8])

            return checksum

        except Exception as e:
            self._log_error("Failed to calculate checksum", e, file_path=file_path)
            raise

    def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes
        """
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            self._log_error("Failed to get file size", e, file_path=file_path)
            return 0
