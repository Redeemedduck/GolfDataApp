"""
Migration Script: Supabase → Firestore

Migrates all golf shot data from Supabase PostgreSQL to Google Firestore.
This is a one-time migration to consolidate the cloud database architecture.

Architecture After Migration:
- SQLite: Local cache (offline access)
- Firestore: Cloud primary (real-time sync)
- BigQuery: Analytics warehouse (auto-synced from Firestore)

Usage:
    python scripts/migrate_supabase_to_firestore.py [--dry-run] [--verify]
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
from supabase import create_client, Client
from google.cloud import firestore
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


class SupabaseToFirestoreMigration:
    """Handles migration from Supabase to Firestore."""

    def __init__(self, dry_run: bool = False):
        """
        Initialize migration.

        Args:
            dry_run: If True, simulate migration without writing to Firestore
        """
        self.dry_run = dry_run

        # Initialize Supabase (source)
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        print(f"✓ Connected to Supabase: {supabase_url}")

        # Initialize Firestore (destination)
        project_id = os.getenv("GCP_PROJECT_ID", "valued-odyssey-474423-g1")
        self.firestore_db = firestore.Client(project=project_id)
        print(f"✓ Connected to Firestore: {project_id}")

        # Collection names
        self.supabase_table = "shots"
        self.firestore_collection = "shots"

        # Migration stats
        self.stats = {
            'total': 0,
            'migrated': 0,
            'errors': 0,
            'skipped': 0
        }

    def fetch_all_shots_from_supabase(self) -> List[Dict]:
        """
        Fetch all shots from Supabase.

        Returns:
            List of shot dictionaries
        """
        print("\n📥 Fetching data from Supabase...")

        all_shots = []
        page_size = 1000
        offset = 0

        while True:
            response = self.supabase.table(self.supabase_table).select("*").range(
                offset, offset + page_size - 1
            ).execute()

            shots = response.data
            if not shots:
                break

            all_shots.extend(shots)
            offset += page_size

            print(f"   Fetched {len(all_shots)} shots...")

        print(f"✓ Total shots in Supabase: {len(all_shots)}")
        return all_shots

    def clean_shot_data(self, shot: Dict) -> Dict:
        """
        Clean and prepare shot data for Firestore.

        Args:
            shot: Raw shot data from Supabase

        Returns:
            Cleaned shot dictionary
        """
        # Remove Supabase-specific fields
        cleaned = {k: v for k, v in shot.items() if k not in ['id', 'created_at']}

        # Ensure shot_id exists
        if 'shot_id' not in cleaned and 'id' in shot:
            cleaned['shot_id'] = shot['id']

        # Add Firestore timestamp
        cleaned['migrated_at'] = datetime.utcnow().isoformat()
        cleaned['updated_at'] = firestore.SERVER_TIMESTAMP

        # Convert None values to 0 for numeric fields
        numeric_fields = [
            'carry', 'total', 'smash', 'ball_speed', 'club_speed',
            'side_spin', 'back_spin', 'launch_angle', 'side_angle',
            'club_path', 'face_angle', 'dynamic_loft', 'attack_angle',
            'impact_x', 'impact_y', 'side_distance', 'descent_angle',
            'apex', 'flight_time', 'optix_x', 'optix_y', 'club_lie'
        ]

        for field in numeric_fields:
            if field in cleaned and cleaned[field] is None:
                cleaned[field] = 0.0

        return cleaned

    def migrate_to_firestore(self, shots: List[Dict]) -> None:
        """
        Migrate shots to Firestore in batches.

        Args:
            shots: List of shot dictionaries to migrate
        """
        print(f"\n📤 Migrating to Firestore...")
        if self.dry_run:
            print("   [DRY RUN MODE - No data will be written]")

        self.stats['total'] = len(shots)
        batch_size = 500  # Firestore batch limit
        batch_count = 0

        for i in range(0, len(shots), batch_size):
            batch_shots = shots[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(shots) + batch_size - 1) // batch_size

            print(f"   Processing batch {batch_num}/{total_batches} ({len(batch_shots)} shots)...")

            if not self.dry_run:
                try:
                    batch = self.firestore_db.batch()

                    for shot in batch_shots:
                        cleaned_shot = self.clean_shot_data(shot)
                        shot_id = cleaned_shot.get('shot_id')

                        if not shot_id:
                            print(f"      Warning: Shot missing shot_id, skipping")
                            self.stats['skipped'] += 1
                            continue

                        doc_ref = self.firestore_db.collection(self.firestore_collection).document(shot_id)
                        batch.set(doc_ref, cleaned_shot, merge=True)

                        self.stats['migrated'] += 1

                    batch.commit()
                    print(f"      ✓ Batch {batch_num} committed successfully")

                except Exception as e:
                    print(f"      ✗ Error in batch {batch_num}: {e}")
                    self.stats['errors'] += len(batch_shots)
            else:
                # Dry run - just validate data
                for shot in batch_shots:
                    cleaned_shot = self.clean_shot_data(shot)
                    if cleaned_shot.get('shot_id'):
                        self.stats['migrated'] += 1
                    else:
                        self.stats['skipped'] += 1

    def verify_migration(self) -> bool:
        """
        Verify migration by comparing counts.

        Returns:
            True if verification passes
        """
        print("\n🔍 Verifying migration...")

        # Count Supabase shots
        supabase_response = self.supabase.table(self.supabase_table).select(
            "shot_id", count="exact"
        ).execute()
        supabase_count = supabase_response.count

        # Count Firestore shots
        firestore_docs = self.firestore_db.collection(self.firestore_collection).stream()
        firestore_count = sum(1 for _ in firestore_docs)

        print(f"   Supabase shots: {supabase_count}")
        print(f"   Firestore shots: {firestore_count}")

        if supabase_count == firestore_count:
            print("   ✓ Counts match!")
            return True
        else:
            print(f"   ✗ Count mismatch! Difference: {abs(supabase_count - firestore_count)}")
            return False

    def print_summary(self):
        """Print migration summary."""
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Total shots:     {self.stats['total']}")
        print(f"Migrated:        {self.stats['migrated']}")
        print(f"Errors:          {self.stats['errors']}")
        print(f"Skipped:         {self.stats['skipped']}")

        if self.dry_run:
            print("\n[DRY RUN - No actual data was written]")
        else:
            success_rate = (self.stats['migrated'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
            print(f"Success rate:    {success_rate:.1f}%")

        print("=" * 60)

    def run(self, verify: bool = False):
        """
        Run the migration.

        Args:
            verify: If True, verify migration after completion
        """
        try:
            # Fetch data
            shots = self.fetch_all_shots_from_supabase()

            if not shots:
                print("⚠️  No shots found in Supabase. Nothing to migrate.")
                return

            # Migrate
            self.migrate_to_firestore(shots)

            # Verify if requested
            if verify and not self.dry_run:
                self.verify_migration()

            # Print summary
            self.print_summary()

            if self.stats['errors'] > 0:
                print("\n⚠️  Migration completed with errors. Review logs above.")
                sys.exit(1)
            else:
                print("\n✓ Migration completed successfully!")

        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate golf shot data from Supabase to Firestore"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate migration without writing to Firestore'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify migration by comparing counts'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("SUPABASE → FIRESTORE MIGRATION")
    print("=" * 60)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No data will be written\n")

    # Confirm migration
    if not args.dry_run:
        response = input("\nThis will migrate all shots to Firestore. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            sys.exit(0)

    # Run migration
    migration = SupabaseToFirestoreMigration(dry_run=args.dry_run)
    migration.run(verify=args.verify)


if __name__ == "__main__":
    main()
