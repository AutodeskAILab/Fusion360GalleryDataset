# Reconstruction Graph
'Regraph' demonstrates how to batch convert the raw data structure provided with the [Reconstruction Subset](../../docs/reconstruction.md) into a series of graphs representing the B-Rep topology with features on faces and edges. A graph is created for each body after each extrude operation in the timeline.

## Running
Regraph runs in Fusion 360 as a script with the following steps.
1. Follow the [general instructions here](../) to get setup with Fusion 360.
2. Optionally change the `data_dir` in [`regraph.py`](regraph.py) to point towards a folder of json data from the reconstruction subset. By default it reconstructs the json files found in [this folder](../testdata).
3. Run the [`regraph.py`](regraph.py) addin from within Fusion 360
4. Check the contents of the [`output`](output) folder for the exported files

## Output Format
Data is exported in json that can be read using networkx. See [regraph_viewer.ipynb](regraph_viewer.ipynb) for an example of how to load the data into networkx. From there it can be [loaded into pytorch geometric for example](https://pytorch-geometric.readthedocs.io/en/latest/modules/utils.html#torch_geometric.utils.from_networkx).

## Face Labels
The following labels are given for each face:
- `operation_label`: The type of extrude operation combined with the location of the extrude operation. Can be one of: `ExtrudeSide`, `ExtrudeStart`, `ExtrudeEnd`, `CutSide`, `CutStart`, `CutEnd`.
- `last_operation_label`: The true/false flag to indicate if this face was created with the last extrude operation.


## Face Features
The following features are given for each face:
- `surface_type`: The type of surface, see [API reference](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SurfaceTypes.htm).
- `area`: The area of the face.
- `normal_*`: The normal vector of the face.
- `max_tangent_*`: The output directions of maximum curvature at a point at or near the center of the face.
- `max_curvature`: The output magnitude of the maximum curvature at a point at or near the center of the face.
- `min_curvature`: The output magnitude of the maximum curvature at a point at or near the center of the face

## Edge Features
The following features are given for each edge:
- `curve_type`: The type of curve, see [API reference](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Curve3DTypes.htm).
- `length`: The length of the curve.
- `convexity`: The convexity of the edge in relation to the two faces it connects. Can be one of: `Convex`, `Concave`, or `Smooth`.
- `perpendicular`: True/False flag indicating if the edge connects two perpendicular planar faces.
- `direction_*`: The output direction of the curvature at a point at or near the center of the edge.
- `curvature`: The output magnitude of the curvature at a point at or near the center of the edge.

