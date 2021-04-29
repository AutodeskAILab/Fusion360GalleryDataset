# Reconstruction Converter
![Reconverter Output](https://i.gyazo.com/8639956e2a5bb551a823f8fcad4c7049.gif)

The Reconstruction Converter (aka Reconverter) demonstrates how to batch convert the raw data structure provided with the [Reconstruction Dataset](../../docs/reconstruction.md) into other representations:
- Images for each curve drawn
- Mesh files after each extrude operation
- B-Rep files of the final design

Reconverter uses common modules from the Fusion 360 Gym directly to allow lower level control.

## Running
Reconverter runs in Fusion 360 as a script with the following steps.
1. Follow the [general instructions here](../) to get setup with Fusion 360.
2. Optionally change the `data_dir` in [`reconverter.py`](reconverter.py) to point towards a folder of json data from the reconstruction dataset. By default it reconstructs the json files found in [this folder](../testdata).
3. Run the [`reconverter.py`](reconverter.py) script from within Fusion 360
4. Check the contents of the `../testdata/output` folder for the exported files
