# Reconstruction Converter
The Reconstruction Converter (aka Reconverter) demonstrates how to batch convert the raw data structure provided with the [Reconstruction Subset](../../docs/reconstruction.md) into other representations.

## Running
Reconverter runs in Fusion 360 as a script with the following steps.
1. Follow the [general instructions here](../) to get setup with Fusion 360.
2. Optionally change the `data_dir` in [`reconverter.py`](reconverter.py) to point towards a folder of json data from the reconstruction subset. By default it reconstructs the json files found in [this folder](../fusion360gym/data).
3. Run the [`reconverter.py`](reconverter.py) script from within Fusion 360
4. Check the contents of the `output` folder for the exported files
