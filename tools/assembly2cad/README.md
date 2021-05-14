# assembly2cad
![assembly2cad](resources/assembly2cad.gif)
assembly2cad construction demostrates how to construct an f3d model using medatada information comming from a json file (`assembly.json`) and also using 3d model files in smt format.Please have in mind that your metadata and your smt files must be located under assembly_data directory.

## Running
assembly2cad runs in Fusion 360 as a script with the following steps.
1. Follow the [general instructions here](../) to get setup with Fusion 360.
2. Optionally change the `assembly_files_dir` in [`assembly2cad.py`](assembly2cad.py) to point towards another folder where you have your constuction data. (have in mind that metadata info of you model must be a file named `assembly.json`, this is a static value, also make sure that your `assembly.json` is in the same directory as your smt files).
3. Optionally change the `f3d_file_constructed_name` in [`assembly2cad.py`](assembly2cad.py) if you want to have a better name for your constucted file.
4. Run the [`assembly2cad.py`](assembly2cad.py) script from within Fusion 360
5. Check the contents of `assembly2cad/` directory, it should contain your constructed f3d file.

## Digging deep
If you look into the code you will notice that the hard work is performed by [`assembly_importer.py`](../common/assembly_importer.py) and to give you an overall idea these are some of the things this utility is doing:
* Open and read `assembly.json`.
* Get a list of all `smt` files are in directory where `assembly.json` is located.
* Look into "root" property of `assembly.json` and create brep bodies using smt files at root level.
* Look into "tree" and "occurrences" properties of the `assembly.json` and start creating components/occurrences and also create breps using `smt` files according to the data collected.
* After tree is fully constructed we proceed to create all joints if those are specified in `assembly.json`.

