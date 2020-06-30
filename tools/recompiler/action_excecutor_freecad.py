"""

Load actions sequence data and reconstructs the geometry in Fusion

"""


import traceback
import json
import os
import sys
import time
import math
from pathlib import Path

from importlib import reload

# add freecad lib folder
# path to FreeCAD.so or FreeCAD.dll file
# make sure to run the python compatible with FreeCAD (used for FreeCAD build)

FREECAD_LIB_PATH = '/Applications/FreeCAD.app/Contents/Resources/lib'  
if FREECAD_LIB_PATH not in sys.path:
    sys.path.append(FREECAD_LIB_PATH)#<-- added, otherwise FreeCAD is not found

import FreeCAD
import Part
from FreeCAD import Base
import numpy as np

class ActionExcecutorFreeCAD():
    def __init__(self, actions, callBack = None):

        if isinstance(actions, list):
            self.actions = actions
        else:
            with open(actions, encoding="utf8") as f:
                self.actions = json.load(f)
    
        self.callback = callBack

    def traverse_actions(self):
        sketch_transformation = {}  # store the sketch transformation
        sketch_stroke = {}  # store the sketch name to stroke list map
        sketch_shape = {}  # store the sketch name to shape map
        solids = {}  # store the solids created by extrusion
        
        for action in self.actions:

            if(action['command'] == "add_sketch"):
                name = action['info']['name']

                T = self.transform_to_mat(action['info']['transform'])
                sketch_transformation[name] = T

                sketch_stroke[name] = []

            if(action['command'] == "add_line"):
                # TODO: add other type supports

                sketch_name = action['info']['sketch']
                myMat = sketch_transformation[sketch_name]

                start_point = action['info']['start']
                end_point = action['info']['end']

                V1_ = Base.Vector(start_point[0], start_point[1], start_point[2])
                V2_ = Base.Vector(end_point[0], end_point[1], end_point[2])
                L = Part.LineSegment(V1_, V2_)

                sketch_stroke[sketch_name].append(L)
            
            if(action['command'] == "close_profile"):
                S1 = Part.Shape(sketch_stroke[sketch_name])
                W = Part.Wire(S1.Edges)
                disc = Part.Face(W)  # this step adds a face to the wire

                sketch_shape[action['info']] = disc

            if(action['command'] == "add_extrude"):
                name = action['info']['name']
                made_of = action['info']['made_of']
                distance = action['info']['distance']
                apply_to =  action['info']['apply_to']
                operation = action['info']['operation']

                # when made_of is a sketch, extrude sketch and apply its transformation 
                if('sketch' in made_of):
                    # print('action', action)

                    body = sketch_shape[made_of].extrude(Base.Vector(0, 0, distance))
                    myMat = sketch_transformation[made_of]

                    body.transformShape(myMat)
                
                else:
                    body = solids[made_of]
                
                if(len(apply_to) > 0):

                    if(operation == 'CutFeatureOperation'):
                        body = solids[apply_to].cut(body)
                    
                    if(operation == 'JoinFeatureOperation'):
                        body = solids[apply_to].fuse(body)

                    # TODO: other operations like intersection

                solids[name] = body
            
            if(action['command'] == "Finish"):
                if(self.callback):
                    self.callback()
                
                self.final_solid = solids[action['info']]
                self.final_solid.exportBrep("test_constructor.brep")

                print(f'{self.final_solid} saved to test_constructor.brep')
                
    def tester(self, json_data):
        """json_data is the original exported json model data"""

        if isinstance(json_data, dict):
            self.data = json_data
        else:
            with open(json_data, encoding="utf8") as f:
                self.data = json.load(f)
        
        properties = self.data['properties']

        print('properties', properties)

    def transform_to_mat(self, transform):
        # the transformation matrix to convert from sketch space to world space

        T = (transform['x_axis']['x'], transform['x_axis']['y'], transform['x_axis']['z'], 0,
            transform['y_axis']['x'], transform['y_axis']['y'], transform['y_axis']['z'], 0,
            transform['z_axis']['x'], transform['z_axis']['y'], transform['z_axis']['z'], 0,
            0, 0, 0, 1)

        T = Base.Matrix(*T)

        T.invert()

        T.move(Base.Vector(transform['origin']['x'], transform['origin']['y'], transform['origin']['z']))
        
        return T
