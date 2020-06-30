# Reconstruction Compiler
The Reconstruction Compiler (aka recompiler) converts the raw data structure provided with the [Reconstruction Subset](../../docs/reconstruction.md) into compact sequential set of design commands.

## Example code

```
            compiler = JsonActionCompiler(json_file)  # json_file is the original fusion data
            compiler.parse()

            tree = compiler.getTree()  # The CSG tree of the model
            actions = compiler.getActions()  # The action sequence acquired by traversing the tree

```
#### Features to be implemented 
- [ ] Expand support to other curve types other than Line3D


# Excecutor
The excecutor takes as input a sequence of actions, and excecutes them to reconstruct the model.

## Fusion excecutor
The fusion excecutor converts the actions to the format [Fusion Gym](../fusion360gym) can run with, and calls Fusion Gym commands to rebuild the model in Fusion. 
Example code can be found [here](./test_recompiler/test_recompiler_fusion.py). 

The code is expected to run inside of Fusion. Details of how to run the code can be found [here](https://modthemachine.typepad.com/my_weblog/2019/09/debug-fusion-360-add-ins.html).

#### Features to be implemented 
- [ ] Expand support to other curve types other than Line3D
- [ ] Currently the "correction matrix" calculation is included in the reconstruction process, it should be swapped if it is pre-calculated

## FreeCAD excecutor
[FreeCAD](https://github.com/FreeCAD/FreeCAD) is an open source CAD software. It can be used as a python package as well for geometric computation.
The FreeCAD excecutor converts the actions to the format FreeCAD can run with, and use the FreeCAD module to rebuild the model. 
Example code can be found [here](./test_recompiler/test_recompiler_freecad.py).

#### Note:
- To run FreeCAD as a python module, it has to run with the python version compatible with FreeCAD. (The python version used for its build)  
- The path to `FreeCAD.so` or `FreeCAD.dll` file need to be added to `sys.path`

#### Features to be implemented 
- [ ] Expand support to other curve types other than Line3D







