# Reconstruction Graph
'Regraph' demonstrates how to batch convert the raw data structure provided with the [Reconstruction Subset](../../docs/reconstruction.md) into a series of graphs representing the B-Rep topology with features on faces and edges.

## Running
Regraph runs in Fusion 360 as a script with the following steps.
1. Follow the [general instructions here](../) to get setup with Fusion 360.
2. Optionally change the `data_dir` in [`regraph.py`](regraph.py) to point towards a folder of json data from the reconstruction subset. By default it reconstructs the json files found in [this folder](../testdata).
3. Run the [`regraph.py`](regraph.py) script from within Fusion 360
4. Check the contents of the `../testdata/output` folder for the exported files
