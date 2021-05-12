"""
Segmentation Viewer

This class allows you to view examples from the Fusion Gallery segmentation dataset.
Additionally you can generate an html view for all the files. 
"""

import argparse
from pathlib import Path
import numpy as np
import igl
import meshplot as mp
import math

class SegmentationViewer:
    def __init__(self, meshes_folder):
        self.meshes_folder = Path(meshes_folder)
        assert self.meshes_folder.exists(), "The meshes folder does not exist"

        bit8_colors = np.array([
                [235, 85, 79],  # ExtrudeSide
                [220, 198, 73], # ExtrudeEnd
                [113, 227, 76], # CutSide
                [0, 226, 124],  # CutEnd
                [23, 213, 221], # Fillet
                [92, 99, 222],  # Chamfer
                [176, 57, 223], # RevolveSide
                [238, 61, 178]  # RevolveEnd
            ]
        )
        self.color_map = bit8_colors / 255.0

    def obj_pathname(self, file_stem):
        obj_pathname = self.meshes_folder / (file_stem + ".obj")
        return obj_pathname

    def seg_pathname(self, file_stem):
        seg_pathname = self.meshes_folder / (file_stem + ".seg")
        return seg_pathname

    def load_mesh(self, obj_file):
        v, f = igl.read_triangle_mesh(str(obj_file))
        return v, f

    def load_data(self, file_stem):
        obj_pathname = self.obj_pathname(file_stem)
        if not obj_pathname.exists():
            print(f"Waring! -- The file {obj_pathname} does not exist")
            return None, None, None
        v, f = self.load_mesh(obj_pathname)

        seg_pathname = self.seg_pathname(file_stem)
        if not seg_pathname.exists():
            print(f"Warning! -- The file {seg_pathname} does not exist")
            return None, None, None
        tris_to_segments = np.loadtxt(seg_pathname, dtype=np.uint64)
        assert f.shape[0] == tris_to_segments.size, "Expect a segment index for every facet"
        facet_colors = self.color_map[tris_to_segments]
        return v, f, facet_colors
        
    def view_segmentation(self, file_stem):
        v, f, facet_colors = self.load_data(file_stem)
        if v is None:
            print(f"The data for {file_stem} could not be loaded")
            return        
        p = mp.plot(v, f, c=facet_colors)

    def save_html(self, file_stem, output_folder):
        v, f, facet_colors = self.load_data(file_stem)
        if v is None:
            print(f"The data for {file_stem} could not be loaded.  Skipping")
            return   
        output_pathname = output_folder / (file_stem + ".html")
        mp.offline()
        p = mp.plot(v, f, c=facet_colors)
        p.save(str(output_pathname))


def create_html(meshes_folder, output_folder):
    viewer = SegmentationViewer(meshes_folder)
    obj_files = [ f for f in meshes_folder.glob("**/*.obj")]
    for file in obj_files:
        viewer.save_html(file.stem, output_folder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--meshes_folder", type=str, required=True, help="Path segmentation meshes folder")
    parser.add_argument("--output_folder", type=str, required=True, help="The folder where you would like to create images")
    args = parser.parse_args()

    meshes_folder = Path(args.meshes_folder)
    if not meshes_folder.exists():
        print(f"The folder {meshes_folder} was not found")

    output_folder = Path(args.output_folder)
    if not output_folder.exists():
        output_folder.mkdir()
        if not output_folder.exists():
            print(f"Failed to create the output folder {output_folder}")

    # Now create the images for all the files
    create_html(meshes_folder, output_folder)

    print("Completed segmentation_viewer.py")
