# Regraph: Reconstruction Graph Exporter
'Regraph' demonstrates how to batch convert the raw data structure provided with the [Reconstruction Dataset](../../docs/reconstruction.md) into graphs representing the B-Rep topology with features on faces and edges. 

<img src="https://i.gyazo.com/2e3ad713965f5dea85ccaa6681fe7886.png" width="400" alt="Regraph">

## Running
Regraph runs in Fusion 360 as a script with the following steps.
1. Follow the [general instructions here](../) to get setup with Fusion 360.
2. Optionally change the `data_dir` in [`regraph_exporter.py`](regraph_exporter.py) to point towards a folder of json data from the reconstruction dataset. By default it reconstructs the json files found in [this folder](../testdata).
3. Run the [`regraph_exporter.py`](regraph_exporter.py) addin from within Fusion 360.
4. Check the contents of the `output` folder for the exported files.

To regenerate the data, delete the output folder and rerun.

## Preprocessed Data
We also provide the [pre-processed data](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/reconstruction/r1.0.0/regraph_05.zip) used for training in the paper. For details on how to use this data for training, see the [regraphnet documentation](../regraphnet).

## Output Format
Data is exported in json that can be read using networkx. See [regraph_viewer.ipynb](regraph_viewer.ipynb) for an example of how to load the data into networkx. From there it can be [loaded into pytorch geometric for example](https://pytorch-geometric.readthedocs.io/en/latest/modules/utils.html#torch_geometric.utils.from_networkx). 

## PerExtrude Mode
When `mode` is set to `PerExtrude`, a graph is created for each extrude operation in the timeline.

### Face Features
The following features are given for each face:
- `surface_type`: The type of surface, see [API reference](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SurfaceTypes.htm).
- `reversed`: If the normal of this face is reversed with respect to the surface geometry associated with this face, see [API Reference](http://help.autodesk.com/view/fusion360/ENU/?guid=GUID-54B1FCE4-25BB-4C37-BF2A-A984739B13E1).
- `area`: The area of the face.
- `normal_*`: The normal vector of the face.
- `max_tangent_*`: The output directions of maximum curvature at a point at or near the center of the face.
- `max_curvature`: The output magnitude of the maximum curvature at a point at or near the center of the face.
- `min_curvature`: The output magnitude of the maximum curvature at a point at or near the center of the face

### Edge Features
The following features are given for each edge:
- `curve_type`: The type of curve, see [API reference](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Curve3DTypes.htm).
- `length`: The length of the curve.
- `convexity`: The convexity of the edge in relation to the two faces it connects. Can be one of: `Convex`, `Concave`, or `Smooth`.
- `perpendicular`: True/False flag indicating if the edge connects two perpendicular faces.
- `direction_*`: The output direction of the curvature at a point at or near the center of the edge.
- `curvature`: The output magnitude of the curvature at a point at or near the center of the edge.


## PerFace Mode
When `mode` is set to `PerFace`, a target graph is created for the full design, along with a `*_sequence.json` file that includes the steps to press/pull and extrude the faces to make the final design.

### Sequence Data
The following data is provided for each step in the `sequence` list:
- `start_face`: The id of the start face used at this step.
- `end_face`: The id of the end face used at this step.
- `operation`: The type of extrude operation used at this step. This will be one of either `JoinFeatureOperation`, `CutFeatureOperation`, `IntersectFeatureOperation`, or `NewBodyFeatureOperation`. See [`FeatureOperations` documentation](http://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/FeatureOperations.htm).
- `faces`: The ids of the faces that are explained at this step.
- `edges`: The ids of the edges that are explained at this step.

Additionally a `bounding_box` is provided that in the `properties` data structure that can be used to normalize any geometry in model space.

### Face Features
Currently the following features are given for each edge (see [UV-Net](https://arxiv.org/abs/2006.10211)):
- `surface_type`: The type of surface for the face. This will be one of either `PlaneSurfaceType`, `CylinderSurfaceType`, `ConeSurfaceType`, `SphereSurfaceType`, `TorusSurfaceType`, `EllipticalCylinderSurfaceType`, `EllipticalConeSurfaceType`, or `NurbsSurfaceType`. See [`SurfaceTypes` documentation](http://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SurfaceTypes.htm).
- `points`: Points sampled on the face in model space. The order is by xyz point in row first order `u0_v0, u0_v1, u0_v2... uN_vN`.
- `normals`: Normals at the corresponding point location.
- `trimming_mask`: Binary value indicating if the corresponding point is inside/outside the trimming boundary.

## Face Labels
The following labels are given for each face:
- `operation_label`: The type of extrude operation. Can be one of: `CutFeatureOperation`, `IntersectFeatureOperation`, `JoinFeatureOperation`.
- `location_in_feature_label`: The location of the face in the extrude feature. Can be one of `StartFace`, `SideFace`, or `EndFace`.
- `timeline_index_label`: An integer value indicating the position in the timeline when the face was created.