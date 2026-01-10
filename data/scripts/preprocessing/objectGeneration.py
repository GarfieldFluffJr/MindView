import nibabel as nib
import numpy as np
from skimage import measure

def create_combined_segmented_obj(folder_path, patient_id, output_name):
    # Load the segmentation file (The most important file for labeling)
    seg_img = nib.load(f"{folder_path}/{patient_id}_seg.nii").get_fdata()
    
    # Define your sub-regions based on BraTS 2020 labels
    # Label 1: Necrotic Core, Label 2: Edema, Label 4: Enhancing Tumor
    label_map = {
        "Edema": 2,
        "Core": 1,
        "Enhancing": 4
    }
    
    combined_verts = []
    combined_faces = []
    vert_offset = 0

    with open(output_name, 'w') as f:
        f.write(f"# Combined Segmented Brain: {patient_id}\n")
        
        for name, label_val in label_map.items():
            # Create a binary mask for the specific label
            mask = (seg_img == label_val).astype(float)
            
            if np.max(mask) > 0:
                # Generate mesh for this specific segment
                verts, faces, _, _ = measure.marching_cubes(mask, level=0.5)
                
                # Write an 'object' group tag so the .obj file is segmented
                f.write(f"o {name}\n")
                
                for v in verts:
                    f.write(f"v {v[0]} {v[1]} {v[2]}\n")
                
                for face in faces:
                    # OBJ indices are 1-based and must account for previous vertices
                    f.write(f"f {face[0]+1+vert_offset} {face[1]+1+vert_offset} {face[2]+1+vert_offset}\n")
                
                vert_offset += len(verts)

# Usage
create_combined_segmented_obj(r'C:\Users\prana\Downloads\niiData\BraTS20_Training_367', 'BraTS20_Training_367', 'BraTS_Final.obj')
