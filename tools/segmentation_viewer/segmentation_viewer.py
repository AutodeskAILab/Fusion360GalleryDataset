import argparse
from pathlib import Path
import numpy as np
import trimesh

class SegmentationViewer:
  def __init__(self):
      self.color_map = np.array([
        [235, 85, 79, 255],  # ExtrudeSide
        [220, 198, 73, 255], # ExtrudeEnd
        [113, 227, 76, 255], # CutSide
        [0, 226, 124, 255],  # CutEnd
        [23, 213, 221, 255], # Fillet
        [92, 99, 222, 255],  # Chamfer
        [176, 57, 223, 255], # RevolveSide
        [238, 61, 178, 255]  # RevolveEnd
        ], dtype=np.uint8
      )

  def view_file(self, obj_file, seg_file):
      mesh = trimesh.load_mesh(obj_file, process=False)
      tris_to_segments = np.loadtxt(seg_file, dtype=np.uint64)
      facet_colors = self.color_map[tris_to_segments]
      mesh.visual.face_colors = facet_colors
      mesh.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--meshes_folder", type=str, required=True, help="Path segmentation meshes folder")
    parser.add_argument("--file_stem", type=str, required=True, help="The name of the file to view (without extension).")
    args = parser.parse_args()

    meshes_folder = Path(args.meshes_folder)
    obj_file = meshes_folder / (args.file_stem + ".obj")
    seg_file = meshes_folder / (args.file_stem + ".seg")

    viewer = SegmentationViewer()
    viewer.view_file(obj_file, seg_file)

    print("Completed view_segmentation.py")