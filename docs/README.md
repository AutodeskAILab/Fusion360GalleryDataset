# Fusion 360 Gallery Dataset Documentation
Here you will find documentation of the data released as part of the Fusion 360 Gallery Dataset.

## Background
The dataset is extracted from designs created in [Fusion 360](https://www.autodesk.com/products/fusion-360/overview) and then posted to the [Autodesk Online Gallery](https://gallery.autodesk.com/) by users. 


## Data Subsets
Data subsets are specific datasets derived from the full Fusion 360 Gallery Dataset focused on specific areas of research. The 3D model content between data subsets will overlap as they are drawn from the same source, but will likely be formatted differently. We currently provide the following data subsets.

### [Segmentation Subset](segmentation.md)
The Segmentation Subset contains a segmentation of design bodies based on the modeling operation used to create each face, e.g. Extrude, Fillet, Chamfer etc...
![Segmentation Subset](images/segmentation_mosaic.jpg)

### [Reconstruction Subset](reconstruction.md)
The Reconstruction Subset contains sequential design data from a subset of simple 'sketch and extrude' components that enables final geometry to be reconstructed.
![Reconstruction Subset](images/reconstruction_mosaic.jpg)


## Tools
We provide [tools](../tools) to work with the data using Fusion 360. Full documentation of how to use these tools and write your own is provided in the [tools](../tools) directory.
