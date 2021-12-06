# Fusion 360 Gallery Dataset Documentation
Here you will find documentation of the data released as part of the Fusion 360 Gallery Dataset. Each dataset is extracted from designs created in [Fusion 360](https://www.autodesk.com/products/fusion-360/overview) and then posted to the [Autodesk Online Gallery](https://gallery.autodesk.com/) by users. 


## Datasets
We derive several datasets focused on specific areas of research. The 3D model content between data subsets will overlap as they are drawn from the same source, but will likely be formatted differently. We provide the following datasets.

### [Assembly Dataset](assembly.md)
The Assembly Dataset contains multi-part CAD assemblies with rich information on joints, contact surfaces, holes, and the underlying assembly graph structure. 
![Assembly Dataset](images/assembly_mosaic.jpg)

### [Assembly Dataset - Joint Data](assembly_joint.md)
The Assembly Dataset joint data contains pairs of parts extracted from CAD assemblies, with one or more joints defined between them.
![Assembly Dataset - Joint Data](images/assembly_joint_mosaic.jpg)

### [Reconstruction Dataset](reconstruction.md)
The Reconstruction Dataset contains construction sequence information from a subset of simple 'sketch and extrude' designs.
![Reconstruction Dataset](images/reconstruction_mosaic.jpg)

### [Segmentation Dataset](segmentation.md)
The Segmentation Dataset contains segmented 3D models based on the modeling operation used to create each face, e.g. Extrude, Fillet, Chamfer etc... 
![Segmentation Dataset](images/segmentation_mosaic.jpg)


## Tools
We provide [tools](../tools) to work with the data using Fusion 360. Full documentation of how to use these tools and write your own is provided in the [tools](../tools) directory.
