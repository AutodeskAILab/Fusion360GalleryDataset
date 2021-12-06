# Joint2CAD

![Joint2CAD](https://i.gyazo.com/d6dfaf36990a4014b5860456abab3494.gif)

[Joint2CAD](joint2cad.py) demonstrates how to build a Fusion 360 CAD model from the joint data provided with the [Assembly Dataset](../../docs/assembly_joint.md). The resulting CAD model has a fully specified parametric joint.


## Running
[Joint2CAD](joint2cad.py) runs in Fusion 360 as a script with the following steps.
1. Follow the [general instructions here](../) to get setup with Fusion 360.
2. Optionally change the `joint_file` in [`joint2cad.py`](joint2cad.py) to point towards a `joint_set_xxxxx.json` provided with the  [Assembly Dataset](../../docs/assembly.md) joint data.
3. Optionally change the `png_file` and `f3d_file` in [`joint2cad.py`](joint2cad.py) to your preferred name for each file that is exported.
4. Run the [`joint2cad.py`](joint2cad.py) script from within Fusion 360. When the script has finished running the design will be open in Fusion 360.
5. Check the contents of `joint2cad/` directory to find the .f3d that was exported.

## How it Works
If you look into the code you will notice that the hard work is performed by [`joint_importer.py`](../common/joint_importer.py) and does the following:
1. Opens and reads `joint_set_xxxxx.json`.
2. Imports the .smt files for each of the parts and creates a component for each.
3. Creates a joint as specified in the `joint_set_xxxxx.json`.

