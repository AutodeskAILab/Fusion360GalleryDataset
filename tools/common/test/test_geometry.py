import adsk.core
import adsk.fusion
import importlib
import unittest
import os
import sys
from pathlib import Path

from .common_test_base import CommonTestBase

# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

import geometry
importlib.reload(geometry)


class TestGeometry(CommonTestBase):

    def __init__(self):
        CommonTestBase.__init__(self)
        unittest.TestCase.__init__(self)
        # The number of decimal places for testing equality
        self.places = 4

    def run(self):
        # self.test_get_union_volume_overlap()
        # self.test_get_union_volume_overlap_double()
        # self.test_get_union_volume_overlap_3way()
        # self.test_get_union_volume_adjacent()
        # self.test_get_union_volume_separate()
        # self.test_get_intersect_volume_overlap()
        # self.test_get_intersect_volume_overlap_double()
        self.test_get_intersect_volume_overlap_3way()
        # self.test_get_intersect_volume_adjacent()
        # self.test_get_intersect_volume_separate()

    def load_f3d(self, file):
        self.clear()
        existing_document = self.app.activeDocument
        options = self.app.importManager.createFusionArchiveImportOptions(
            str(file.resolve())
        )
        self.app.importManager.importToNewDocument(options)
        existing_document.close(False)
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        # # We need direct design to do some boolean operations
        # self.design.designType = adsk.fusion.DesignTypes.DirectDesignType

    def get_component_bodies(self, component):
        bodies = adsk.core.ObjectCollection.create()
        for body in component.bRepBodies:
            bodies.add(body)
        return bodies

    def test_get_union_volume_overlap(self):
        f3d = self.testdata_dir / "common/BooleanOverlap.f3d"
        self.load_f3d(f3d)
        bodies = self.get_component_bodies(self.design.rootComponent)
        volume = geometry.get_union_volume(bodies)
        self.assertAlmostEqual(volume, 3, places=self.places)

    def test_get_union_volume_overlap_double(self):
        f3d = self.testdata_dir / "common/BooleanOverlapDouble.f3d"
        self.load_f3d(f3d)
        bodies = self.get_component_bodies(self.design.rootComponent)
        volume = geometry.get_union_volume(bodies)
        self.assertAlmostEqual(volume, 6, places=self.places)

    def test_get_union_volume_overlap_3way(self):
        f3d = self.testdata_dir / "common/BooleanOverlap3Way.f3d"
        self.load_f3d(f3d)
        bodies = self.get_component_bodies(self.design.rootComponent)
        volume = geometry.get_union_volume(bodies)
        self.assertAlmostEqual(volume, 4, places=self.places)

    def test_get_union_volume_adjacent(self):
        f3d = self.testdata_dir / "common/BooleanAdjacent.f3d"
        self.load_f3d(f3d)
        bodies = self.get_component_bodies(self.design.rootComponent)
        volume = geometry.get_union_volume(bodies)
        self.assertAlmostEqual(volume, 2, places=self.places)

    def test_get_union_volume_separate(self):
        f3d = self.testdata_dir / "common/BooleanSeparate.f3d"
        self.load_f3d(f3d)
        bodies = self.get_component_bodies(self.design.rootComponent)
        volume = geometry.get_union_volume(bodies)
        self.assertAlmostEqual(volume, 2, places=self.places)
    
    def test_get_intersect_volume_overlap(self):
        f3d = self.testdata_dir / "common/BooleanOverlap.f3d"
        self.load_f3d(f3d)
        bodies = self.get_component_bodies(self.design.rootComponent)
        volume = geometry.get_intersect_volume(bodies)
        self.assertAlmostEqual(volume, 1, places=self.places)

    def test_get_intersect_volume_overlap_double(self):
        f3d = self.testdata_dir / "common/BooleanOverlapDouble.f3d"
        self.load_f3d(f3d)
        bodies = self.get_component_bodies(self.design.rootComponent)
        volume = geometry.get_intersect_volume(bodies)
        self.assertAlmostEqual(volume, 2, places=self.places)

    def test_get_intersect_volume_overlap_3way(self):
        f3d = self.testdata_dir / "common/BooleanOverlap3Way.f3d"
        self.load_f3d(f3d)
        bodies = self.get_component_bodies(self.design.rootComponent)
        volume = geometry.get_intersect_volume(bodies)
        self.assertAlmostEqual(volume, 1, places=self.places)
    
    def test_get_intersect_volume_adjacent(self):
        f3d = self.testdata_dir / "common/BooleanAdjacent.f3d"
        self.load_f3d(f3d)
        bodies = self.get_component_bodies(self.design.rootComponent)
        volume = geometry.get_intersect_volume(bodies)
        self.assertAlmostEqual(volume, 0, places=self.places)

    def test_get_intersect_volume_separate(self):
        f3d = self.testdata_dir / "common/BooleanSeparate.f3d"
        self.load_f3d(f3d)
        bodies = self.get_component_bodies(self.design.rootComponent)
        volume = geometry.get_intersect_volume(bodies)
        self.assertAlmostEqual(volume, 0, places=self.places)