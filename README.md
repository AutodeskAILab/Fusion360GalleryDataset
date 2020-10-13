# Fusion 360 Gallery Dataset
![Fusion 360 Gallery Dataset](docs/images/fusion_gallery_mosaic.jpg)

The *Fusion 360 Gallery Dataset* contains rich 2D and 3D geometry data derived from parametric CAD models. The dataset is produced from designs submitted by users of the CAD package [Autodesk Fusion 360](https://www.autodesk.com/products/fusion-360/overview) to the [Autodesk Online Gallery](https://gallery.autodesk.com/fusion360). The dataset provides valuable data for learning how people design, including sequential CAD design data, designs segmented by modeling operation, and design hierarchy and connectivity data.

## Datasets
From the approximately 20,000 designs available we derive several datasets focused on specific areas of research. Currently the following data subsets are available, with more to be released on an ongoing basis.

-  [Reconstruction Dataset](docs/reconstruction.md): Sequential construction sequence information from a subset of simple 'sketch and extrude' designs.
- [Segmentation Dataset](docs/segmentation.md): A segmentation of 3D models based on the modeling operation used to create each face, e.g. Extrude, Fillet, Chamfer etc... 

## Download

| Dataset | Designs | Documentation | Download | Paper |
| - | - | - | - | - |
| Reconstruction | 8,625 | [Documentation](docs/reconstruction.md) | [Version d7](https://github.com/karldd/Fusion360GalleryDataset/releases/tag/d7) | [Paper](https://arxiv.org/abs/2010.02392) |
| Segmentation |  35,858 | [Documentation](docs/segmentation.md) | [Version d5](https://github.com/karldd/Fusion360GalleryDataset/releases/tag/d5) | Forthcoming |

## Publications
Please cite the relevant paper below if you use the Fusion 360 Gallery dataset in your research.

#### Reconstruction Dataset
```
@article{willis2020fusion,
    title={Fusion 360 Gallery: A Dataset and Environment for Programmatic CAD Reconstruction},
    author={Karl D. D. Willis and Yewen Pu and Jieliang Luo and Hang Chu and Tao Du and Joseph G. Lambourne and Armando Solar-Lezama and Wojciech Matusik},
    journal={arXiv preprint arXiv:2010.02392},
    year={2020}
}
```

#### Segmentation Dataset
Coming soon...



## Tools
As part of the dataset we provide various tools for working with the data. These tools leverage the [Fusion 360 API](http://help.autodesk.com/view/fusion360/ENU/?guid=GUID-7B5A90C8-E94C-48DA-B16B-430729B734DC) to perform operations such as geometry reconstruction, traversing B-Rep data structures, and conversion to other formats. More information can be found in the [tools directory](tools).


## License
Please refer to the [dataset license](LICENSE.md).
