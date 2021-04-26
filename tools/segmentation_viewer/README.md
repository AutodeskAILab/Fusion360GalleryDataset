# Segmentation Viewer

The easiest way to view the segmentation dataset is by visualizing the .obj files with the triangles colored according to the segment index values n the .seg files.   A very small example utility to do this is provided in [segmentation_viewer.py](tools/segmentation_viewer/segmentation_viewer.py). 

## Setup
Install requirements:
   - `numpy`
   - `trimesh`
   - `pyglet`

## Running
Segmentation Viewer can be run as follows:

```
python -m tools.segmentation_viewer.segmentation_viewer \
   --meshes_folder s1.0.0/meshes                        \                      
   --file_stem 102673_56775b8e_5
```

## Arguments

- `--meshes_folder`: Path to the folder containing the obj meshes in the dataset.

- `--file_stem`: Filename of the file you want to view, without the file extension.
