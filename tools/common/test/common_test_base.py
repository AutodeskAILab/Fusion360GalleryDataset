
import adsk.core
import adsk.fusion
import unittest
import os
import sys
from pathlib import Path


class CommonTestBase(unittest.TestCase):

    def __init__(self):
        unittest.TestCase.__init__(self)
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.current_dir = Path(os.path.join(os.path.dirname(__file__)))
        self.testdata_dir = self.current_dir.parent.parent / "testdata"

    def clear(self):
        """Clear everything by closing all documents"""
        for doc in self.app.documents:
            # Save without closing
            doc.close(False)
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
