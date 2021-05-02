# Segmentation Viewer

The easiest way to view the segmentation dataset is by visualizing the `.obj` files with the triangles colored according to the segment index values n the .seg files.   A very small example utility to do this is provided in [segmentation_viewer.py](tools/segmentation_viewer/segmentation_viewer.py). 

## Setup
Install requirements:
   - `numpy`
   - `meshplot`
   - `igl`

## Notebook
An example of using the segmentation viewer is included in this [jupyter notebook](tools/segmentation_viewer/segmentation_viewer_demo.ipynb).

## Extracting html files for every example in the dataset
Alternatively you may find it useful to extract an html view for each file in the dataset.   The mesh and associated segmentation are then shown in threesj.   To extract the html data then run the segmentation viewer as follows.

```
python -m tools.segmentation_viewer.segmentation_viewer \
   --meshes_folder s1.0.0/meshes                        \                      
   --output_folder /path/to/save/visualization_data
```

## Arguments

- `--meshes_folder`: Path to the folder containing the obj meshes in the dataset.

- `--output_folder`: The path to the folder where you want the visualization data to be saved 
