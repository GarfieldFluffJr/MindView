"""Convert segmentation labels to 3D meshes with metadata."""
from pathlib import Path
from typing import Optional, Callable
import json
import numpy as np
import nibabel as nib
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
import trimesh

from .synthseg_service import get_label_info, SYNTHSEG_LABELS, TUMOR_LABELS


def segmentation_to_meshes(
    segmentation_path: Path,
    output_glb_path: Path,
    output_metadata_path: Path,
    job_id: str,
    progress_callback: Optional[Callable[[int], None]] = None,
    max_faces_per_region: int = 100000,
    smoothing_iterations: int = 5
) -> bool:
    """
    Convert a segmentation NIfTI to a GLB file with colored meshes and metadata.

    Args:
        segmentation_path: Path to segmentation .nii.gz
        output_glb_path: Path for output .glb file
        output_metadata_path: Path for output .json metadata
        job_id: Job ID for logging
        progress_callback: Optional callback(progress_percent)
        max_faces_per_region: Max faces per mesh for simplification
        smoothing_iterations: Laplacian smoothing iterations

    Returns:
        True if successful
    """
    print(f"[{job_id}] Loading segmentation from {segmentation_path}...")
    img = nib.load(str(segmentation_path))
    data = img.get_fdata().astype(np.int32)
    spacing = img.header.get_zooms()[:3]

    # Get unique labels (excluding background)
    unique_labels = np.unique(data[data > 0]).astype(int).tolist()
    print(f"[{job_id}] Found {len(unique_labels)} regions: {unique_labels[:10]}{'...' if len(unique_labels) > 10 else ''}")

    meshes = []
    regions_metadata = []

    for i, label_id in enumerate(unique_labels):
        if progress_callback:
            progress_callback(10 + int((i / len(unique_labels)) * 70))

        label_info = get_label_info(label_id)
        region_name = label_info["name"]
        color = label_info["color"]
        category = label_info["category"]

        print(f"[{job_id}] Processing {region_name} (label {label_id})...")

        # Create binary mask
        mask = (data == label_id).astype(np.float32)

        # Light smoothing to reduce jagged edges
        mask_smoothed = gaussian_filter(mask, sigma=0.5)

        try:
            verts, faces, normals, _ = marching_cubes(
                mask_smoothed,
                level=0.5,
                spacing=spacing
            )

            if len(verts) == 0:
                print(f"[{job_id}] {region_name}: No vertices, skipping")
                continue

            mesh = trimesh.Trimesh(
                vertices=verts,
                faces=faces,
                vertex_normals=normals
            )

            # Apply Laplacian smoothing
            trimesh.smoothing.filter_laplacian(mesh, iterations=smoothing_iterations)

            # Simplify if needed
            if len(mesh.faces) > max_faces_per_region:
                try:
                    mesh = mesh.simplify_quadric_decimation(max_faces_per_region)
                    print(f"[{job_id}] {region_name}: Simplified to {len(mesh.faces)} faces")
                except Exception as simp_err:
                    print(f"[{job_id}] {region_name}: Simplification failed: {simp_err}")

            # Apply color (RGBA)
            rgba = [color[0], color[1], color[2], 255]
            vertex_colors = np.tile(rgba, (len(mesh.vertices), 1)).astype(np.uint8)
            mesh.visual.vertex_colors = vertex_colors

            # Store metadata in mesh for scene export
            mesh.metadata["region_name"] = region_name
            mesh.metadata["label_id"] = label_id

            meshes.append(mesh)

            # Determine default visibility and opacity based on category
            is_tumor = category == "tumor"
            is_outer = category in ["cortex", "white_matter", "cerebellum"]

            regions_metadata.append({
                "name": region_name,
                "label": region_name.replace("_", " ").title(),
                "labelId": label_id,
                "color": color,
                "category": category,
                "opacity": 1.0 if is_tumor else (0.3 if is_outer else 0.8),
                "defaultVisible": True,
                "vertexCount": len(mesh.vertices),
                "faceCount": len(mesh.faces),
            })

            print(f"[{job_id}] {region_name}: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")

        except Exception as e:
            print(f"[{job_id}] {region_name} failed: {e}")
            continue

    if not meshes:
        raise ValueError("No meshes could be generated from segmentation")

    # Create scene with named meshes
    if progress_callback:
        progress_callback(85)

    print(f"[{job_id}] Creating scene with {len(meshes)} meshes...")
    scene = trimesh.Scene()
    for mesh in meshes:
        region_name = mesh.metadata.get("region_name", "unknown")
        scene.add_geometry(mesh, node_name=region_name)

    # Export GLB
    if progress_callback:
        progress_callback(90)

    print(f"[{job_id}] Exporting to GLB...")
    scene.export(str(output_glb_path), file_type="glb")

    # Check for tumors
    has_tumor = any(r["category"] == "tumor" for r in regions_metadata)

    # Save metadata
    metadata = {
        "regions": regions_metadata,
        "has_tumor": has_tumor,
        "total_regions": len(regions_metadata),
        "segmentation_method": "auto",
    }

    with open(output_metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    if progress_callback:
        progress_callback(100)

    print(f"[{job_id}] Export complete: {output_glb_path}")
    print(f"[{job_id}] Metadata saved: {output_metadata_path}")
    return True


def intensity_to_meshes(
    input_path: Path,
    output_glb_path: Path,
    output_metadata_path: Path,
    job_id: str,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> bool:
    """
    Convert intensity MRI data to meshes using multiple thresholds.
    Used for raw MRI scans that aren't segmented.

    Args:
        input_path: Path to input .nii.gz
        output_glb_path: Path for output .glb file
        output_metadata_path: Path for output .json metadata
        job_id: Job ID for logging
        progress_callback: Optional callback(progress_percent)

    Returns:
        True if successful
    """
    print(f"[{job_id}] Loading intensity data...")
    img = nib.load(str(input_path))
    data = img.get_fdata()
    spacing = img.header.get_zooms()[:3]

    # Smooth the data
    smoothed = gaussian_filter(data, sigma=1.0)
    print(f"[{job_id}] Smoothing complete")

    non_zero = smoothed[smoothed > 0]
    if len(non_zero) == 0:
        raise ValueError("No non-zero values in scan data")

    # Define intensity layers with colors
    layers = [
        {"name": "outer_surface", "percentile": 25, "color": [150, 180, 210], "opacity": 0.3},
        {"name": "mid_layer", "percentile": 50, "color": [100, 150, 200], "opacity": 0.5},
        {"name": "inner_structure", "percentile": 70, "color": [80, 120, 180], "opacity": 0.7},
        {"name": "deep_structures", "percentile": 85, "color": [200, 100, 100], "opacity": 1.0},
    ]

    meshes = []
    regions_metadata = []

    for i, layer in enumerate(layers):
        if progress_callback:
            progress_callback(20 + (i * 15))

        threshold = np.percentile(non_zero, layer["percentile"])
        print(f"[{job_id}] Processing {layer['name']} at threshold {threshold:.2f}")

        try:
            verts, faces, normals, _ = marching_cubes(
                smoothed,
                level=threshold,
                spacing=spacing
            )

            if len(verts) == 0:
                print(f"[{job_id}] {layer['name']}: No vertices, skipping")
                continue

            mesh = trimesh.Trimesh(
                vertices=verts,
                faces=faces,
                vertex_normals=normals
            )

            # Apply smoothing
            trimesh.smoothing.filter_laplacian(mesh, iterations=10)

            # Simplify if needed
            if len(mesh.faces) > 300000:
                try:
                    mesh = mesh.simplify_quadric_decimation(300000)
                except Exception:
                    pass

            # Apply color
            color = layer["color"]
            rgba = [color[0], color[1], color[2], 255]
            vertex_colors = np.tile(rgba, (len(mesh.vertices), 1)).astype(np.uint8)
            mesh.visual.vertex_colors = vertex_colors

            mesh.metadata["region_name"] = layer["name"]
            meshes.append(mesh)

            regions_metadata.append({
                "name": layer["name"],
                "label": layer["name"].replace("_", " ").title(),
                "labelId": i + 1,
                "color": color,
                "category": "intensity_layer",
                "opacity": layer["opacity"],
                "defaultVisible": True,
                "vertexCount": len(mesh.vertices),
                "faceCount": len(mesh.faces),
            })

            print(f"[{job_id}] {layer['name']}: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")

        except Exception as e:
            print(f"[{job_id}] {layer['name']} failed: {e}")
            continue

    if not meshes:
        raise ValueError("No meshes could be generated")

    # Create scene
    if progress_callback:
        progress_callback(85)

    scene = trimesh.Scene()
    for mesh in meshes:
        region_name = mesh.metadata.get("region_name", "unknown")
        scene.add_geometry(mesh, node_name=region_name)

    # Export
    if progress_callback:
        progress_callback(90)

    scene.export(str(output_glb_path), file_type="glb")

    metadata = {
        "regions": regions_metadata,
        "has_tumor": False,
        "total_regions": len(regions_metadata),
        "segmentation_method": "intensity_threshold",
    }

    with open(output_metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    if progress_callback:
        progress_callback(100)

    print(f"[{job_id}] Export complete")
    return True
