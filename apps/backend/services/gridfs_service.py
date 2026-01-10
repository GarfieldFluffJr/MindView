"""GridFS service for uploading and downloading files from MongoDB."""
from io import BytesIO
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from database import Database


async def upload_to_gridfs(
    file_data: bytes, filename: str, content_type: str, metadata: dict
) -> ObjectId:
    """
    Upload a file to GridFS.

    Args:
        file_data: The file content as bytes
        filename: The name of the file
        content_type: MIME type of the file
        metadata: Additional metadata to store with the file

    Returns:
        ObjectId: The GridFS file ID

    Raises:
        HTTPException: If upload fails
    """
    try:
        file_id = await Database.gridfs_bucket.upload_from_stream(
            filename,
            BytesIO(file_data),
            metadata={"contentType": content_type, **metadata},
        )
        print(f"✓ Uploaded {filename} to GridFS with ID: {file_id}")
        return file_id
    except Exception as e:
        print(f"✗ Failed to upload {filename} to GridFS: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to upload to GridFS: {str(e)}"
        )


async def download_from_gridfs(file_id: ObjectId) -> bytes:
    """
    Download entire file from GridFS.

    Args:
        file_id: The GridFS file ID

    Returns:
        bytes: The file content

    Raises:
        HTTPException: If download fails or file not found
    """
    try:
        grid_out = await Database.gridfs_bucket.open_download_stream(file_id)
        file_data = await grid_out.read()
        print(f"✓ Downloaded file {file_id} from GridFS ({len(file_data)} bytes)")
        return file_data
    except Exception as e:
        print(f"✗ Failed to download file {file_id} from GridFS: {e}")
        raise HTTPException(
            status_code=404, detail=f"File not found in GridFS: {str(e)}"
        )


async def stream_from_gridfs(
    file_id: ObjectId, filename: str, content_type: str
) -> StreamingResponse:
    """
    Stream a file from GridFS for HTTP download.

    Args:
        file_id: The GridFS file ID
        filename: The name to use for the downloaded file
        content_type: MIME type of the file

    Returns:
        StreamingResponse: FastAPI streaming response

    Raises:
        HTTPException: If streaming fails or file not found
    """
    try:
        grid_out = await Database.gridfs_bucket.open_download_stream(file_id)

        async def file_iterator():
            """Iterate over file chunks for streaming."""
            while True:
                chunk = await grid_out.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                yield chunk

        print(f"✓ Streaming file {file_id} from GridFS as {filename}")
        return StreamingResponse(
            file_iterator(),
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        print(f"✗ Failed to stream file {file_id} from GridFS: {e}")
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")


async def delete_from_gridfs(file_id: ObjectId) -> bool:
    """
    Delete a file from GridFS.

    Args:
        file_id: The GridFS file ID

    Returns:
        bool: True if deletion was successful

    Raises:
        HTTPException: If deletion fails
    """
    try:
        await Database.gridfs_bucket.delete(file_id)
        print(f"✓ Deleted file {file_id} from GridFS")
        return True
    except Exception as e:
        print(f"✗ Failed to delete file {file_id} from GridFS: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete from GridFS: {str(e)}"
        )


async def get_file_metadata(file_id: ObjectId) -> Optional[dict]:
    """
    Get metadata for a file in GridFS.

    Args:
        file_id: The GridFS file ID

    Returns:
        dict: File metadata including filename, size, upload date, etc.

    Raises:
        HTTPException: If file not found
    """
    try:
        # Find the file in fs.files collection
        file_doc = await Database.db.fs.files.find_one({"_id": file_id})
        if not file_doc:
            raise HTTPException(status_code=404, detail="File not found")

        return {
            "file_id": str(file_doc["_id"]),
            "filename": file_doc.get("filename"),
            "length": file_doc.get("length"),
            "upload_date": file_doc.get("uploadDate"),
            "content_type": file_doc.get("metadata", {}).get("contentType"),
            "metadata": file_doc.get("metadata", {}),
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Failed to get metadata for file {file_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get file metadata: {str(e)}"
        )
