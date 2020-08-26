import adsk.core
import adsk.fusion
import importlib
import unittest
import os
import sys
from pathlib import Path
import time

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
        self.test_get_union_volume_overlap()
        self.test_get_union_volume_overlap_double()
        self.test_get_union_volume_overlap_3way()
        self.test_get_union_volume_adjacent()
        self.test_get_union_volume_separate()
        self.test_get_union_volume_overlap_component()
        self.test_get_intersect_volume_overlap()
        self.test_get_intersect_volume_overlap_self_intersect()


    def load_f3d(self, file):
        self.clear()
        existing_document = self.app.activeDocument
        options = self.app.importManager.createFusionArchiveImportOptions(
            str(file.resolve())
        )
        self.app.importManager.importToNewDocument(options)
        existing_document.close(False)
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)

    def get_component_bodies(self, component):
        bodies = adsk.core.ObjectCollection.create()
        for body in component.bRepBodies:
            bodies.add(body)
        return bodies
    
    def get_component(self, name):
        # named_comp = None
        # for comp in self.design.allComponents:
        #     if comp.name == name:
        #         named_comp = comp
        #         break
        named_comp = self.design.allComponents.itemByName(name)
        assert named_comp is not None
        return named_comp

    # -------------------------------------------------------------------------
    # UNION
    # -------------------------------------------------------------------------

    def test_get_union_volume_overlap(self):
        f3d = self.testdata_dir / "common/BooleanOverlap.f3d"
        self.load_f3d(f3d)
        volume = geometry.get_union_volume(self.design.rootComponent.bRepBodies)
        self.assertAlmostEqual(volume, 3, places=self.places)

    def test_get_union_volume_overlap_double(self):
        f3d = self.testdata_dir / "common/BooleanOverlapDouble.f3d"
        self.load_f3d(f3d)
        volume = geometry.get_union_volume(self.design.rootComponent.bRepBodies)
        self.assertAlmostEqual(volume, 6, places=self.places)

    def test_get_union_volume_overlap_3way(self):
        f3d = self.testdata_dir / "common/BooleanOverlap3Way.f3d"
        self.load_f3d(f3d)
        volume = geometry.get_union_volume(self.design.rootComponent.bRepBodies)
        self.assertAlmostEqual(volume, 4, places=self.places)

    def test_get_union_volume_adjacent(self):
        f3d = self.testdata_dir / "common/BooleanAdjacent.f3d"
        self.load_f3d(f3d)
        volume = geometry.get_union_volume(self.design.rootComponent.bRepBodies)
        self.assertAlmostEqual(volume, 2, places=self.places)

    def test_get_union_volume_separate(self):
        f3d = self.testdata_dir / "common/BooleanSeparate.f3d"
        self.load_f3d(f3d)
        volume = geometry.get_union_volume(self.design.rootComponent.bRepBodies)
        self.assertAlmostEqual(volume, 2, places=self.places)
    
    def test_get_union_volume_overlap_component(self):
        f3d = self.testdata_dir / "common/BooleanIntersectOverlap.f3d"
        self.load_f3d(f3d)
        tool_comp = self.get_component("Tool")
        bodies = []
        for body in self.design.rootComponent.bRepBodies:
            bodies.append(body)
        for body in tool_comp.bRepBodies:
            bodies.append(body)
        volume = geometry.get_union_volume(bodies)
        self.assertAlmostEqual(volume, 3, places=self.places)
    
    # -------------------------------------------------------------------------
    # INTERSECT
    # -------------------------------------------------------------------------

    def test_get_intersect_volume_overlap(self):
        f3d = self.testdata_dir / "common/BooleanIntersectOverlap.f3d"
        self.load_f3d(f3d)
        tool_comp = self.get_component("Tool")
        volume = geometry.get_intersect_volume(
            self.design.rootComponent.bRepBodies,
            tool_comp.bRepBodies
        )
        self.assertAlmostEqual(volume, 1, places=self.places)

    def test_get_intersect_volume_overlap_self_intersect(self):
        f3d = self.testdata_dir / "common/BooleanIntersectOverlapSelfIntersect.f3d"
        self.load_f3d(f3d)
        tool_comp = self.get_component("Tool")
        volume = geometry.get_intersect_volume(
            self.design.rootComponent.bRepBodies,
            tool_comp.bRepBodies
        )
        self.assertAlmostEqual(volume, 1, places=self.places)
