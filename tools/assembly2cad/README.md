# Assembly2CAD

![Assembly2CAD](https://i.gyazo.com/a43a60bbe9f8a9906da4ea713c2a0728.gif)

[Assembly2CAD](assembly2cad.py) demonstrates how to build a Fusion 360 CAD model from the assembly data provided with the [Assembly Dataset](../../docs/assembly.md). The resulting CAD model has a complete assembly tree and fully specified parametric joints.


## Running
[Assembly2CAD](assembly2cad.py) runs in Fusion 360 as a script with the following steps.
1. Follow the [general instructions here](../) to get setup with Fusion 360.
2. Optionally change the `assembly_file` in [`assembly2cad.py`](assembly2cad.py) to point towards an `assembly.json` provided with the  [Assembly Dataset](../../docs/assembly.md).
3. Optionally change the `png_file` and `f3d_file` in [`assembly2cad.py`](assembly2cad.py) to your preferred name for each file that is exported.
4. Run the [`assembly2cad.py`](assembly2cad.py) script from within Fusion 360. When the script has finished running the design will be open in Fusion 360.
5. Check the contents of `assembly2cad/` directory to find the .f3d that was exported.

## How it Works
If you look into the code you will notice that the hard work is performed by [`assembly_importer.py`](../common/assembly_importer.py) and does the following:
1. Opens and reads `assembly.json`.
2. Gets a list of all .smt files are in the directory where `assembly.json` is located.
3. Looks into the `root` data of `assembly.json` and creates brep bodies from the smt files at the root level.
4. Looks into `tree` and `occurrences` data of the `assembly.json` and creates components/occurrences by importing the appropriate .smt files.
5. After the assembly tree is built it creates joints if specified in `assembly.json`.

