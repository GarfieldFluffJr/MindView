"""
Migration script to populate metadata for existing files in the database.

This script reads metadata JSON files from the filesystem and updates the
corresponding database records with the metadata information.
"""
import asyncio
import json
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

from config import settings

# Paths
BASE_DIR = Path(__file__).parent
METADATA_DIR = BASE_DIR / "storage" / "metadata"


async def migrate_metadata():
    """Migrate metadata from JSON files to database records."""
    print("Starting metadata migration...")

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.database_name]
    scan_files = db["scan_files"]

    # Find all completed files with empty or missing metadata
    query = {
        "status": "completed",
        "$or": [
            {"metadata": {"$exists": False}},
            {"metadata": {}},
            {"metadata.regions": {"$exists": False}},
            {"metadata.regions": []},
        ]
    }

    files_to_migrate = await scan_files.find(query).to_list(length=None)
    print(f"Found {len(files_to_migrate)} files that need metadata migration")

    migrated = 0
    skipped = 0
    errors = 0

    for file_doc in files_to_migrate:
        job_id = file_doc.get("job_id")
        print(f"\nProcessing {job_id}...")

        # Check if metadata JSON file exists
        metadata_path = METADATA_DIR / f"{job_id}.json"
        if not metadata_path.exists():
            print(f"  ⚠ Metadata file not found: {metadata_path}")
            skipped += 1
            continue

        try:
            # Load metadata from JSON
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            regions_count = len(metadata.get("regions", []))
            print(f"  ✓ Loaded metadata with {regions_count} regions")

            # Validate metadata structure
            if "regions" not in metadata:
                metadata["regions"] = []
            if "has_tumor" not in metadata:
                metadata["has_tumor"] = False
            if "total_regions" not in metadata:
                metadata["total_regions"] = len(metadata.get("regions", []))

            # Update database record
            result = await scan_files.update_one(
                {"job_id": job_id},
                {"$set": {"metadata": metadata}}
            )

            if result.modified_count > 0:
                print(f"  ✓ Updated database record with {regions_count} regions")
                migrated += 1
            else:
                print(f"  ⚠ Database record not modified")
                skipped += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            errors += 1

    print("\n" + "="*60)
    print("Migration Summary:")
    print(f"  ✓ Successfully migrated: {migrated}")
    print(f"  ⚠ Skipped: {skipped}")
    print(f"  ✗ Errors: {errors}")
    print(f"  Total processed: {len(files_to_migrate)}")
    print("="*60)

    # Close connection
    client.close()


if __name__ == "__main__":
    asyncio.run(migrate_metadata())
