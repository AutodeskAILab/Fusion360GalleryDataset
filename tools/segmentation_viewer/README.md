# Segmentation Viewer

The easiest way to view the segmentation dataset is by visualizing the `.obj` files with the triangles colored according to the segment index values in the `.seg` files.   A very small example utility to do this is provided in [segmentation_viewer.py](tools/segmentation_viewer/segmentation_viewer.py). 

<img src="https://i.gyazo.com/4b6b076190dc775f62cf8fb903f5a6cb.png" alt="Example Segmentation" width="400"/>

## Setup
Install requirements:
   - `numpy`
   - `meshplot`
   - `igl`

## Notebook
An example of using the segmentation viewer is included in this [jupyter notebook](segmentation_viewer_demo.ipynb).

## Extracting html files for every example in the dataset
Alternatively you may find it useful to extract an html view for each file in the dataset.   The mesh and associated segmentation are then shown in threejs.   To extract the html data run the segmentation viewer as follows.

```
python -m tools.segmentation_viewer.segmentation_viewer \
   --meshes_folder s1.0.0/meshes                        \                      
   --output_folder /path/to/save/visualization_data
```

## Arguments

- `--meshes_folder`: Path to the folder containing the obj meshes in the dataset.

- `--output_folder`: The path to the folder where you want the visualization data to be saved 
