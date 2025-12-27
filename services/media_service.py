"""
Media Service

Intelligent media handling with caching, deduplication, and optimization.
Handles images (impact, swing) and video frames for golf shots.
"""

import os
import json
import requests
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from .base_service import BaseService
from repositories.media_repository import MediaRepository


class MediaCache:
    """
    Local media cache with index for fast lookups.

    Stores media files locally with metadata to avoid re-downloading
    from the Uneekor API and re-uploading to cloud storage.
    """

    def __init__(self, cache_dir: str = "./media_cache"):
        """
        Initialize media cache.

        Args:
            cache_dir: Directory for cached files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache index file
        self.index_file = self.cache_dir / "cache_index.json"
        self.index = self._load_index()

    def _load_index(self) -> Dict:
        """Load cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_index(self):
        """Save cache index to disk."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save cache index: {e}")

    def get(self, shot_id: str, media_type: str) -> Optional[Dict]:
        """
        Get cached media info.

        Args:
            shot_id: Shot ID
            media_type: Type (impact_img, swing_img, video_frame_0, etc.)

        Returns:
            Cache entry dict with local_path and cloud_url, or None
        """
        key = f"{shot_id}_{media_type}"
        entry = self.index.get(key)

        if entry and Path(entry['local_path']).exists():
            return entry

        return None

    def put(
        self,
        shot_id: str,
        media_type: str,
        local_path: str,
        cloud_url: str = None,
        checksum: str = None
    ) -> Dict:
        """
        Add entry to cache.

        Args:
            shot_id: Shot ID
            media_type: Media type
            local_path: Local file path
            cloud_url: Optional cloud URL
            checksum: Optional file checksum

        Returns:
            Cache entry dict
        """
        key = f"{shot_id}_{media_type}"

        entry = {
            'local_path': str(local_path),
            'cloud_url': cloud_url,
            'checksum': checksum,
            'cached_at': datetime.utcnow().isoformat(),
            'shot_id': shot_id,
            'media_type': media_type
        }

        self.index[key] = entry
        self._save_index()

        return entry

    def exists(self, shot_id: str, media_type: str) -> bool:
        """Check if media is cached and file still exists."""
        entry = self.get(shot_id, media_type)
        return entry is not None

    def get_path(self, shot_id: str, media_type: str, extension: str = "jpg") -> Path:
        """
        Get cache file path for media.

        Args:
            shot_id: Shot ID
            media_type: Media type
            extension: File extension

        Returns:
            Path object for cache file
        """
        # Organize by shot_id subdirectories
        shot_dir = self.cache_dir / shot_id
        shot_dir.mkdir(exist_ok=True)

        return shot_dir / f"{media_type}.{extension}"

    def clear_old_entries(self, days: int = 30):
        """
        Remove cache entries older than specified days.

        Args:
            days: Age threshold in days
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        removed = 0

        for key, entry in list(self.index.items()):
            cached_at = datetime.fromisoformat(entry['cached_at'])
            if cached_at < cutoff:
                # Remove file if exists
                local_path = Path(entry['local_path'])
                if local_path.exists():
                    local_path.unlink()

                # Remove from index
                del self.index[key]
                removed += 1

        if removed > 0:
            self._save_index()
            print(f"Cleared {removed} old cache entries")


class MediaService(BaseService):
    """
    Service for intelligent media handling with caching and optimization.

    Handles downloading, caching, deduplication, and uploading of
    golf shot media (images and video frames).
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize media service.

        Args:
            config: Optional configuration
        """
        super().__init__(config)

        self.media_repo = MediaRepository()
        self.cache = MediaCache(
            cache_dir=self.get_config('cache_dir', './media_cache')
        )

        self._log_info("MediaService initialized", cache_dir=str(self.cache.cache_dir))

    def process_shot_media(
        self,
        shot_id: str,
        api_params: Dict,
        frame_strategy: str = "keyframes"
    ) -> Dict[str, Optional[str]]:
        """
        Process all media for a shot (images + video frames).

        Args:
            shot_id: Shot ID
            api_params: API parameters (report_id, key, session_id, shot_id)
            frame_strategy: Video frame strategy (none, keyframes, half, full)

        Returns:
            Dictionary with media URLs:
            {
                'impact_img': url,
                'swing_img': url,
                'video_frames': comma-separated URLs
            }
        """
        with self._track_performance("process_shot_media"):
            result = {}

            # Process impact image
            impact_url = self._process_image(shot_id, 'impact_img', api_params)
            result['impact_img'] = impact_url

            # Process swing image
            swing_url = self._process_image(shot_id, 'swing_img', api_params)
            result['swing_img'] = swing_url

            # Process video frames
            frame_urls = self._process_video_frames(shot_id, api_params, frame_strategy)
            result['video_frames'] = ','.join(frame_urls) if frame_urls else None

            self._log_info(
                "Shot media processed",
                shot_id=shot_id,
                has_impact=impact_url is not None,
                has_swing=swing_url is not None,
                frame_count=len(frame_urls) if frame_urls else 0
            )

            return result

    def _process_image(
        self,
        shot_id: str,
        image_type: str,
        api_params: Dict
    ) -> Optional[str]:
        """
        Process a single image with caching.

        Args:
            shot_id: Shot ID
            image_type: Type (impact_img or swing_img)
            api_params: API parameters

        Returns:
            Cloud URL or None
        """
        with self._track_performance(f"process_{image_type}"):
            # Check cache first
            cached = self.cache.get(shot_id, image_type)
            if cached and cached.get('cloud_url'):
                self._log_debug(
                    f"Using cached {image_type}",
                    shot_id=shot_id,
                    url=cached['cloud_url'][:50]
                )
                return cached['cloud_url']

            # Build API URL
            base_url = "https://api-v2.golfsvc.com/v2/oldmyuneekor/report/shotimage"
            api_url = f"{base_url}/{api_params['report_id']}/{api_params['key']}/{api_params['session_id']}/{api_params['shot_id']}"

            if image_type == 'impact_img':
                api_url += "/ballimpact"
            elif image_type == 'swing_img':
                api_url += "/topview00"  # Use first frame as swing image
            else:
                return None

            try:
                # Download from API
                response = requests.get(api_url, timeout=10)
                if response.status_code != 200:
                    self._log_warning(
                        f"Failed to download {image_type}",
                        shot_id=shot_id,
                        status=response.status_code
                    )
                    return None

                # Save to cache
                cache_path = self.cache.get_path(shot_id, image_type, "jpg")
                with open(cache_path, 'wb') as f:
                    f.write(response.content)

                # Calculate checksum
                checksum = self.media_repo.calculate_checksum(str(cache_path))

                # Upload to cloud storage
                remote_path = f"{shot_id}/{image_type}.jpg"
                cloud_url = self.media_repo.upload(str(cache_path), remote_path)

                # Update cache index
                self.cache.put(
                    shot_id,
                    image_type,
                    str(cache_path),
                    cloud_url,
                    checksum
                )

                self._log_info(
                    f"Processed {image_type}",
                    shot_id=shot_id,
                    size_kb=len(response.content) // 1024
                )

                return cloud_url

            except Exception as e:
                self._handle_error(e, f"processing {image_type}", raise_error=False)
                return None

    def _process_video_frames(
        self,
        shot_id: str,
        api_params: Dict,
        strategy: str = "keyframes"
    ) -> List[str]:
        """
        Process video frames with configurable strategy.

        Args:
            shot_id: Shot ID
            api_params: API parameters
            strategy: Frame selection strategy

        Returns:
            List of cloud URLs
        """
        with self._track_performance("process_video_frames"):
            # Determine which frames to download
            frame_indices = self._get_frame_indices(strategy)

            if not frame_indices:
                return []

            frame_urls = []

            for frame_idx in frame_indices:
                frame_type = f"video_frame_{frame_idx}"

                # Check cache
                cached = self.cache.get(shot_id, frame_type)
                if cached and cached.get('cloud_url'):
                    frame_urls.append(cached['cloud_url'])
                    continue

                # Download frame
                cloud_url = self._download_video_frame(shot_id, api_params, frame_idx)
                if cloud_url:
                    frame_urls.append(cloud_url)

            self._log_info(
                "Video frames processed",
                shot_id=shot_id,
                strategy=strategy,
                requested=len(frame_indices),
                downloaded=len(frame_urls)
            )

            return frame_urls

    def _download_video_frame(
        self,
        shot_id: str,
        api_params: Dict,
        frame_idx: int
    ) -> Optional[str]:
        """
        Download a single video frame.

        Args:
            shot_id: Shot ID
            api_params: API parameters
            frame_idx: Frame index (0-23)

        Returns:
            Cloud URL or None
        """
        frame_type = f"video_frame_{frame_idx}"

        # Build API URL
        base_url = "https://api-v2.golfsvc.com/v2/oldmyuneekor/report/shotimage"
        api_url = f"{base_url}/{api_params['report_id']}/{api_params['key']}/{api_params['session_id']}/{api_params['shot_id']}"
        api_url += f"/topview{frame_idx:02d}"

        try:
            # Download
            response = requests.get(api_url, timeout=10)
            if response.status_code != 200:
                return None

            # Save to cache
            cache_path = self.cache.get_path(shot_id, frame_type, "jpg")
            with open(cache_path, 'wb') as f:
                f.write(response.content)

            # Calculate checksum
            checksum = self.media_repo.calculate_checksum(str(cache_path))

            # Upload to cloud
            remote_path = f"{shot_id}/frame_{frame_idx:02d}.jpg"
            cloud_url = self.media_repo.upload(str(cache_path), remote_path)

            # Update cache
            self.cache.put(shot_id, frame_type, str(cache_path), cloud_url, checksum)

            return cloud_url

        except Exception as e:
            self._log_error(f"Failed to download frame {frame_idx}", e, shot_id=shot_id)
            return None

    def _get_frame_indices(self, strategy: str) -> List[int]:
        """
        Get frame indices based on strategy.

        Args:
            strategy: Frame selection strategy

        Returns:
            List of frame indices to download
        """
        if strategy == "none":
            return [0]  # Just first frame
        elif strategy == "keyframes":
            return [0, 6, 12, 18, 23]  # 5 key frames
        elif strategy == "half":
            return list(range(0, 24, 2))  # Every other frame (12 frames)
        elif strategy == "full":
            return list(range(24))  # All 24 frames
        else:
            return [0, 6, 12, 18, 23]  # Default to keyframes

    def check_media_exists(self, shot_id: str) -> Dict[str, bool]:
        """
        Check which media exists for a shot.

        Args:
            shot_id: Shot ID

        Returns:
            Dictionary with existence flags
        """
        return {
            'impact_img': self.cache.exists(shot_id, 'impact_img'),
            'swing_img': self.cache.exists(shot_id, 'swing_img'),
            'has_video': any(
                self.cache.exists(shot_id, f'video_frame_{i}')
                for i in range(24)
            )
        }

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_entries = len(self.cache.index)
        total_size = 0

        for entry in self.cache.index.values():
            path = Path(entry['local_path'])
            if path.exists():
                total_size += path.stat().st_size

        return {
            'total_entries': total_entries,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_dir': str(self.cache.cache_dir)
        }

    def clear_cache(self, shot_id: Optional[str] = None, days: Optional[int] = None):
        """
        Clear cache entries.

        Args:
            shot_id: Optional specific shot ID to clear
            days: Optional age threshold (clear entries older than N days)
        """
        if days:
            self.cache.clear_old_entries(days)
            self._log_info(f"Cleared cache entries older than {days} days")
        elif shot_id:
            # Clear specific shot
            removed = 0
            for key in list(self.cache.index.keys()):
                if key.startswith(shot_id):
                    entry = self.cache.index[key]
                    path = Path(entry['local_path'])
                    if path.exists():
                        path.unlink()
                    del self.cache.index[key]
                    removed += 1

            if removed > 0:
                self.cache._save_index()
                self._log_info(f"Cleared {removed} entries for shot {shot_id}")
        else:
            self._log_warning("Clear cache called without parameters")
