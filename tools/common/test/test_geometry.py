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
        self.boolean_f3d = self.testdata_dir / "common/Boolean3Body.f3d"

    def run(self):
        self.test_get_union_volume()

    def load_boolean_f3d(self):
        self.clear()
        options = self.app.importManager.createFusionArchiveImportOptions(
            str(self.boolean_f3d.resolve())
        )
        self.app.importManager.importToNewDocument(options)

    def test_get_union_volume(self):
        self.load_boolean_f3d()
        bodies = []
        for body in self.design.rootComponent.bRepBodies:
            bodies.append(body)
        volume = geometry.get_union_volume(bodies)
        print(volume)
