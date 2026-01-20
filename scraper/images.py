"""
Image handling for Uneekor shot assets.
"""
from typing import Any
import requests

from scraper.api import fetch_shot_images
from scraper.config import supabase


def upload_shot_images(report_id: str, key: str, session_id: str, shot_id: str) -> dict[str, str]:
    """
    Fetch images from Uneekor API and upload to Supabase Storage.
    Returns dictionary of public URLs.
    """
    if not supabase:
        print("Warning: Supabase client not initialized, skipping image upload.")
        return {}

    uploaded_urls: dict[str, str] = {}

    try:
        images_data = fetch_shot_images(report_id, key, session_id, shot_id)

        for img in images_data:
            img_name = img.get("name")
            img_path = img.get("image")

            if img_path:
                full_url = f"https://api-v2.golfsvc.com/v2{img_path}"

                # Download image into memory
                img_response = requests.get(full_url, timeout=30)
                if img_response.status_code == 200:
                    image_bytes = img_response.content

                    # Define path in Supabase bucket
                    # Structure: report_id/shot_id_type.jpg
                    storage_path = f"{report_id}/{shot_id}_{img_name}.jpg"

                    try:
                        # Upload to Supabase
                        bucket = "shot-images"
                        supabase.storage.from_(bucket).upload(
                            path=storage_path,
                            file=image_bytes,
                            file_options={"content-type": "image/jpeg", "upsert": "true"},
                        )

                        # Get Public URL
                        public_url = supabase.storage.from_(bucket).get_public_url(storage_path)

                        if img_name == "ballimpact":
                            uploaded_urls["impact_img"] = public_url
                        elif img_name.startswith("topview"):
                            uploaded_urls["swing_img"] = public_url

                    except Exception as storage_err:
                        print(f"Storage Upload Error ({img_name}): {storage_err}")

        return uploaded_urls

    except Exception as exc:
        print(f"Error handling images for shot {shot_id}: {exc}")
        return {}
