"""
Migration script to move existing files from local filesystem to MongoDB GridFS.

This script:
1. Finds all existing scan files in the database
2. Checks if they have GridFS IDs
3. If not, uploads files from local storage to GridFS
4. Updates database records with GridFS IDs
"""
import asyncio
from pathlib import Path
from bson import ObjectId
from database import connect_to_mongo, close_mongo_connection, Database
from services.gridfs_service import upload_to_gridfs

# Storage directories
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
MESH_DIR = BASE_DIR / "storage" / "meshes"


async def migrate_files():
    """Migrate all existing files from filesystem to GridFS."""
    print("=" * 80)
    print("Starting migration of files to GridFS")
    print("=" * 80)

    await connect_to_mongo()

    try:
        # Find all scan files in the database
        cursor = Database.scan_files.find({})
        files = await cursor.to_list(length=None)

        print(f"\nFound {len(files)} file records in database")

        migrated_count = 0
        skipped_count = 0
        error_count = 0

        for file_doc in files:
            job_id = file_doc.get("job_id")
            print(f"\n{'=' * 60}")
            print(f"Processing job_id: {job_id}")

            # Check if original file already has GridFS ID
            original_file = file_doc.get("original_file", {})
            processed_mesh = file_doc.get("processed_mesh", {})

            update_fields = {}

            # Migrate original file if needed
            if not original_file.get("gridfs_id"):
                print(f"  → Original file missing GridFS ID")

                # Try to find the original file on disk
                file_type = original_file.get("file_type", "")

                # Determine file extension
                if file_type == "nifti":
                    possible_paths = [
                        UPLOAD_DIR / f"{job_id}.nii",
                        UPLOAD_DIR / f"{job_id}.nii.gz"
                    ]
                elif file_type == "obj":
                    possible_paths = [UPLOAD_DIR / f"{job_id}.obj"]
                elif file_type == "multimodal_nifti":
                    # For multimodal, we'll handle each modality separately
                    possible_paths = []
                    for mod in ["t1", "t1ce", "t2", "flair"]:
                        possible_paths.extend([
                            UPLOAD_DIR / f"{job_id}_{mod}.nii",
                            UPLOAD_DIR / f"{job_id}_{mod}.nii.gz"
                        ])
                else:
                    possible_paths = []

                original_uploaded = False
                for orig_path in possible_paths:
                    if orig_path.exists():
                        print(f"  → Found original file: {orig_path}")
                        try:
                            with open(orig_path, "rb") as f:
                                content = f.read()

                            gridfs_id = await upload_to_gridfs(
                                file_data=content,
                                filename=original_file.get("filename", orig_path.name),
                                content_type=original_file.get("content_type", "application/octet-stream"),
                                metadata={
                                    "job_id": job_id,
                                    "patient_id": file_doc.get("patient_id"),
                                    "case_id": file_doc.get("case_id"),
                                    "file_type": "original",
                                    "migrated": True
                                }
                            )

                            update_fields["original_file.gridfs_id"] = gridfs_id
                            print(f"  ✓ Uploaded original to GridFS: {gridfs_id}")
                            original_uploaded = True
                            break

                        except Exception as e:
                            print(f"  ✗ Error uploading original file: {e}")

                if not original_uploaded:
                    print(f"  ⚠ Could not find original file on disk")
            else:
                print(f"  ✓ Original file already has GridFS ID")
                skipped_count += 1

            # Migrate processed mesh if needed
            if file_doc.get("status") == "completed":
                if not processed_mesh or not processed_mesh.get("gridfs_id"):
                    print(f"  → Processed mesh missing GridFS ID")

                    mesh_path = MESH_DIR / f"{job_id}.glb"
                    if mesh_path.exists():
                        print(f"  → Found mesh file: {mesh_path}")
                        try:
                            with open(mesh_path, "rb") as f:
                                mesh_content = f.read()

                            mesh_gridfs_id = await upload_to_gridfs(
                                file_data=mesh_content,
                                filename=f"{job_id}.glb",
                                content_type="model/gltf-binary",
                                metadata={
                                    "job_id": job_id,
                                    "patient_id": file_doc.get("patient_id"),
                                    "case_id": file_doc.get("case_id"),
                                    "file_type": "mesh",
                                    "migrated": True
                                }
                            )

                            update_fields["processed_mesh"] = {
                                "gridfs_id": mesh_gridfs_id,
                                "size_bytes": len(mesh_content)
                            }
                            print(f"  ✓ Uploaded mesh to GridFS: {mesh_gridfs_id}")

                        except Exception as e:
                            print(f"  ✗ Error uploading mesh: {e}")
                            error_count += 1
                    else:
                        print(f"  ⚠ Mesh file not found on disk: {mesh_path}")
                else:
                    print(f"  ✓ Processed mesh already has GridFS ID")

            # Update database if we uploaded anything
            if update_fields:
                try:
                    await Database.scan_files.update_one(
                        {"_id": file_doc["_id"]},
                        {"$set": update_fields}
                    )
                    print(f"  ✓ Updated database record")
                    migrated_count += 1
                except Exception as e:
                    print(f"  ✗ Error updating database: {e}")
                    error_count += 1

        print("\n" + "=" * 80)
        print("Migration Summary")
        print("=" * 80)
        print(f"Total files processed: {len(files)}")
        print(f"Files migrated: {migrated_count}")
        print(f"Files skipped (already migrated): {skipped_count}")
        print(f"Errors: {error_count}")
        print("=" * 80)

    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(migrate_files())
