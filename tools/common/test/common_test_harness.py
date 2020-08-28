"""

Common Test Harness

"""
import adsk.core
import adsk.fusion
import traceback

from .test_geometry import TestGeometry


def run(context):

    try:

        test_geometry = TestGeometry()
        test_geometry.run()

    except:
        print(traceback.format_exc())
