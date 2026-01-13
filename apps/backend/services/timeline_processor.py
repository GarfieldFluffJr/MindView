"""Timeline mesh generation with voxel interpolation for morph targets."""
import json
import os
import numpy as np
import nibabel as nib
from pathlib import Path
from typing import List, Tuple, Optional, Callable
from scipy.ndimage import gaussian_filter, zoom
from skimage.measure import marching_cubes
import trimesh
from datetime import datetime

# Detect if running on a memory-constrained hosted environment
def is_hosted_environment() -> bool:
    """Check if running on Render or other hosted service with limited memory."""
    return os.getenv("RENDER") is not None or os.getenv("RAILWAY_ENVIRONMENT") is not None

# Paths
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
TIMELINE_MESH_DIR = BASE_DIR / "storage" / "timeline_meshes"

# Ensure timeline mesh directory exists
TIMELINE_MESH_DIR.mkdir(parents=True, exist_ok=True)


async def load_nifti_voxels(job_id: str, downsample_factor: float = 1.0) -> Tuple[np.ndarray, tuple]:
    """Load voxel data from a NIfTI file by job_id.

    Downloads from GridFS if not available locally. Downsamples on hosted environments.

    Args:
        job_id: The job ID of the scan file
        downsample_factor: Factor to downsample by (1.0 = full res, 0.5 = half res)

    Returns:
        Tuple of (voxel_data, spacing)
    """
    # Try both .nii and .nii.gz extensions
    nii_path = UPLOAD_DIR / f"{job_id}.nii"
    nii_gz_path = UPLOAD_DIR / f"{job_id}.nii.gz"

    if nii_gz_path.exists():
        path = nii_gz_path
    elif nii_path.exists():
        path = nii_path
    else:
        # File not on filesystem - try to download from GridFS
        print(f"[Timeline] NIfTI file not found locally for {job_id}, downloading from GridFS...")
        from database import Database
        from services.gridfs_service import download_from_gridfs
        from bson import ObjectId

        # Get file record from database
        file_doc = await Database.scan_files.find_one({"job_id": job_id})
        if not file_doc:
            raise FileNotFoundError(f"NIfTI file not found in database for job {job_id}")

        # Get GridFS ID for original file
        original_file = file_doc.get("original_file", {})
        gridfs_id = original_file.get("gridfs_id")
        filename = original_file.get("filename", f"{job_id}.nii.gz")

        if not gridfs_id:
            raise FileNotFoundError(f"NIfTI file not in GridFS for job {job_id}")

        # Download from GridFS
        print(f"[Timeline] Downloading {filename} from GridFS (ID: {gridfs_id})...")
        file_data = await download_from_gridfs(ObjectId(gridfs_id))

        # Determine extension and save to disk temporarily
        ext = ".nii.gz" if filename.endswith(".nii.gz") else ".nii"
        path = UPLOAD_DIR / f"{job_id}{ext}"

        with open(path, "wb") as f:
            f.write(file_data)

        print(f"[Timeline] Downloaded {len(file_data)} bytes to {path}")

    img = nib.load(str(path))
    data = img.get_fdata()
    original_shape = data.shape
    spacing = img.header.get_zooms()[:3]

    # Downsample to reduce memory usage
    if downsample_factor < 1.0:
        print(f"[Timeline] Downsampling from {original_shape} by factor {downsample_factor} to save memory...")
        data = zoom(data, downsample_factor, order=1)
        spacing = tuple(s / downsample_factor for s in spacing)
        print(f"[Timeline] Downsampled to {data.shape}")

    return data, spacing


def align_voxel_grids(voxels_list: List[np.ndarray]) -> List[np.ndarray]:
    """Resample all voxel grids to match the first one's shape.

    Args:
        voxels_list: List of 3D numpy arrays

    Returns:
        List of aligned 3D numpy arrays all with the same shape
    """
    target_shape = voxels_list[0].shape
    aligned = [voxels_list[0]]

    for voxels in voxels_list[1:]:
        if voxels.shape != target_shape:
            # Calculate zoom factors
            factors = tuple(t / s for t, s in zip(target_shape, voxels.shape))
            resampled = zoom(voxels, factors, order=1)  # Linear interpolation
            aligned.append(resampled)
        else:
            aligned.append(voxels)

    return aligned


def interpolate_voxels(
    voxels_a: np.ndarray,
    voxels_b: np.ndarray,
    num_frames: int
) -> List[np.ndarray]:
    """Generate interpolated voxel grids between two scans.

    Args:
        voxels_a: First voxel grid
        voxels_b: Second voxel grid (must have same shape as voxels_a)
        num_frames: Number of intermediate frames to generate

    Returns:
        List of interpolated voxel grids (excluding the endpoints)
    """
    frames = []
    for i in range(num_frames):
        t = (i + 1) / (num_frames + 1)  # Exclude endpoints (0 and 1)
        interpolated = (1 - t) * voxels_a + t * voxels_b
        frames.append(interpolated)
    return frames


def voxels_to_mesh(
    voxels: np.ndarray,
    spacing: tuple,
    threshold: float,
    simplify_target: int = None  # Auto-determined based on environment
) -> Optional[trimesh.Trimesh]:
    """Convert voxel data to mesh using marching cubes.

    Args:
        voxels: 3D numpy array of voxel data
        spacing: Voxel spacing tuple (x, y, z)
        threshold: Isosurface threshold value
        simplify_target: Target number of faces after simplification (auto if None)

    Returns:
        Trimesh object or None if no mesh could be generated
    """
    # Auto-determine simplification target based on environment
    if simplify_target is None:
        simplify_target = 50000 if is_hosted_environment() else 100000

    print(f"[voxels_to_mesh] Input shape: {voxels.shape}, spacing: {spacing}, threshold: {threshold}")
    print(f"[voxels_to_mesh] Simplify target: {simplify_target} faces")
    print(f"[voxels_to_mesh] Voxel stats - min: {voxels.min():.2f}, max: {voxels.max():.2f}, mean: {voxels.mean():.2f}")

    # Smooth to reduce noise
    smoothed = gaussian_filter(voxels, sigma=1.0)
    print(f"[voxels_to_mesh] Smoothed stats - min: {smoothed.min():.2f}, max: {smoothed.max():.2f}")

    try:
        verts, faces, normals, _ = marching_cubes(
            smoothed, level=threshold, spacing=spacing
        )
        print(f"[voxels_to_mesh] Marching cubes produced {len(verts)} vertices, {len(faces)} faces")
    except Exception as e:
        print(f"[voxels_to_mesh] Marching cubes FAILED: {e}")
        return None

    if len(verts) == 0:
        print(f"[voxels_to_mesh] No vertices generated - threshold {threshold} may be outside data range")
        return None

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)

    # Smooth mesh
    trimesh.smoothing.filter_laplacian(mesh, iterations=5)

    # Decimate if too large
    if len(mesh.faces) > simplify_target:
        try:
            mesh = mesh.simplify_quadric_decimation(simplify_target)
        except Exception:
            pass  # Keep original if simplification fails

    return mesh


def compute_vertex_displacements(
    base_mesh: trimesh.Trimesh,
    voxels: np.ndarray,
    spacing: tuple,
    threshold: float,
    displacement_scale: float = 2.0
) -> np.ndarray:
    """Compute vertex displacements by sampling voxel field.

    For each vertex in the base mesh, sample the voxel field and compute
    displacement along the vertex normal based on the difference from threshold.

    Args:
        base_mesh: The base mesh with vertices and normals
        voxels: 3D voxel array for the target frame
        spacing: Voxel spacing (x, y, z)
        threshold: Isosurface threshold value
        displacement_scale: Scale factor for displacements

    Returns:
        Array of vertex positions after displacement
    """
    from scipy.ndimage import map_coordinates

    vertices = np.array(base_mesh.vertices)
    normals = np.array(base_mesh.vertex_normals)

    # Convert vertex positions to voxel coordinates
    voxel_coords = vertices / np.array(spacing)

    # Clamp coordinates to valid range
    for i in range(3):
        voxel_coords[:, i] = np.clip(voxel_coords[:, i], 0, voxels.shape[i] - 1)

    # Sample voxel values at vertex positions
    sampled_values = map_coordinates(
        voxels,
        voxel_coords.T,
        order=1,  # Linear interpolation
        mode='nearest'
    )

    # Compute displacement along normals based on difference from threshold
    # Positive when surface should move outward, negative when inward
    displacement_amount = (sampled_values - threshold) * displacement_scale

    # Apply displacement along normals
    displaced_vertices = vertices + normals * displacement_amount[:, np.newaxis]

    return displaced_vertices.astype(np.float32)


def create_morph_data_json(
    base_mesh: trimesh.Trimesh,
    morph_meshes: List[trimesh.Trimesh],
    scan_timestamps: List[datetime],
    output_path: Path
) -> None:
    """Create JSON file containing morph target delta data.

    The JSON structure contains:
    - frame_count: Total number of frames (including base)
    - vertex_count: Number of vertices per frame
    - timestamps: ISO timestamps for each original scan
    - scan_indices: Which frame indices correspond to actual scans
    - deltas: List of vertex position deltas from base mesh

    Args:
        base_mesh: The base mesh (first frame)
        morph_meshes: List of morph target meshes (or displaced vertex arrays)
        scan_timestamps: Timestamps for the original scans
        output_path: Path to save the JSON file
    """
    base_verts = np.array(base_mesh.vertices, dtype=np.float32)

    morph_data = {
        "frame_count": len(morph_meshes) + 1,  # +1 for base
        "vertex_count": len(base_verts),
        "timestamps": [ts.isoformat() if isinstance(ts, datetime) else ts for ts in scan_timestamps],
        "deltas": []
    }

    for morph in morph_meshes:
        # Handle both trimesh objects and numpy arrays
        if isinstance(morph, np.ndarray):
            morph_verts = morph
        else:
            morph_verts = np.array(morph.vertices, dtype=np.float32)

        delta = morph_verts - base_verts
        # Store as flattened list for JSON
        morph_data["deltas"].append(delta.flatten().tolist())

    # Save as JSON
    with open(output_path, 'w') as f:
        json.dump(morph_data, f)


def export_timeline_glb(
    base_mesh: trimesh.Trimesh,
    output_path: Path
) -> None:
    """Export the base mesh as GLB file.

    Args:
        base_mesh: The base mesh to export
        output_path: Path to save the GLB file
    """
    # Apply a neutral color
    vertex_colors = np.tile([180, 180, 200, 255], (len(base_mesh.vertices), 1)).astype(np.uint8)
    base_mesh.visual.vertex_colors = vertex_colors

    base_mesh.export(str(output_path), file_type="glb")


async def process_timeline_generation(
    job_id: str,
    patient_id: int,
    case_id: int,
    scan_job_ids: List[str],
    scan_timestamps: List[datetime],
    frames_between: int,
    update_progress: Callable[[str, int, str], None]
) -> str:
    """Main timeline processing pipeline.

    Steps:
    1. Load all NIfTI voxel grids
    2. Align to common grid size
    3. For each adjacent pair, generate interpolated frames
    4. Run marching cubes on ALL frames (guarantees same topology!)
    5. Export base mesh as GLB + morph deltas as JSON

    Args:
        job_id: Unique job identifier
        patient_id: Patient ID
        case_id: Case ID
        scan_job_ids: List of scan job IDs in chronological order
        scan_timestamps: List of scan timestamps
        frames_between: Number of interpolation frames between each scan pair
        update_progress: Callback function(job_id, progress, step_description)

    Returns:
        Path to the generated GLB file
    """
    # Memory optimization: Only apply on hosted environments (Render, Railway, etc.)
    is_hosted = is_hosted_environment()
    downsample_factor = 1.0  # Default: full resolution

    if is_hosted:
        print(f"[Timeline {job_id}] Detected hosted environment - applying memory optimizations")
        # Limit to 3 scans max on hosted to prevent OOM
        MAX_SCANS = 3
        if len(scan_job_ids) > MAX_SCANS:
            print(f"[Timeline {job_id}] Memory optimization: Limiting from {len(scan_job_ids)} scans to {MAX_SCANS}")
            # Take first, middle, and last scan for good temporal coverage
            indices = [0, len(scan_job_ids) // 2, len(scan_job_ids) - 1]
            scan_job_ids = [scan_job_ids[i] for i in indices]
            scan_timestamps = [scan_timestamps[i] for i in indices]

        # Reduce interpolation frames to save memory
        frames_between = min(frames_between, 5)  # Max 5 frames between scans
        print(f"[Timeline {job_id}] Using {frames_between} interpolation frames for memory efficiency")

        # Downsample to half resolution (1/8 memory usage)
        downsample_factor = 0.5
        print(f"[Timeline {job_id}] Downsampling to {downsample_factor}x for memory efficiency")

    update_progress(job_id, 5, f"Loading NIfTI files{'(downsampled)' if is_hosted else ''}...")

    # Step 1: Load voxel data
    voxels_list = []
    spacing = None
    for i, scan_id in enumerate(scan_job_ids):
        update_progress(job_id, 5 + int(10 * (i + 1) / len(scan_job_ids)),
                       f"Loading scan {i+1}/{len(scan_job_ids)}")
        voxels, sp = await load_nifti_voxels(scan_id, downsample_factor=downsample_factor)
        voxels_list.append(voxels)
        if spacing is None:
            spacing = sp

    update_progress(job_id, 18, "Aligning voxel grids...")

    # Step 2: Align grids
    aligned_voxels = align_voxel_grids(voxels_list)
    del voxels_list  # Free memory

    update_progress(job_id, 22, "Interpolating voxels...")

    # Step 3: Generate all frame voxels
    all_frame_voxels = [aligned_voxels[0]]  # Start with first scan
    scan_frame_indices = [0]  # Track which frames are actual scans

    for i in range(len(aligned_voxels) - 1):
        interp_frames = interpolate_voxels(
            aligned_voxels[i],
            aligned_voxels[i + 1],
            frames_between
        )

        for frame in interp_frames:
            all_frame_voxels.append(frame)

        all_frame_voxels.append(aligned_voxels[i + 1])
        scan_frame_indices.append(len(all_frame_voxels) - 1)

    del aligned_voxels  # Free memory

    update_progress(job_id, 42, "Generating meshes...")
    total_frames = len(all_frame_voxels)

    # Step 4: Calculate global threshold for consistent topology
    # Use the same threshold across all frames
    print(f"[Timeline] Calculating threshold from {len(all_frame_voxels)} frames...")
    print(f"[Timeline] Frame 0 stats - shape: {all_frame_voxels[0].shape}, min: {all_frame_voxels[0].min():.2f}, max: {all_frame_voxels[0].max():.2f}")

    all_non_zero = np.concatenate([v[v > 0].flatten() for v in all_frame_voxels[:3]])  # Sample from first few
    print(f"[Timeline] Non-zero values count: {len(all_non_zero)}")
    if len(all_non_zero) == 0:
        raise ValueError("No non-zero values in voxel data")

    # Check if data is binary (all non-zero values are the same)
    unique_non_zero = np.unique(all_non_zero)
    is_binary_data = len(unique_non_zero) == 1

    if is_binary_data:
        # Binary/segmentation mask - use midpoint between 0 and the value
        global_threshold = unique_non_zero[0] / 2.0
        print(f"[Timeline] Detected binary data, using threshold: {global_threshold}")
    else:
        global_threshold = np.percentile(all_non_zero, 50)
        print(f"[Timeline] Detected continuous data, using threshold: {global_threshold}")

    # Generate base mesh from first frame
    update_progress(job_id, 45, "Generating base mesh...")
    base_mesh = voxels_to_mesh(all_frame_voxels[0], spacing, threshold=global_threshold)
    if base_mesh is None:
        raise ValueError("Failed to generate base mesh from first frame")

    base_vertex_count = len(base_mesh.vertices)
    print(f"[Timeline] Base mesh has {base_vertex_count} vertices")

    glb_path = TIMELINE_MESH_DIR / f"{job_id}.glb"
    json_path = TIMELINE_MESH_DIR / f"{job_id}.morphs.json"

    if is_binary_data:
        # Binary data: all frames should have same topology, use marching cubes for each
        print(f"[Timeline] Using marching cubes for all {total_frames} frames (binary data)")
        meshes = [base_mesh]
        for i, voxels in enumerate(all_frame_voxels[1:], 1):
            mesh = voxels_to_mesh(voxels, spacing, threshold=global_threshold)
            if mesh is None:
                raise ValueError(f"Failed to generate mesh for frame {i}")
            if len(mesh.vertices) != base_vertex_count:
                print(f"[Timeline] Warning: Frame {i} has {len(mesh.vertices)} vertices, expected {base_vertex_count}")
                # Fall back to displacement method for this frame
                displaced = compute_vertex_displacements(base_mesh, voxels, spacing, global_threshold)
                meshes.append(displaced)
            else:
                meshes.append(mesh)
            update_progress(job_id, 45 + int(45 * i / (total_frames - 1)),
                           f"Generating mesh {i+1}/{total_frames}")

        morph_data = meshes[1:]
    else:
        # Continuous data: use displacement-based morphing to maintain topology
        print(f"[Timeline] Using displacement morphing for {total_frames} frames (continuous data)")
        morph_data = []
        for i, voxels in enumerate(all_frame_voxels[1:], 1):
            displaced = compute_vertex_displacements(base_mesh, voxels, spacing, global_threshold)
            morph_data.append(displaced)
            update_progress(job_id, 45 + int(45 * i / (total_frames - 1)),
                           f"Computing displacements {i+1}/{total_frames}")

    update_progress(job_id, 92, "Exporting GLB and morph data...")

    # Export GLB (base mesh only)
    export_timeline_glb(base_mesh, glb_path)

    # Export morph data as JSON
    create_morph_data_json(base_mesh, morph_data, scan_timestamps, json_path)

    update_progress(job_id, 100, "Complete")

    return str(glb_path)
