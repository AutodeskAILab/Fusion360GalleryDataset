# AssemblyGraph
Generate a graph representation from an assembly.

## Setup
Install requirements:
- `numpy`
- `networkx`
- `meshplot`
- `trimesh`
- `tqdm`

## [Assembly Viewer](assembly_viewer.ipynb)
Example notebook showing how to use the [`AssemblyGraph`](assembly_graph.py) class to generate a NetworkX graph and visualize it as both a graph and a 3D model.

![Assembly Viewer](https://i.gyazo.com/ef0ab11a58d10da2b25828dceed1f6f1.gif)

## [Assembly2Graph](assembly2graph.py)
Utility script to convert a folder of assemblies into a NetworkX node-link graph JSON file format.

```
python assembly2graph.py --input path/to/a1.0.0/assembly --output path/to/graphs
```

