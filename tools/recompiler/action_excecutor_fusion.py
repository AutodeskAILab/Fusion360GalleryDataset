"""

Load actions sequence data and reconstructs the geometry in Fusion

TODO: support more sketch data, now only supports Line3D
TODO: currently the correction matrix calculation is included in the reconstruction process, 
    will be swapped if it is pre-calculated

"""


import traceback
import json
import os
import sys
import time
import math
from pathlib import Path
import adsk.core
import adsk.fusion

from importlib import reload

# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common"))
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

# Add the server folder to sys.path
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fusion360gym", "server"))
if SERVER_DIR not in sys.path:
    sys.path.append(SERVER_DIR)

from command_runner import CommandRunner

import deserialize
import serialize
import data_util



class ActionExcecutorFusion():
    def __init__(self, actions, callBack = None):

        if isinstance(actions, list):
            self.actions = actions
        else:
            with open(actions, encoding="utf8") as f:
                self.actions = json.load(f)
    
        self.app = adsk.core.Application.get()
        product = self.app.activeProduct
        self.design = adsk.fusion.Design.cast(product)

        self.callback = callBack

    def traverse_actions(self):
        c_runner = CommandRunner()
        name_mapper = {}  # store the data name to fusion name map

        for action in self.actions:

            if(action['command'] == "add_sketch"):

                name = action['info']['name']

                sketch_plane = None
                if 'name' in action['info']['ref']:
                    sketch_plane = action['info']['ref']['name']
                elif 'point_on_face' in action['info']['ref']:
                    sketch_plane = action['info']['ref']['point_on_face']

                d = {
                    'sketch_plane': sketch_plane
                }
                r = c_runner.run_command('add_sketch', d)
                name_mapper[name] = r[2]

                # calculate correction_matrix
                self.find_correction_matrix(action, name_mapper)

            if(action['command'] == "add_line"):
                # print(action)


                start_point = action['info']['start']
                end_point = action['info']['end']

                # apply correction matrix
                correction = name_mapper[action['info']['sketch']]['correction_matrix']
                start_point = deserialize.point3d(start_point)
                end_point = deserialize.point3d(end_point)
                start_point.transformBy(correction)
                end_point.transformBy(correction)
                start_point = serialize.point3d(start_point)
                end_point = serialize.point3d(end_point)

                d = {
                    'sketch_name': name_mapper[action['info']['sketch']]['sketch_name'],
                    'pt1': start_point,
                    'pt2': end_point
                }
                r = c_runner.run_command('add_line', d)

                profiles = list(r[2]['profiles'].keys())

                # we only create single loop sketches
                if len(profiles):
                    name_mapper[action['info']['sketch']]['profile'] = profiles[0]
                # print('line info', r)
            
            if(action['command'] == "add_extrude"):
                # print(action)
                # print('name_mapper', name_mapper)

                d = {
                    'sketch_name': name_mapper[action['info']['made_of']]['sketch_name'],
                    'distance': action['info']['distance'],
                    'profile_id': name_mapper[action['info']['made_of']]['profile'],
                    'operation': action['info']['operation']
                }

                r = c_runner.run_command('add_extrude', d)
            
            if(action['command'] == "Finish"):
                if(self.callback):
                    self.callback()


            

        # Close the document - Fusion automatically opens a new window after the last one is closed
        # self.app.activeDocument.close(False)

    def tester(self, json_data):
        """json_data is the original exported json model data"""

        if isinstance(json_data, dict):
            self.data = json_data
        else:
            with open(json_data, encoding="utf8") as f:
                self.data = json.load(f)
        
        properties = self.data['properties']

        print(f'Original Properties: {properties}')



        bodies = []
        for component in self.design.allComponents:
            for body in component.bRepBodies:
                bodies.append(body)

        print(f'Reconstruction Properties: {data_util.get_properties(bodies[0])}')



    def find_correction_matrix(self, action, name_mapper):

        name = action['info']['name']

        sketch_data = {
            'ref': action['info']['ref'],
            'transform': action['info']['transform']
        }

        sketches = self.design.rootComponent.sketches
        # Find the right sketch plane to use
        sketch_plane = self.get_sketch_plane(sketch_data["ref"])
        sketch = sketches.addWithoutEdges(sketch_plane)

        # Create an identity matrix
        transform_for_sketch_geom = adsk.core.Matrix3D.create()
        # We will need to apply some other transform to the sketch data
        sketch_transform = sketch.transform
        transform_for_sketch_geom = self.find_transform_for_sketch_geom(sketch_transform, sketch_data["transform"])

        name_mapper[name]['correction_matrix'] = transform_for_sketch_geom

    def get_sketch_plane(self, reference_plane):
        # ConstructionPlane as reference plane
        if reference_plane["type"] == "ConstructionPlane" and "name" in reference_plane:
            sketch_plane = deserialize.construction_plane(reference_plane["name"])
            if sketch_plane is not None:
                return sketch_plane
        # BRepFace as reference plane
        elif reference_plane["type"] == "BRepFace" and "point_on_face" in reference_plane:
            face = deserialize.face_by_point3d(reference_plane["point_on_face"])
            if face is not None:
                if face.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                    return face
                else:
                    print(f"Sketch plane (BRepFace) - invalid surface type {face.geometry.surfaceType}")
            else:
                print("Sketch plane point on face not found!")

        return self.design.rootComponent.xYConstructionPlane


    def find_transform_for_sketch_geom(self, sketch_transform, original_transform_json):
        # The sketch transform operates on a sketch point p_sketch and transforms it into
        # world space (or at least the space of the assembly context)
        #
        # p_world = T * p_sketch
        #
        # Now we need to cope with the sketch plane having two different transforms when we
        # extract and when we import it.
        #
        # We know the one thing which stays constant is the final point in world space, so
        # we have
        #
        # p_world = T_extract * p_sketch = T_import * T_correction * p_sketch
        #
        # hence
        #
        # T_extract = T_import * T_correction
        #
        # Now premultiplying both sides by T_import^-1 gives us
        #
        # T_correction = T_import^-1  * T_extract
        #
        # This function need to compute T_correction

        # sketch_transform is T_import.    Here we find T_import^-1
        ok = sketch_transform.invert()
        assert ok

        # Set xform = T_extract
        xform = deserialize.matrix3d(original_transform_json)

        # The transformBy() function must be "premultiply"
        # so here we have
        # xform = T_import^-1  * T_extract
        xform.transformBy(sketch_transform)
        return xform