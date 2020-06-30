# path to your FreeCAD.so or FreeCAD.dll file
# make sure to run the python compatible with FreeCAD

FREECAD_LIB_PATH = '/Applications/FreeCAD.app/Contents/Resources/lib'  
import sys
sys.path.append(FREECAD_LIB_PATH)#<-- added, otherwise FreeCAD is not found

import FreeCAD
import Part
from FreeCAD import Base

V1 = Base.Vector(0, 10, 0)
V2 = Base.Vector(30, 10, 0)
V3 = Base.Vector(30, -10, 0)
V4 = Base.Vector(0, -10, 0)

VC1 = Base.Vector(-10, 0, 0)
C1 = Part.Arc(V1, VC1, V4)
VC2 = Base.Vector(40, 0, 0)
C2 = Part.Arc(V2, VC2, V3)

L1 = Part.LineSegment(V1, V2)
L2 = Part.LineSegment(V3, V4)

S1 = Part.Shape([C1, L1, C2, L2])

W = Part.Wire(S1.Edges)
disc = Part.Face(W)  # this step adds a cap for the extrusion

P = disc.extrude(Base.Vector(0, 0, 10))

sphere = Part.makeSphere(12, Base.Vector(5, 0, 10))
diff = P.cut(sphere)

print(f'Area: {diff.Area}')
print(f'BoundBox: {diff.BoundBox}')
print(f'Edges: {len(diff.Edges)}')
print(f'Faces: {len(diff.Faces)}')
print(f'Length: {diff.Length}')
print(f'Matrix: {diff.Matrix}')
print(f'Orientation: {diff.Orientation}')
print(f'Placement: {diff.Placement}')
print(f'ShapeType: {diff.ShapeType}')
print(f'Shells: {len(diff.Shells)}')
print(f'Solids: {len(diff.Solids)}')
print(f'Vertexes: {len(diff.Vertexes)}')
print(f'Volume: {diff.Volume}')
print(f'Orientation: {diff.Orientation}')

diff.exportStep("test.stp")
