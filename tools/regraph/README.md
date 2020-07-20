# Reconstruction Graph
'Regraph' demonstrates how to batch convert the raw data structure provided with the [Reconstruction Subset](../../docs/reconstruction.md) into a series of graphs representing the B-Rep topology with features on faces and edges.

## Running
Regraph runs in Fusion 360 as a script with the following steps.
1. Follow the [general instructions here](../) to get setup with Fusion 360.
2. Optionally change the `data_dir` in [`regraph.py`](regraph.py) to point towards a folder of json data from the reconstruction subset. By default it reconstructs the json files found in [this folder](../testdata).
3. Run the [`regraph.py`](regraph.py) script from within Fusion 360
4. Check the contents of the `../testdata/output` folder for the exported files

## Face Labels
The following labels are given for each face:
- `timeline_label`: A normalized index of the extrude feature in the timeline. If there is only 1 extrude operation, this value will be `1.0`. If there are 3 extrude operations the values will be `0.33`, `0.66`, `1.0`.
- `operation_label`: The type of extrude operation combined with the location of the extrude operation. Can be one of: `ExtrudeSide`, `ExtrudeStart`, `ExtrudeEnd`, `CutSide`, `CutStart`, `CutEnd`.

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
- `concave`: Flag indicating if the edge connects concave faces.
- `direction_*`: The output direction of the curvature at a point at or near the center of the edge.
- `curvature`: The output magnitude of the curvature at a point at or near the center of the edge.

