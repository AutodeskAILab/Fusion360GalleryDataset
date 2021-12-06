# Fusion 360 Gallery Dataset
![Fusion 360 Gallery Dataset](docs/images/fusion_gallery_mosaic.jpg)

The *Fusion 360 Gallery Dataset* contains rich 2D and 3D geometry data derived from parametric CAD models. The dataset is produced from designs submitted by users of the CAD package [Autodesk Fusion 360](https://www.autodesk.com/products/fusion-360/overview) to the [Autodesk Online Gallery](https://gallery.autodesk.com/fusion360). The dataset provides valuable data for learning how people design, including sequential CAD design data, designs segmented by modeling operation, and assemblies containing hierarchy and joint connectivity information.

## Datasets
From the approximately 20,000 designs available we derive several datasets focused on specific areas of research. Currently the following data subsets are available, with more to be released on an ongoing basis.

### [Assembly Dataset](docs/assembly.md) - NEW!
Multi-part CAD assemblies containing rich information on joints, contact surfaces, holes, and the underlying assembly graph structure.

![Fusion 360 Gallery Assembly Dataset](docs/images/assembly_mosaic.jpg)


### [Reconstruction Dataset](docs/reconstruction.md)
Sequential construction sequence information from a subset of simple 'sketch and extrude' designs.

![Fusion 360 Gallery Reconstruction Dataset](docs/images/reconstruction_teaser.jpg)

### [Segmentation Dataset](docs/segmentation.md)

A segmentation of 3D models based on the modeling operation used to create each face, e.g. Extrude, Fillet, Chamfer etc...

![Fusion 360 Gallery Segmentation Dataset](docs/images/segmentation_example.jpg)


## Publications
Please cite the relevant paper below if you use the Fusion 360 Gallery dataset in your research.

### Asembly Dataset
[JoinABLe: Learning Bottom-up Assembly of Parametric CAD Joints](https://arxiv.org/abs/2111.12772)

```
@article{willis2021joinable,
  title={JoinABLe: Learning Bottom-up Assembly of Parametric CAD Joints},
  author={Willis, Karl DD and Jayaraman, Pradeep Kumar and Chu, Hang and Tian, Yunsheng and Li, Yifei and Grandi, Daniele and Sanghi, Aditya and Tran, Linh and Lambourne, Joseph G and Solar-Lezama, Armando and Matusik, Wojciech},
  journal={arXiv preprint arXiv:2111.12772},
  year={2021}
}
```

### Reconstruction Dataset
[Fusion 360 Gallery: A Dataset and Environment for Programmatic CAD Construction from Human Design Sequences](https://arxiv.org/abs/2010.02392)
```
@article{willis2020fusion,
    title={Fusion 360 Gallery: A Dataset and Environment for Programmatic CAD Construction from Human Design Sequences},
    author={Karl D. D. Willis and Yewen Pu and Jieliang Luo and Hang Chu and Tao Du and Joseph G. Lambourne and Armando Solar-Lezama and Wojciech Matusik},
    journal={ACM Transactions on Graphics (TOG)},
    volume={40},
    number={4},
    year={2021},
    publisher={ACM New York, NY, USA}
}
```

### Segmentation Dataset
[BRepNet: A Topological Message Passing System for Solid Models](https://arxiv.org/abs/2104.00706)
```
@inproceedings{lambourne2021brepnet,
    author    = {Lambourne, Joseph G. and Willis, Karl D.D. and Jayaraman, Pradeep Kumar and Sanghi, Aditya and Meltzer, Peter and Shayani, Hooman},
    title     = {BRepNet: A Topological Message Passing System for Solid Models},
    booktitle = {Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)},
    month     = {June},
    year      = {2021},
    pages     = {12773-12782}
}
```

## Download

| Dataset | Designs | Documentation | Download | Paper | Code |
| - | - | - | - | - | - |
| Assembly | 8,251 assemblies / 154,468 parts  | [Documentation](docs/assembly.md) | [Instructions](tools/assembly_download) | [Paper](https://arxiv.org/abs/2111.12772) | [Code](tools) |
| Assembly - Joint | 32,148 joints / 23,029 parts | [Documentation](docs/assembly_joint.md) | [j1.0.0 - 2.8 GB](https://fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/assembly/j1.0.0/j1.0.0.7z) | [Paper](https://arxiv.org/abs/2111.12772) | [Code](tools) |
| Reconstruction | 8,625 sequences | [Documentation](docs/reconstruction.md) | [r1.0.1 - 2.0 GB](https://fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/reconstruction/r1.0.1/r1.0.1.zip) | [Paper](https://arxiv.org/abs/2010.02392) | [Code](tools) |
| Segmentation |  35,680 parts | [Documentation](docs/segmentation.md) | [s2.0.1 - 3.1 GB](https://fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/segmentation/s2.0.1/s2.0.1.zip) | [Paper](https://arxiv.org/abs/2104.00706) | [Code](https://github.com/AutodeskAILab/BRepNet)

### Additional Downloads
- **Reconstruction Dataset Extrude Volumes** [(r1.0.1 - 152 MB)](https://fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/reconstruction/r1.0.1/r1.0.1_extrude_tools.zip): The extrude volumes for each extrude operation in the design timeline.
- **Reconstruction Dataset Face Extrusion Sequences** [(r1.0.1 - 41MB)](https://fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/reconstruction/r1.0.1/r1.0.1_regraph_05.zip): The pre-processed face extrusion sequences used to train our [reconstruction network](tools/regraphnet).
- **Segmentation Extended STEP Dataset** [(s2.0.1 - 483 MB)](https://fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/segmentation/s2.0.1/s2.0.1_extended_step.zip): An extended collection of 42,912 STEP files with associated segmentation information.  This include all STEP data from s2.0.0 along with additional files for which triangle meshes with close to 2500 edges could not be created. 

## Tools
As part of the dataset we provide various tools for working with the data. These tools leverage the [Fusion 360 API](http://help.autodesk.com/view/fusion360/ENU/?guid=GUID-7B5A90C8-E94C-48DA-B16B-430729B734DC) to perform operations such as geometry reconstruction, traversing B-Rep data structures, and conversion to other formats. More information can be found in the [tools directory](tools).


## License
Please refer to the [dataset license](LICENSE.md).
