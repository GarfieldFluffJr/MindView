# MindView

[![MindView - DeltaHacks 2026](https://d112y698adiu2z.cloudfront.net/photos/production/software_thumbnail_photos/004/151/529/datas/medium.png)](https://youtu.be/9CTsuVTGyxg?si=aDAIGowrsER1MILm)

## Inspiration

Brain tumors are complex and life-altering conditions, with over 3,300 Canadians diagnosed in 2024 alone. Symptoms such as loss of motor control, memory impairment, and seizures can evolve over time, making early and accurate interpretation critical. Our team was first introduced to this challenge through a close friend who was diagnosed with a brain tumor, revealing firsthand how difficult it is for clinicians to track changes, communicate findings, and align on decisions across time and care teams.

MindView was inspired by the need for a clearer, shared way to understand tumor progression over time. Brain tumor care relies on detecting subtle changes across multiple scans and timepoints, which forces clinicians to compare hundreds of 2D slices across disconnected tools. This not only increases cognitive load, but also makes it harder for neurologists, radiologists, and oncologists to communicate clearly - slowing diagnoses and adding friction to high stakes decisions.

## What it does

- **Large-Scale Imaging Data Processing**: The system transforms large amounts of complex imaging data into a clear, interpretable format for clinical use.

- **Interactive 3D Brain Model**: Clinicians can explore a fully interactive 3D representation of the brain and tumor, replacing manual comparison of 2D slices with an intuitive spatial view.

- **Segment Highlighting & Selection**: Users can select and visually isolate tumor and brain segments to focus analysis and support precise, shared discussion.

- **Quantification & Severity Indicators**: The system computes and visualizes measurable changes such as tumor volume and relative position to support objective assessment.

- **Timepoint Comparison**: Clinicians can explore a fully interactive 3D representation of the brain and tumor, replacing manual comparison of 2D slices with an intuitive spatial view.

- **Collaborative Feedback & Annotation**: Clinicians can annotate regions, share diagnoses, and document reasoning, enabling quicker communication across teams or regions where specialists might not be available.

## How we built it

- **Imaging Pipeline**: We inputted raw MRI brain scan data into a fine tuned publically available 3D CNN called SegResNet by MONAI. SegResNet is designed for volumetric medical image segmentation and based on a ResNet/U-net variant. We had to use and fine-tune pre-trained models due to the complexity of our data. The pipeline outputs a segmented file (essentially a 3D array) which represents the presence of either enema, tumor, or necrosis based on density data.

- **3D Segmentation/Visualization**: We used splicing techniques (Nibabel, Skimage) to create an interactive 3d model of brain and tumor models. Using segmentation, data can be visualized in many colors and opacity can be changed.

- **Temporal Analysis**: Each scan is resampled to ensure consistent shaping using scipy with linear interpolation. Intermediate frames are generated linearly by interpolating where each voxel point will be by calculating its temporal distance from both scans. Each voxel grid is then converted to a mesh using skimage. Displayed on the frontend with the React useFrame hook to render the linearly altered shape every frame based on its difference between the two scans.

- **Gemini Chatbot Diagnosis Assistance**: We integrated Gemini via Google’s Developer API as a case feedback and explanation assistant, constrained to analyze pre-computed tumor metrics and highlight potentially concerning patterns for clinician review. The system is designed exclusively for physician facing use, where outputs are interpreted within established clinical workflows and subject to professional review.

## Challenges we ran into

- **Dataset Size**: The .nii and .obj files we used were huge, requiring careful optimization of our processing pipeline to manage memory usage.
- **LLM Safety**: We had to figure out how to safely integrate AI in a decision-support role without overclaiming its capabilites. In the future, we can increase or decrease the scope of Gemini MindView in accordance with legal and ethical concerns.
- **Machine Learning Models**: The model that we used to segment the brain into segments failed on brains with tumors, so we we had to switch our course.

## Accomplishments that we're proud of

- Transforming fragmented 2D MRI slices into an interactive, color-coded 3D visualization.
- Enabled timepoint-based comparison of scans with interpolated transitions to help visualize tumor progression between scans.
- Finetuning a preexisting segmentation model to better detect tumors.

## What we learned

- The importance of consulting industry insiders early to ensure the product addresses real pain points.
- How to allocate work in a time crunch by defining clear responsibilities, setting MVPs, and following a shared execution plan.
- Visualizing imaging data in 3D is more significantly more intuitive than mentally reconstructing multiple 2D slices.

## What's next for MindView

- Real time collaboration using Websockets.
- Optimizing imaging pipeline to increase accuracy and reduce processing time.
- Making the platform HIPAA compliant by implementing secure data handling, access controls, and audit logging.

## Updates I made in my fork post-hackathon

* Disabled control operations (upload file, delete file, create patients and cases) since server memory is extremely low and cannot handle it

* Added notices for users to expect long build and load times since backend goes inactive after a while

* Decided to store entire scan files in MongoDB with GridFS instead of storing locally and only storing metadata so it can persist across multiple devices, and fixed the segmentation so the user can change opacity and inspect different parts of the brain on different devices

* Optimized the timeline by reducing frames and number of voxels and compressed scan files so server can process the timeline

* Added footer with copyright with group member names, and added links to demo, devpost, and github repo

* Hosted everything on Vercel and Render, fully updated and able to deploy automatically

MindView is available live here: [https://mind-view-gamma.vercel.app/](https://mind-view-gamma.vercel.app/)
