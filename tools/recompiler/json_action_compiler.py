import traceback
import json
import os
import sys
import time
import math
from pathlib import Path

from importlib import reload
import geo_utils

# import utils


class JsonActionCompiler():
    def __init__(self, json_data):

        if isinstance(json_data, dict):
            self.data = json_data
        else:
            with open(json_data, encoding="utf8") as f:
                self.data = json.load(f)
        
        # if a new body is added
        self.initiated = False
        self.construction_tree = {}
        self.json = json_data

    def parse(self, callback=None):

        # record all profiles used for extrusion
        self.record_extrusion_profiles()
        # record all sketches used in the model
        self.record_sketches()

        # sort the profile loops by in and out
        self.record_profile_loops()

        self.build_construction_tree()
        self.traverse_construction_tree(self.construction_tree)
        self.saveDataAsJson(self.json, self.construction_tree)
    
    def pprint(self, js_input):
        json_formatted_str = json.dumps(js_input, indent=2)
        print(json_formatted_str)
    
    def record_sketches(self):
        self.sketches = {}

        for timeline_object in self.data["timeline"]:
            entity_uuid = timeline_object["entity"]
            entity = self.data["entities"][entity_uuid]
            t_index = timeline_object["index"]  # the index on the timeline

            # extrusion
            if entity["type"] == "Sketch":

                self.sketches[entity_uuid] = {}

                transform = geo_utils.transform_print(entity["transform"])
                ref = None

                if entity["reference_plane"]['type'] == "ConstructionPlane":
                    ref = entity["reference_plane"]['name']
                elif entity["reference_plane"]['type'] == "BRepFace":
                    ref = entity["reference_plane"]['point_on_face']

                self.sketches[entity_uuid]['transform'] = transform
                self.sketches[entity_uuid]['ref'] = ref
                self.sketches[entity_uuid]['t_index'] = t_index

    def record_extrusion_profiles(self):
        self.extrusion_profiles = {}
        extrusion_index = 0

        for timeline_object in self.data["timeline"]:
            entity_uuid = timeline_object["entity"]
            entity = self.data["entities"][entity_uuid]

            # extrusion
            if entity["type"] == "ExtrudeFeature":
                entity['extrusion_index'] = extrusion_index
                extrusion_index += 1

                profile_ids = entity["profiles"]
                profile_ids = [pr["profile"] for pr in profile_ids]

                # each profile might be applied for multiple extrusions
                for ind in profile_ids:
                    if ind not in self.extrusion_profiles:
                        self.extrusion_profiles[ind] = []

                    # record the extrusion that uses this profile
                    self.extrusion_profiles[ind].append(entity["name"])

    def record_profile_loops(self):

        self.profiles = {}

        for timeline_object in self.data["timeline"]:
            entity_uuid = timeline_object["entity"]
            entity = self.data["entities"][entity_uuid]
            t_index = timeline_object["index"]  # the index on the timeline

            if entity["type"] == "Sketch":
                profiles = entity["profiles"]

                for profile_id in profiles:
                    if profile_id in self.extrusion_profiles:

                        # record outside loops and inside loops for each profile
                        if profile_id not in self.profiles:
                            self.profiles[profile_id] = {
                                'out': [],
                                'in': [],
                                'transform': entity['transform'],
                                't_index': t_index
                            }
                                                
                        for loop in profiles[profile_id]['loops']:
                            if loop['is_outer']:
                                self.profiles[profile_id]['out'].append(loop['profile_curves'])
                            else:
                                self.profiles[profile_id]['in'].append(loop['profile_curves'])

    def build_construction_tree(self):

        # traverse timeline in reverse order
        # the next operation always operates on the previous geometry
        # put them in pairs in the tree structure

        self.construction_tree['made_of'] = {}
        current_branch = self.construction_tree['made_of']
        # t_total = len(self.data["timeline"])

        for i, timeline_object in enumerate(self.data["timeline"][::-1]):
            entity_uuid = timeline_object["entity"]
            entity = self.data["entities"][entity_uuid]

            # extrusion
            if entity["type"] == "ExtrudeFeature":
                name = entity['name']
                main_operation = entity['operation']

                current_branch["geometry"] = {
                    'name': name,
                    'type': 'body',
                    'operation': main_operation,
                    'uuid': entity_uuid,
                    'apply_to': {},
                    'made_of': {},
                    # 't_index': (t_total-i)
                }

                current_branch = current_branch["geometry"]['apply_to']
                pass
        
        self.build_branch()

    def traverse_construction_tree(self, tree):
        # # lines = self.get_type_in_tree(self.construction_tree, 'Line3D', [])
        sketches = self.get_type_in_tree(self.construction_tree, 'sketch', [])

        message = {}

        # print('lines', lines)

        for sketch in sketches:
            t = sketch['t_index']

            if(t not in message):
                message[t] = {}

            if('sketch' not in message[t]):
                message[t]['sketch'] = ""

            sketch_info = {
                'name': sketch['name'],
                'transform': sketch['transform'],
                'ref': sketch['ref'],
                't': t
            }


            # print(f"Start Sketch: {sketch_info}")
            message[t]['sketch'] += f"Start Sketch: {sketch_info}\n"

            curves = sketch['made_of']['stroke_list']

            for id in curves:
                curve = curves[id]
                start = [curve['start']['x'], curve['start']['y'], curve['start']['z']]
                end = [curve['end']['x'], curve['end']['y'], curve['end']['z']]

                curve_info = {
                    'start': start,
                    'end': end
                }

                # print(f"Add {curve['type']}: {curve_info}")
                message[t]['sketch'] += f"Add {curve['type']}: {curve_info}\n"

            # print(f"End Sketch")
            message[t]['sketch'] += f"End Sketch\n"
            message[t]['sketch'] += f"\n"


        bodies = self.get_type_in_tree(self.construction_tree, 'body', [])
        bodies.reverse()

        for body in bodies:



            name = body['name']
            operation = body['operation']

            made_of = body['made_of']['geometry']['name']
            made_of_type = body['made_of']['geometry']['type']
            apply_to = ''
            if 'geometry' in body['apply_to']:
                apply_to = body['apply_to']['geometry']['name']
            
            t = -1
            if('t_index' in body):
                t = body['t_index'] + 1  # extrusion adds one by default

            if(t not in message):
                message[t] = {}

            if('body' not in message[t]):
                message[t]['body'] = ""

            body_info = {
                'name': name,
                'operation': operation,
                'made_of': made_of,
                'apply_to': apply_to,
                't': t
            }

            if made_of_type == 'sketch':
                body_info['distance'] = body['distance']

            # print(f"Add body: {body_info}")
            message[t]['body'] += f"Add body: {body_info}\n"
            message[t]['body'] += f"\n"

        # print(f"Finishing body: {self.construction_tree['made_of']['geometry']['name']}")
        message[t]['body'] += f"Finishing body: {self.construction_tree['made_of']['geometry']['name']}\n"

        # message is indexed by time
        message_ts = list(message.keys())
        message_ts = [t if t >= 0 else len(message_ts)-1 for t in message_ts]

        message_ts.sort()

        for t in message_ts:
            # print('t', t)
            if(t in message):
                if('sketch' in message[t]):
                    print(message[t]['sketch'], end='')
                if('body' in message[t]):
                    print(message[t]['body'], end='')
            else:
                if('sketch' in message[-1]):
                    print(message[-1]['sketch'], end='')
                if('body' in message[-1]):
                    print(message[-1]['body'], end='')





    def get_branch(self, tree, name):
        # get branch by uuid or name

        for branch in tree:
            if branch == 'name' and tree[branch] == name:
                return tree
            elif branch == 'uuid' and tree[branch] == name:
                return tree
            elif branch == 'made_of' \
                or branch == 'apply_to' \
                    or branch == 'geometry'\
                        or branch == 'stroke_list'\
                            or branch == 'strokes':
                return self.get_branch(tree[branch], name)
            else:
                pass

    def get_type_in_tree(self, tree, item_type, lst=[]):
        # get all branches as a flatten list that matches the given type

        for branch in tree:

            if isinstance(tree[branch], dict):

                if 'type' in tree[branch] and tree[branch]['type'] == item_type:
                    lst.append(tree[branch])

                lst = (self.get_type_in_tree(tree[branch], item_type, lst))

        return lst

    def curves_to_sequence(self, profile_curves, transform):
        for profile_curve in (profile_curves):

            curve_type = profile_curve['type']
            start = geo_utils.transform_pt(profile_curve['start_point'], transform)
            end = geo_utils.transform_pt(profile_curve['end_point'], transform)

            print(f"{curve_type} from {start} to {end}")

    def build_branch(self):
        # traverse timeline
        for timeline_object in (self.data["timeline"]):
            entity_uuid = timeline_object["entity"]
            entity = self.data["entities"][entity_uuid]

            # extrusion
            if entity["type"] == "ExtrudeFeature":
                name = entity['name']
                distance = entity['extent_one']['distance']['value']

                # get the branch in the construction tree
                current_branch = self.get_branch(self.construction_tree, name)
                current_branch['made_of']['geometry'] = {}
                current_branch = current_branch['made_of']
                
                profiles = entity['profiles']

                # print('profiles', profiles)
                # profiles = [pr['profile'] for pr in profiles]

                # each extrusion might link to multiple profile loops
                # we split them as seperate extrusions
                for pr in profiles:
                    profile_id = pr['profile']
                    sketch_id = pr['sketch']

                    out_loops = self.profiles[profile_id]['out']
                    in_loops = self.profiles[profile_id]['in']
                    transform = geo_utils.transform_print(self.profiles[profile_id]['transform'])
                    ref = self.sketches[sketch_id]['ref']  # ref-plane pointer
                    t_index = self.sketches[sketch_id]['t_index']

                    # each loop creates a new extrusion
                    # inner loops apply cutting
                    for i, lp in enumerate(in_loops):
                        # if main_operation == "NewBodyFeatureOperation"\
                        #     or main_operation == "JoinFeatureOperation"\
                        #         or main_operation == "IntersectFeatureOperation":
                        #     operation = "CutFeatureOperation"

                        # else:
                        #     operation = "NewBodyFeatureOperation"
                        
                        # self.curves_to_sequence(lp, transform)
                        lp_name = f"{name}_inlp_{i}"

                        made_of_data = {
                            'geometry': {
                                'name': f"{lp_name}_sketch",
                                'type': 'sketch',
                                'ref': ref,
                                'transform': transform,
                                'parent': lp_name,
                                'made_of': {
                                    'strokes': self.get_strokes_data(lp_name, lp)
                                },
                                't_index': t_index,
                            }
                        }

                        current_branch['geometry'] = {
                            'name': lp_name,
                            'type': 'body',
                            'operation': "CutFeatureOperation",
                            'distance': distance,
                            'apply_to': {},
                            'made_of': made_of_data,
                            't_index': t_index,

                        }

                        current_branch = current_branch["geometry"]['apply_to']

                    # outer loops creates new solid
                    for i, lp in enumerate(out_loops):
                        # if not self.initiated:
                        #     operation = "NewBodyFeatureOperation"
                        #     self.initiated = True

                        lp_name = f"{name}_outlp_{i}"

                        made_of_data = {
                            'geometry': {
                                'name': f"{lp_name}_sketch",
                                'type': 'sketch',
                                'ref': ref,
                                'transform': transform,
                                'parent': lp_name,
                                'made_of': {
                                    'stroke_list': self.get_strokes_data(lp_name, lp)
                                },
                                't_index': t_index,
                            }
                        }

                        current_branch['geometry'] = {
                            'name': lp_name,
                            'type': 'body',
                            'operation': "NewBodyFeatureOperation",
                            'distance': distance,
                            'apply_to': {},
                            'made_of': made_of_data,
                            't_index': t_index,

                        }

                        current_branch = current_branch["geometry"]['apply_to']

    def get_strokes_data(self, lp_name, profile_curves):

        out = {}

        for i, profile_curve in enumerate(profile_curves):

            curve_type = profile_curve['type']
            start = profile_curve['start_point']
            end = profile_curve['end_point']

            out[str(i)] = {
                'start': start,
                'end': end,
                'type': curve_type,
                'parent': f"{lp_name}_strokes"
            }

        return out

    def saveDataAsJson(self, path, data):

        json_file = path.parent / f"{path.stem}_tree.txt"

        with open(str(json_file.resolve()), 'w') as fileToSave:
            json.dump(data, fileToSave, ensure_ascii=True, indent=4, sort_keys=True)

            print(f"Data saved to {json_file}")

