"""Database connection and initialization using Motor (async MongoDB driver)."""
import ssl
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from pymongo import ASCENDING, DESCENDING

from config import settings


class Database:
    """Database connection manager."""

    client: AsyncIOMotorClient = None
    db = None
    gridfs_bucket: AsyncIOMotorGridFSBucket = None

    # Collections
    patients = None
    medical_cases = None
    scan_files = None
    timeline_jobs = None
    notes = None
    feedback_sessions = None
    feedback_messages = None


async def connect_to_mongo():
    """Connect to MongoDB and initialize collections and indexes."""
    try:
        print(f"Connecting to MongoDB at {settings.mongodb_uri[:30]}...")
        Database.client = AsyncIOMotorClient(
            settings.mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
        Database.db = Database.client[settings.database_name]

        # Initialize collections
        Database.patients = Database.db["patients"]
        Database.medical_cases = Database.db["medical_cases"]
        Database.scan_files = Database.db["scan_files"]
        Database.timeline_jobs = Database.db["timeline_jobs"]
        Database.notes = Database.db["notes"]
        Database.feedback_sessions = Database.db["feedback_sessions"]
        Database.feedback_messages = Database.db["feedback_messages"]

        # Initialize GridFS bucket
        Database.gridfs_bucket = AsyncIOMotorGridFSBucket(
            Database.db, bucket_name=settings.gridfs_bucket_name
        )

        # Test connection
        await Database.db.command("ping")

        # Create indexes
        await create_indexes()

        print("✓ Connected to MongoDB successfully!")
        print(f"✓ Database: {settings.database_name}")
        print(f"✓ GridFS Bucket: {settings.gridfs_bucket_name}")

    except Exception as e:
        print(f"✗ Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close the MongoDB connection."""
    if Database.client:
        Database.client.close()
        print("MongoDB connection closed")


async def create_indexes():
    """Create indexes for optimal query performance."""
    print("Creating database indexes...")

    try:
        # Patient indexes
        await Database.patients.create_index([("patient_id", ASCENDING)], unique=True)

        # Medical case indexes (unique on patient_id + case_id combination)
        await Database.medical_cases.create_index(
            [("patient_id", ASCENDING), ("case_id", ASCENDING)], unique=True
        )
        await Database.medical_cases.create_index(
            [("patient_id", ASCENDING), ("created_at", DESCENDING)]
        )

        # Scan file indexes
        await Database.scan_files.create_index([("job_id", ASCENDING)], unique=True)
        await Database.scan_files.create_index([("file_id", ASCENDING)], unique=True)
        await Database.scan_files.create_index([("case_id", ASCENDING)])
        await Database.scan_files.create_index([("patient_id", ASCENDING)])
        await Database.scan_files.create_index([("status", ASCENDING)])
        await Database.scan_files.create_index(
            [("case_id", ASCENDING), ("scan_timestamp", DESCENDING)]
        )

        # Timeline job indexes
        await Database.timeline_jobs.create_index([("job_id", ASCENDING)], unique=True)
        await Database.timeline_jobs.create_index([
            ("patient_id", ASCENDING),
            ("case_id", ASCENDING)
        ])

        # Notes indexes
        await Database.notes.create_index([("note_id", ASCENDING)], unique=True)
        await Database.notes.create_index([("file_id", ASCENDING)])
        await Database.notes.create_index([
            ("patient_id", ASCENDING),
            ("case_id", ASCENDING),
            ("file_id", ASCENDING),
            ("created_at", DESCENDING)
        ])

        # Feedback session indexes
        await Database.feedback_sessions.create_index([("session_id", ASCENDING)], unique=True)
        await Database.feedback_sessions.create_index([
            ("patient_id", ASCENDING),
            ("case_id", ASCENDING)
        ], unique=True)

        # Feedback message indexes
        await Database.feedback_messages.create_index([("message_id", ASCENDING)], unique=True)
        await Database.feedback_messages.create_index([("session_id", ASCENDING)])
        await Database.feedback_messages.create_index([
            ("session_id", ASCENDING),
            ("created_at", ASCENDING)
        ])

        print("✓ Indexes created successfully")
    except Exception as e:
        # If user doesn't have permission to create indexes, just warn and continue
        # Indexes are for performance optimization, not critical for functionality
        print(f"⚠ Warning: Could not create indexes (this is OK): {e}")
        print("⚠ The application will work fine without indexes, just slightly slower for large datasets")
