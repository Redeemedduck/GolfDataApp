"""
One-Time Sync: Firestore → BigQuery

Syncs all existing shots from Firestore to BigQuery.
After this initial sync, the Cloud Function will handle incremental updates.

Usage:
    python scripts/sync_firestore_to_bigquery.py [--dry-run]
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
from google.cloud import firestore, bigquery
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


class FirestoreToBigQuerySync:
    """Handles one-time sync from Firestore to BigQuery."""

    def __init__(self, dry_run: bool = False):
        """
        Initialize sync.

        Args:
            dry_run: If True, simulate sync without writing to BigQuery
        """
        self.dry_run = dry_run

        # Configuration
        project_id = os.getenv("GCP_PROJECT_ID", "valued-odyssey-474423-g1")
        self.bq_dataset_id = os.getenv("BQ_DATASET_ID", "golf_data")
        self.bq_table_id = os.getenv("BQ_TABLE_ID", "shots")
        self.bq_full_table_id = f"{project_id}.{self.bq_dataset_id}.{self.bq_table_id}"

        # Initialize Firestore (source)
        self.firestore_db = firestore.Client(project=project_id)
        print(f"✓ Connected to Firestore: {project_id}")

        # Initialize BigQuery (destination)
        self.bq_client = bigquery.Client(project=project_id)
        print(f"✓ Connected to BigQuery: {self.bq_full_table_id}")

        # Sync stats
        self.stats = {
            'total': 0,
            'synced': 0,
            'errors': 0,
            'skipped': 0
        }

    def fetch_all_shots_from_firestore(self) -> List[Dict]:
        """
        Fetch all shots from Firestore.

        Returns:
            List of shot dictionaries
        """
        print("\n📥 Fetching data from Firestore...")

        all_shots = []
        shots_ref = self.firestore_db.collection('shots')

        # Fetch all documents
        docs = shots_ref.stream()

        for doc in docs:
            shot_data = doc.to_dict()
            shot_data['shot_id'] = doc.id  # Ensure shot_id is in data
            all_shots.append(shot_data)

            if len(all_shots) % 100 == 0:
                print(f"   Fetched {len(all_shots)} shots...")

        print(f"✓ Total shots in Firestore: {len(all_shots)}")
        return all_shots

    def transform_shot_for_bigquery(self, shot: Dict) -> Dict:
        """
        Transform Firestore shot to BigQuery-compatible format.

        Args:
            shot: Raw shot data from Firestore

        Returns:
            Transformed shot data
        """
        # Copy to avoid modifying original
        transformed = dict(shot)

        # Handle ALL timestamp fields - convert to ISO strings
        # Iterate through all fields to catch any DatetimeWithNanoseconds objects
        for field, value in list(transformed.items()):
            if value is not None:
                # Check if it's a timestamp object
                if hasattr(value, 'isoformat'):
                    transformed[field] = value.isoformat()
                elif isinstance(value, bytes):
                    # Handle binary data
                    transformed[field] = value.decode('utf-8', errors='ignore')

        # Ensure numeric fields are properly typed
        numeric_fields = [
            'carry', 'total', 'ball_speed', 'club_speed', 'smash',
            'back_spin', 'side_spin', 'launch_angle', 'side_angle',
            'club_path', 'face_angle', 'dynamic_loft', 'attack_angle',
            'descent_angle', 'apex', 'flight_time', 'side_distance',
            'impact_x', 'impact_y', 'optix_x', 'optix_y',
            'club_lie', 'lie_angle'
        ]

        for field in numeric_fields:
            if field in transformed:
                if transformed[field] is None or transformed[field] == '':
                    transformed[field] = None
                else:
                    try:
                        transformed[field] = float(transformed[field])
                    except (ValueError, TypeError):
                        transformed[field] = None

        return transformed

    def sync_to_bigquery(self, shots: List[Dict]) -> None:
        """
        Sync shots to BigQuery.

        Args:
            shots: List of shot dictionaries
        """
        if not shots:
            print("⚠️  No shots to sync")
            return

        print(f"\n📤 Syncing {len(shots)} shots to BigQuery...")

        if self.dry_run:
            print("   [DRY RUN MODE - No data will be written]")
            self.stats['synced'] = len(shots)
            return

        # Transform data
        transformed_shots = []
        for shot in shots:
            try:
                transformed = self.transform_shot_for_bigquery(shot)
                transformed_shots.append(transformed)
            except Exception as e:
                print(f"   ✗ Error transforming shot {shot.get('shot_id')}: {e}")
                self.stats['errors'] += 1

        # Configure load job (WRITE_TRUNCATE replaces all data)
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            autodetect=True,  # Auto-detect schema
        )

        # Load data
        try:
            job = self.bq_client.load_table_from_json(
                transformed_shots,
                self.bq_full_table_id,
                job_config=job_config
            )

            # Wait for job to complete
            job.result()

            self.stats['synced'] = len(transformed_shots)
            print(f"✓ Synced {len(transformed_shots)} shots to BigQuery")

        except Exception as e:
            print(f"✗ BigQuery load failed: {e}")
            self.stats['errors'] = len(shots)
            raise

    def verify_sync(self) -> bool:
        """
        Verify sync by comparing counts.

        Returns:
            True if counts match, False otherwise
        """
        print("\n🔍 Verifying sync...")

        try:
            # Get Firestore count
            firestore_count = len(list(self.firestore_db.collection('shots').stream()))

            # Get BigQuery count
            query = f"SELECT COUNT(*) as count FROM `{self.bq_full_table_id}`"
            result = self.bq_client.query(query).to_dataframe()
            bigquery_count = int(result['count'].iloc[0])

            print(f"   Firestore shots: {firestore_count}")
            print(f"   BigQuery shots:  {bigquery_count}")

            if firestore_count == bigquery_count:
                print("   ✓ Counts match!")
                return True
            else:
                print(f"   ✗ Count mismatch! Difference: {abs(firestore_count - bigquery_count)}")
                return False

        except Exception as e:
            print(f"   ✗ Verification failed: {e}")
            return False

    def run(self, verify: bool = False):
        """
        Run the sync process.

        Args:
            verify: If True, verify sync after completion
        """
        self.stats['total'] = 0

        # Fetch shots from Firestore
        shots = self.fetch_all_shots_from_firestore()
        self.stats['total'] = len(shots)

        # Sync to BigQuery
        self.sync_to_bigquery(shots)

        # Verify if requested
        if verify and not self.dry_run:
            self.verify_sync()

        # Print summary
        print("\n" + "=" * 60)
        print("SYNC SUMMARY")
        print("=" * 60)
        print(f"Total shots:     {self.stats['total']}")
        print(f"Synced:          {self.stats['synced']}")
        print(f"Errors:          {self.stats['errors']}")

        if self.dry_run:
            print("\n[DRY RUN - No actual data was written]")

        print("=" * 60)

        if self.stats['errors'] == 0:
            print("\n✓ Sync completed successfully!")
        else:
            print("\n⚠️  Sync completed with errors. Review logs above.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Sync Firestore shots to BigQuery (one-time)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate sync without writing to BigQuery'
    )

    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify sync by comparing counts'
    )

    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt (auto-confirm)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("FIRESTORE → BIGQUERY ONE-TIME SYNC")
    print("=" * 60)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No data will be written\n")

    # Confirm sync
    if not args.dry_run and not args.yes:
        response = input("\nThis will replace all data in BigQuery. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Sync cancelled.")
            sys.exit(0)

    # Run sync
    sync = FirestoreToBigQuerySync(dry_run=args.dry_run)
    sync.run(verify=args.verify)


if __name__ == "__main__":
    main()
