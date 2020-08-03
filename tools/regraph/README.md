# Reconstruction Graph
'Regraph' demonstrates how to batch convert the raw data structure provided with the [Reconstruction Subset](../../docs/reconstruction.md) into graphs representing the B-Rep topology with features on faces and edges. 

## Running
Regraph runs in Fusion 360 as a script with the following steps.
1. Follow the [general instructions here](../) to get setup with Fusion 360.
2. Optionally change the `data_dir` in [`regraph_exporter.py`](regraph_exporter.py) to point towards a folder of json data from the reconstruction subset. By default it reconstructs the json files found in [this folder](../testdata).
3. Run the [`regraph_exporter.py`](regraph_exporter.py) addin from within Fusion 360
4. Check the contents of the [`output`](output) folder for the exported files

## Output Format
Data is exported in json that can be read using networkx. See [regraph_viewer.ipynb](regraph_viewer.ipynb) for an example of how to load the data into networkx. From there it can be [loaded into pytorch geometric for example](https://pytorch-geometric.readthedocs.io/en/latest/modules/utils.html#torch_geometric.utils.from_networkx).

## PerExtrude Mode
When `mode` is set to `PerExtrude`, a graph is created for each extrude operation in the timeline.

### Face Labels
The following labels are given for each face:
- `operation_label`: The type of extrude operation combined with the location of the extrude operation. Can be one of: `ExtrudeSide`, `ExtrudeStart`, `ExtrudeEnd`, `CutSide`, `CutStart`, `CutEnd`.
- `last_operation_label`: The true/false flag to indicate if this face was created with the last extrude operation.

### Face Features
The following features are given for each face:
- `surface_type`: The type of surface, see [API reference](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SurfaceTypes.htm).
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
- `action`: The id of the face used at this step.
- `faces`: The ids of the faces that are explained at this step.
- `edges`: The ids of the edges that are explained at this step.

Additionally a `bounding_box` is provided that in the `properties` data structure that can be used to normalize any geometry in model space.

### Face Features
Currently the following features are given for each edge (see [UV-Net](https://arxiv.org/abs/2006.10211)):
- `points`: Points sampled on the face in model space. The order is by xyz point in row first order `u0_v0, u0_v1, u0_v2... uN_vN`.
- `normals`: Normals at the corresponding point location.
- `trimming_mask`: Binary value indicating if the corresponding point is inside/outside the trimming boundary.
