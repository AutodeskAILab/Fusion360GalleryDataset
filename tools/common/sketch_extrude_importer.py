"""

Import and reconstruction of sketch and extrude designs
from the Reconstruction Dataset

"""

import adsk.core
import adsk.fusion
import traceback
import json
import os
import sys
import time
import math
from pathlib import Path
from collections import OrderedDict

import deserialize


class SketchExtrudeImporter():
    def __init__(self, json_data=None):
        self.app = adsk.core.Application.get()
        if json_data is not None:
            if isinstance(json_data, dict):
                self.data = json_data
            else:
                with open(json_data, encoding="utf8") as f:
                    self.data = json.load(f, object_pairs_hook=OrderedDict)

        product = self.app.activeProduct
        self.design = adsk.fusion.Design.cast(product)
        # Callback during reconstruction
        # called incrementally when the design changs
        self.reconstruct_cb = None

    # --------------------------------------------------------
    # PUBLIC API CALLS
    # --------------------------------------------------------

    def reconstruct(self, reconstruct_cb=None, reconstruction=None):
        """Reconstruct the full design"""
        self.reconstruct_cb = reconstruct_cb
        self.reconstruction = reconstruction
        if self.reconstruction is None:
            self.reconstruction = self.design.rootComponent
        timeline = self.data["timeline"]
        entities = self.data["entities"]
        # Get the profiles used in this design
        profiles_used = self.get_extrude_profiles(timeline, entities)

        # Keep track of the sketch profiles
        sketch_profiles = {}
        for timeline_object in timeline:
            entity_uuid = timeline_object["entity"]
            entity_index = timeline_object["index"]
            entity = entities[entity_uuid]
            if entity["type"] == "Sketch":
                # Only reconstruct this sketch if it is used with an extrude
                if entity_uuid in profiles_used["sketches"]:
                    sketch, sketch_profile_set = self.reconstruct_sketch_feature(
                        entity, sketch_profiles,
                        sketch_uuid=entity_uuid, sketch_index=entity_index
                    )
                    if sketch_profile_set:
                        sketch_profiles.update(**sketch_profile_set)

            elif entity["type"] == "ExtrudeFeature":
                self.reconstruct_extrude_feature(entity, entity_uuid, entity_index, sketch_profiles)

    def reconstruct_sketch(self, sketch_data, sketch_uuid=None,
                           sketch_index=None, sketch_plane=None,
                           transform=None, reconstruct_cb=None,
                           reconstruction=None):
        """Reconstruct and return just a single sketch"""
        self.reconstruct_cb = reconstruct_cb
        self.reconstruction = reconstruction
        if self.reconstruction is None:
            self.reconstruction = self.design.rootComponent
        sketch, sketch_profile_set = self.reconstruct_sketch_feature(
            sketch_data, {},
            sketch_uuid=sketch_uuid, sketch_index=sketch_index,
            sketch_plane=sketch_plane, transform=transform
        )
        return sketch

    def reconstruct_profile(self, sketch_data, sketch_name, profile_uuid,
                            transform=None, reconstruct_cb=None,
                            reconstruction=None):
        """Reconstruct a single profile from a given sketch"""
        self.reconstruct_cb = reconstruct_cb
        self.reconstruction = reconstruction
        if self.reconstruction is None:
            self.reconstruction = self.design.rootComponent
        profile_data = sketch_data["profiles"][profile_uuid]
        sketches = self.reconstruction.sketches
        sketch = sketches.itemByName(sketch_name)
        if transform is None:
            transform = adsk.core.Matrix3D.create()
        self.reconstruct_trimmed_curves(sketch, profile_data, transform)
        return sketch

    def reconstruct_curve(self, sketch_data, sketch_name, curve_uuid,
                          sketch_uuid=None, sketch_index=None,
                          transform=None, reconstruct_cb=None,
                          reconstruction=None):
        """Reconstruct a single curve in a given sketch"""
        self.reconstruct_cb = reconstruct_cb
        self.reconstruction = reconstruction
        if self.reconstruction is None:
            self.reconstruction = self.design.rootComponent

        curve_data = sketch_data["curves"][curve_uuid]
        points_data = sketch_data["points"]
        sketches = self.reconstruction.sketches
        sketch = sketches.itemByName(sketch_name)
        if transform is None:
            transform = adsk.core.Matrix3D.create()
        self.reconstruct_sketch_curve(
            sketch,
            curve_data,
            curve_uuid,
            points_data,
            transform=transform,
            sketch_uuid=sketch_uuid,
            sketch_index=sketch_index
        )
        adsk.doEvents()
        return sketch

    def reconstruct_curves(self, sketch_data, sketch_name,
                          sketch_uuid=None, sketch_index=None,
                          transform=None, reconstruct_cb=None,
                          reconstruction=None):
        """Reconstruct all curves in a given sketch"""
        self.reconstruct_cb = reconstruct_cb
        self.reconstruction = reconstruction
        if self.reconstruction is None:
            self.reconstruction = self.design.rootComponent

        points_data = sketch_data["points"]
        sketches = self.reconstruction.sketches
        sketch = sketches.itemByName(sketch_name)
        if transform is None:
            transform = adsk.core.Matrix3D.create()

        # Turn off sketch compute until we add all the curves
        sketch.isComputeDeferred = True
        for curve_uuid, curve_data in sketch_data["curves"].items():
            self.reconstruct_sketch_curve(
                sketch,
                curve_data,
                curve_uuid,
                points_data,
                transform=transform,
                sketch_uuid=sketch_uuid,
                sketch_index=sketch_index
            )
        sketch.isComputeDeferred = False
        adsk.doEvents()
        return sketch

    # --------------------------------------------------------
    # SKETCH FEATURE
    # --------------------------------------------------------

    def get_extrude_profiles(self, timeline, entities):
        """Get the profiles used with extrude operations"""
        profiles = set()
        sketches = set()
        for timeline_object in timeline:
            entity_key = timeline_object["entity"]
            entity = entities[entity_key]
            if entity["type"] == "ExtrudeFeature":
                for profile in entity["profiles"]:
                    profiles.add(profile["profile"])
                    sketches.add(profile["sketch"])
        return {
           "profiles": profiles,
           "sketches": sketches
        }

    def find_profile(self, reconstructed_profiles, profile_uuid, profile_data, transform):
        # Sketch profiles are automatically generated by Fusion
        # After we have added the curves we have to traverse the profiles
        # to find one with all of the curve uuids from the original
        sorted_curve_uuids = self.get_curve_uuids(profile_data)
        # print(f"Finding profile {profile_uuid} with {len(sorted_curve_uuids)} curves")
        for index, profile_dict in enumerate(reconstructed_profiles):
            profile = profile_dict["profile"]
            profile_index = profile_dict["profile_index"]
            sorted_found_curve_uuids = profile_dict["curve_uuids"]
            if sorted_found_curve_uuids == sorted_curve_uuids and self.are_profile_properties_identical(profile, profile_data, transform):
                # print(f"Profile found with {len(sorted_curve_uuids)} curve uuids")
                return profile_dict, index
        # print(f"Profile not found: {profile_uuid} with {len(sorted_curve_uuids)} curves")
        return None, -1

    def are_profile_properties_identical(self, profile, profile_data, transform):
        profile_props = profile.areaProperties(adsk.fusion.CalculationAccuracy.HighCalculationAccuracy)
        tolerance = 0.000001
        if not math.isclose(profile_props.area, profile_data["properties"]["area"], abs_tol=tolerance):
            # print("Profile area doesn't match")
            return False
        if not math.isclose(profile_props.perimeter, profile_data["properties"]["perimeter"], abs_tol=tolerance):
            # print("Profile perimeter doesn't match")
            return False
        centroid_point = deserialize.point3d(profile_data["properties"]["centroid"])
        centroid_point.transformBy(transform)
        if not math.isclose(profile_props.centroid.x, centroid_point.x, abs_tol=tolerance):
            # print("Centroid.x doesn't match")
            return False
        if not math.isclose(profile_props.centroid.y, centroid_point.y, abs_tol=tolerance):
            # print("Centroid.y doesn't match")
            return False
        if not math.isclose(profile_props.centroid.z, centroid_point.z, abs_tol=tolerance):
            # print("Centroid.z doesn't match")
            return False
        return True

    def get_profile_curve_uuids(self, sketch, sketch_uuid):
        reconstructed_profiles = []
        for profile_index, profile in enumerate(sketch.profiles):
            # We use a set as there can be duplicate curves in the list
            found_curve_uuids = set()
            for loop in profile.profileLoops:
                for curve in loop.profileCurves:
                    sketch_ent = curve.sketchEntity
                    curve_uuid = self.get_uuid(sketch_ent)
                    if curve_uuid is not None:
                        found_curve_uuids.add(curve_uuid)
            sorted_found_curve_uuids = sorted(list(found_curve_uuids))
            reconstructed_profiles.append({
                "profile": profile,
                "profile_index": profile_index,
                "sketch": sketch,
                "sketch_uuid": sketch_uuid,
                "curve_uuids": sorted_found_curve_uuids
            })
        return reconstructed_profiles

    def get_uuid(self, entity):
        uuid_att = entity.attributes.itemByName("Dataset", "uuid")
        if uuid_att is not None:
            return uuid_att.value
        else:
            return None

    def set_uuid(self, entity, unique_id):
        uuid_att = entity.attributes.itemByName("Dataset", "uuid")
        if uuid_att is None:
            entity.attributes.add("Dataset", "uuid", unique_id)

    def get_curve_uuids(self, profile_data):
        loops = profile_data["loops"]
        # Use a set to remove duplicates
        curve_uuids = set()
        for loop in loops:
            profile_curves = loop["profile_curves"]
            for profile_curve in profile_curves:
                curve_uuids.add(profile_curve["curve"])
        return sorted(list(curve_uuids))

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

    def reconstruct_sketch_feature(self, sketch_data, sketch_profiles,
                                   sketch_uuid=None, sketch_index=None,
                                   sketch_plane=None, transform=None):
        # Skip empty sketches
        if ("curves" not in sketch_data or "profiles" not in sketch_data or
           "points" not in sketch_data):
            return None

        sketches = self.reconstruction.sketches
        # Find the right sketch plane to use
        if sketch_plane is None:
            sketch_plane = self.get_sketch_plane(sketch_data["reference_plane"], sketch_profiles)
        sketch = sketches.addWithoutEdges(sketch_plane)

        # If we want to manually overide the transform we can
        # but the sketch may be flipped without the call to
        # find_transform_for_sketch_geom()
        if transform is not None:
            transform_for_sketch_geom = transform
        else:
            # We need to apply some other transform to the sketch data
            # as sketch geometry created via the UI has a slightly different
            # coordinate system when created via the API
            # This applies when the sketch plane references other geometry
            # like a B-Rep face
            transform_for_sketch_geom = adsk.core.Matrix3D.create()
            sketch_transform = sketch.transform
            transform_for_sketch_geom = self.find_transform_for_sketch_geom(sketch_transform, sketch_data["transform"])

        if self.reconstruct_cb is not None:
            cb_data = {
                "sketch": sketch,
                "sketch_name": sketch_data["name"],
                "corrective_transform": transform_for_sketch_geom
            }
            if sketch_uuid is not None:
                cb_data["sketch_uuid"] = sketch_uuid
            self.reconstruct_cb(cb_data)

        # Draw exactly what the user drew and then search for the profiles
        new_sketch_profiles = self.reconstruct_curves_to_profiles(sketch, sketch_data, sketch_uuid, sketch_index, transform_for_sketch_geom)
        adsk.doEvents()
        return sketch, new_sketch_profiles

    def get_sketch_plane(self, reference_plane, sketch_profiles):
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
        # Sketch Profile as reference plane
        elif reference_plane["type"] == "Profile" and "profile" in reference_plane:
            profile_uuid = reference_plane["profile"]
            # We could reference the original sketch plane like this:
            # return profile.parentSketch.referencePlane
            # But the sketch plane can differ from the profile plane
            # so we go ahead and find the actual profile plane
            sketch_profile = self.get_sketch_profile_reference(profile_uuid, sketch_profiles)
            if sketch_profile is not None:
                # Note: The API doesn't support creating references
                # to sketch profiles directly
                # So instead we create a construction plane from the profile
                # and use that
                # This preserves the reference indirectly
                # through the construction plane
                planes = self.reconstruction.constructionPlanes
                plane_input = planes.createInput()
                offset_distance = adsk.core.ValueInput.createByReal(0)
                plane_input.setByOffset(sketch_profile, offset_distance)
                plane = planes.add(plane_input)
                return plane

        return self.reconstruction.xYConstructionPlane

    def reconstruct_curves_to_profiles(self, sketch, sketch_data, sketch_uuid, sketch_index, transform):
        # Turn off sketch compute until we add all the curves
        sketch.isComputeDeferred = True
        self.reconstruct_sketch_curves(sketch, sketch_data, sketch_uuid, sketch_index, transform)
        sketch.isComputeDeferred = False

        # If we draw the user curves
        # we have to recover the profiles that Fusion generates
        # First pull out the list of reconstructed profile curve uuids
        reconstructed_profiles = self.get_profile_curve_uuids(sketch, sketch_uuid)
        sketch_profiles = {}
        missing_profiles = {}
        # We first try and find exact matches
        # i.e. a profile with the same set of (deduplicated) curve ids
        # and with an area/perimeter/centroid that matches
        for profile_uuid, profile_data in sketch_data["profiles"].items():
            # print("Finding profile", profile_data["profile_uuid"])
            sketch_profile_data, reconstructed_profile_index = self.find_profile(
                reconstructed_profiles, profile_uuid, profile_data, transform
            )
            if sketch_profile_data is not None:
                sketch_profiles[profile_uuid] = sketch_profile_data
                # Remove the matched profile from the pool
                del reconstructed_profiles[reconstructed_profile_index]
            else:
                missing_profiles[profile_uuid] = profile_data

        # Sometimes the exact match will fail,
        # so we search for the most 'similar' profile,
        # with the most common curve uuids,
        # remaining in the reconstructed profile set
        missing_profile_count = len(missing_profiles)
        if missing_profile_count > 0:
            print(f"{missing_profile_count} Missing profiles and {len(reconstructed_profiles)} remaining reconstructed profiles")
            matched_profiles = 0
            for missing_profile_uuid, missing_profile_data in missing_profiles.items():
                best_match_profile_data = self.get_closest_profile(
                    missing_profile_data, reconstructed_profiles, missing_profile_uuid
                )
                if best_match_profile_data is not None:
                    sketch_profiles[missing_profile_uuid] = best_match_profile_data
                    matched_profiles += 1

            unmatched_profiles = missing_profile_count - matched_profiles
            if unmatched_profiles > 0:
                print(f"{unmatched_profiles} left over unmatched profiles!")

        return sketch_profiles

    def get_closest_profile(self, missing_profile_data, reconstructed_profiles, missing_profile_uuid):
        """Try and find the closest profile match based on overlap of curve ids"""
        if len(reconstructed_profiles) == 1:
            return reconstructed_profiles[0]
        sorted_curve_uuids = self.get_curve_uuids(missing_profile_data)
        sorted_curve_uuids_count = len(sorted_curve_uuids)
        max_score = 0
        best_match_index = -1
        for index, reconstructed_profile in enumerate(reconstructed_profiles):
            overlap = self.get_profile_curve_overlap_count(sorted_curve_uuids, reconstructed_profile["curve_uuids"])
            reconstructed_profile_curve_uuids_coint = len(reconstructed_profile["curve_uuids"])
            score = overlap - abs(reconstructed_profile_curve_uuids_coint-sorted_curve_uuids_count)
            if score > max_score:
                best_match_index = index
                max_score = score
        if best_match_index >= 0:
            print(f"""Matching profile {missing_profile_uuid} with {sorted_curve_uuids_count} curves
                to a left over reconstructed profile with {len(reconstructed_profiles[best_match_index]["curve_uuids"])} curves""")
            return reconstructed_profiles[best_match_index]
        else:
            return None

    def get_profile_curve_overlap_count(self, original, reconstructed):
        intersection = set(original) & set(reconstructed)
        return len(intersection)

    def reconstruct_sketch_curves(self, sketch, sketch_data, sketch_uuid, sketch_index, transform):
        """Reconstruct the sketch curves in profile order"""
        curves_data = sketch_data["curves"]
        points_data = sketch_data["points"]
        profiles_data = sketch_data["profiles"]
        current_curves_data = OrderedDict(curves_data)
        # curve_keys = curves_data.keys()
        # Redraw the curves in the order of the profiles
        for profile_uuid, profile in profiles_data.items():
            for loop in profile["loops"]:
                for profile_curve in loop["profile_curves"]:
                    curve_uuid = profile_curve["curve"]
                    #  Only draw the curves that haven't been draw already
                    if curve_uuid in current_curves_data:
                        curve = curves_data[curve_uuid]
                        self.reconstruct_sketch_curve(
                            sketch,
                            curve,
                            curve_uuid,
                            points_data,
                            transform=transform,
                            sketch_uuid=sketch_uuid,
                            sketch_index=sketch_index
                        )
                        # Remove the curve from list of curves to draw
                        del current_curves_data[curve_uuid]
        # Next add the remaining curves not used in profiles
        for curve_uuid, curve in current_curves_data.items():
            self.reconstruct_sketch_curve(
                sketch,
                curve,
                curve_uuid,
                points_data,
                transform=transform,
                sketch_uuid=sketch_uuid,
                sketch_index=sketch_index
            )

    def get_sketch_profile_reference(self, profile_uuid, sketch_profiles):
        """Return a reference to the sketch profile from our stored dict"""
        if profile_uuid not in sketch_profiles:
            return None
        # We have a reference we stored directly of the profile
        # sketch_profile = sketch_profiles[profile_uuid]["profile"]
        # But this reference to the profile fails if you toggle
        # visibility of the sketch off after the reference is created
        # as we do to generate image output of the sequence
        # So instead we find the reference again via the sketch
        sketch = sketch_profiles[profile_uuid]["sketch"]
        sketch_profile_index = sketch_profiles[profile_uuid]["profile_index"]
        sketch_profile = sketch.profiles[sketch_profile_index]
        return sketch_profile

    # --------------------------------------------------------
    # PROFILE CURVES
    # --------------------------------------------------------

    def reconstruct_sketch_curve(self, sketch, curve_data, curve_uuid, points_data,
                                 transform=None, sketch_uuid=None,
                                 sketch_index=None):
        """Reconstruct a sketch curve"""
        if curve_data["construction_geom"]:
            return
        if transform is None:
            transform = adsk.core.Matrix3D.create()
        if curve_data["type"] == "SketchLine":
            curve_obj = self.reconstruct_sketch_line(
                sketch.sketchCurves.sketchLines,
                curve_data, curve_uuid, points_data, transform
            )
        elif curve_data["type"] == "SketchArc":
            curve_obj = self.reconstruct_sketch_arc(
                sketch.sketchCurves.sketchArcs,
                curve_data, curve_uuid, points_data, transform
            )
        elif curve_data["type"] == "SketchCircle":
            curve_obj = self.reconstruct_sketch_circle(
                sketch.sketchCurves.sketchCircles,
                curve_data, curve_uuid, points_data, transform
            )
        elif curve_data["type"] == "SketchEllipse":
            curve_obj = self.reconstruct_sketch_ellipse(
                sketch.sketchCurves.sketchEllipses,
                curve_data, curve_uuid, points_data, transform
            )
        elif curve_data["type"] == "SketchFittedSpline":
            curve_obj = self.reconstruct_sketch_fitted_spline(
                sketch.sketchCurves.sketchFittedSplines,
                curve_data, curve_uuid, transform
            )
        else:
            raise Exception(f"Unsupported curve type: {curve_data['type']}")

        if self.reconstruct_cb is not None:
            cb_data = {
                "sketch": sketch,
                "sketch_name": sketch.name,
                "curve": curve_obj,
                "curve_uuid": curve_uuid
            }
            if sketch_uuid is not None:
                cb_data["sketch_id"] = sketch_uuid
            if sketch_index is not None:
                cb_data["sketch_index"] = sketch_index
            self.reconstruct_cb(cb_data)

    def reconstruct_sketch_line(self, sketch_lines, curve_data, curve_uuid, points_data, transform):
        start_point_uuid = curve_data["start_point"]
        end_point_uuid = curve_data["end_point"]
        start_point = deserialize.point3d(points_data[start_point_uuid])
        end_point = deserialize.point3d(points_data[end_point_uuid])
        start_point.transformBy(transform)
        end_point.transformBy(transform)
        line = sketch_lines.addByTwoPoints(start_point, end_point)
        self.set_uuid(line, curve_uuid)
        return line

    def reconstruct_sketch_arc(self, sketch_arcs, curve_data, curve_uuid, points_data, transform):
        start_point_uuid = curve_data["start_point"]
        center_point_uuid = curve_data["center_point"]
        start_point = deserialize.point3d(points_data[start_point_uuid])
        center_point = deserialize.point3d(points_data[center_point_uuid])
        start_point.transformBy(transform)
        center_point.transformBy(transform)
        sweep_angle = curve_data["end_angle"] - curve_data["start_angle"]
        arc = sketch_arcs.addByCenterStartSweep(center_point, start_point, sweep_angle)
        self.set_uuid(arc, curve_uuid)
        return arc

    def reconstruct_sketch_circle(self, sketch_circles, curve_data, curve_uuid, points_data, transform):
        center_point_uuid = curve_data["center_point"]
        center_point = deserialize.point3d(points_data[center_point_uuid])
        center_point.transformBy(transform)
        radius = curve_data["radius"]
        circle = sketch_circles.addByCenterRadius(center_point, radius)
        self.set_uuid(circle, curve_uuid)
        return circle

    def reconstruct_sketch_ellipse(self, sketch_ellipses, curve_data, curve_uuid, points_data, transform):
        # Ellipse reconstruction requires us to provide 3 points:
        # - Center point
        # - Major axis point
        # - (Minor axis) point that the ellipse will pass through

        # Center point
        center_point_uuid = curve_data["center_point"]
        center_point = deserialize.point3d(points_data[center_point_uuid])
        center_point_vector = center_point.asVector()

        # Major axis point
        # Take the vector for the major axis
        # then normalize it
        # then scale it to the radius of the major axis
        # and offset by the center point
        major_axis = deserialize.vector3d(curve_data["major_axis"])
        major_axis_radius = curve_data["major_axis_radius"]
        major_axis.normalize()
        major_axis_vector = major_axis.copy()
        major_axis_vector.scaleBy(major_axis_radius)
        major_axis_point = major_axis_vector.asPoint()
        major_axis_point.translateBy(center_point_vector)

        # Minor axis point
        # Rotate 90 deg around z from the major axis
        # then scale and offset by the center point
        minor_axis_radius = curve_data["minor_axis_radius"]
        rot_matrix = adsk.core.Matrix3D.create()
        origin = adsk.core.Point3D.create()
        axis = adsk.core.Vector3D.create(0.0, 0.0, 1.0)
        rot_matrix.setToRotation(math.radians(90), axis, origin)
        minor_axis = major_axis.copy()
        minor_axis.transformBy(rot_matrix)
        minor_axis_vector = minor_axis.copy()
        minor_axis_vector.scaleBy(minor_axis_radius)
        minor_axis_point = minor_axis_vector.asPoint()
        minor_axis_point.translateBy(center_point_vector)

        # Finally apply the sketch alignment matrix
        major_axis_point.transformBy(transform)
        minor_axis_point.transformBy(transform)
        center_point.transformBy(transform)

        ellipse = sketch_ellipses.add(center_point, major_axis_point, minor_axis_point)
        self.set_uuid(ellipse, curve_uuid)
        return ellipse

    def reconstruct_sketch_fitted_spline(self, sketch_fitted_splines, curve_data, curve_uuid, transform):
        nurbs_curve = self.get_nurbs_curve(curve_data, transform)
        spline = sketch_fitted_splines.addByNurbsCurve(nurbs_curve)
        self.set_uuid(spline, curve_uuid)
        return spline

    def get_nurbs_curve(self, curve_data, transform):
        control_points = deserialize.point3d_list(curve_data["control_points"], transform)
        nurbs_curve = None
        if curve_data["rational"] is True:
            nurbs_curve = adsk.core.NurbsCurve3D.createRational(
                control_points, curve_data["degree"],
                curve_data["knots"], curve_data["weights"],
                curve_data["periodic"]
            )
        else:
            nurbs_curve = adsk.core.NurbsCurve3D.createNonRational(
                control_points, curve_data["degree"],
                curve_data["knots"], curve_data["periodic"]
            )
        return nurbs_curve

    # --------------------------------------------------------
    # TRIMMED PROFILE CURVES
    # --------------------------------------------------------

    def reconstruct_trimmed_curves(self, sketch, profile_data, transform):
        loops = profile_data["loops"]
        for loop in loops:
            profile_curves = loop["profile_curves"]
            for curve_data in profile_curves:
                self.reconstruct_trimmed_curve(sketch, curve_data, transform)

    def reconstruct_trimmed_curve(self, sketch, curve_data, transform):
        if curve_data["type"] == "Line3D":
            self.reconstruct_line(
                sketch.sketchCurves.sketchLines, curve_data, transform
            )
        elif curve_data["type"] == "Arc3D":
            self.reconstruct_arc(
                sketch.sketchCurves.sketchArcs, curve_data, transform
            )
        elif curve_data["type"] == "Circle3D":
            self.reconstruct_circle(
                sketch.sketchCurves.sketchCircles, curve_data, transform
            )
        elif curve_data["type"] == "Ellipse3D":
            self.reconstruct_ellipse(
                sketch.sketchCurves.sketchEllipses, curve_data, transform
            )
        elif curve_data["type"] == "NurbsCurve3D":
            self.reconstruct_nurbs_curve(
                sketch.sketchCurves.sketchFittedSplines, curve_data, transform
            )
        else:
            raise Exception(f"Unsupported curve type: {curve_data['type']}")

    def reconstruct_line(self, sketch_lines, curve_data, transform):
        start_point = deserialize.point3d(curve_data["start_point"])
        start_point.transformBy(transform)
        end_point = deserialize.point3d(curve_data["end_point"])
        end_point.transformBy(transform)
        line = sketch_lines.addByTwoPoints(start_point, end_point)
        self.set_uuid(line, curve_data["curve"])
        return line

    def reconstruct_arc(self, sketch_arcs, curve_data, transform):
        start_point = deserialize.point3d(curve_data["start_point"])
        start_point.transformBy(transform)
        center_point = deserialize.point3d(curve_data["center_point"])
        center_point.transformBy(transform)
        sweep_angle = curve_data["end_angle"] - curve_data["start_angle"]
        arc = sketch_arcs.addByCenterStartSweep(center_point, start_point, sweep_angle)
        self.set_uuid(arc, curve_data["curve"])
        return arc

    def reconstruct_circle(self, sketch_circles, curve_data, transform):
        center_point = deserialize.point3d(curve_data["center_point"])
        center_point.transformBy(transform)
        radius = curve_data["radius"]
        circle = sketch_circles.addByCenterRadius(center_point, radius)
        self.set_uuid(circle, curve_data["curve"])
        return circle

    def reconstruct_ellipse(self, sketch_ellipses, curve_data, transform):
        # Ellipse reconstruction requires us to provide 3 points:
        # - Center point
        # - Major axis point
        # - (Minor axis) point that the ellipse will pass through

        # Center point
        center_point = deserialize.point3d(curve_data["center_point"])
        center_point_vector = center_point.asVector()

        # Major axis point
        # Take the vector for the major axis
        # then normalize it
        # then scale it to the radius of the major axis
        # and offset by the center point
        major_axis = deserialize.vector3d(curve_data["major_axis"])
        major_axis_radius = curve_data["major_axis_radius"]
        major_axis.normalize()
        major_axis_vector = major_axis.copy()
        major_axis_vector.scaleBy(major_axis_radius)
        major_axis_point = major_axis_vector.asPoint()
        major_axis_point.translateBy(center_point_vector)

        # Minor axis point
        # Rotate 90 deg around z from the major axis
        # then scale and offset by the center point
        minor_axis_radius = curve_data["minor_axis_radius"]
        rot_matrix = adsk.core.Matrix3D.create()
        origin = adsk.core.Point3D.create()
        axis = adsk.core.Vector3D.create(0.0, 0.0, 1.0)
        rot_matrix.setToRotation(math.radians(90), axis, origin)
        minor_axis = major_axis.copy()
        minor_axis.transformBy(rot_matrix)
        minor_axis_vector = minor_axis.copy()
        minor_axis_vector.scaleBy(minor_axis_radius)
        minor_axis_point = minor_axis_vector.asPoint()
        minor_axis_point.translateBy(center_point_vector)

        # Finally apply the sketch alignment matrix
        major_axis_point.transformBy(transform)
        minor_axis_point.transformBy(transform)
        center_point.transformBy(transform)

        ellipse = sketch_ellipses.add(center_point, major_axis_point, minor_axis_point)
        self.set_uuid(ellipse, curve_data["curve"])
        return ellipse

    def reconstruct_nurbs_curve(self, sketch_fitted_splines, curve_data, transform):
        nurbs_curve = self.get_nurbs_curve(curve_data, transform)
        spline = sketch_fitted_splines.addByNurbsCurve(nurbs_curve)
        self.set_uuid(spline, curve_data["curve"])
        return spline

    # --------------------------------------------------------
    # EXTRUDE FEATURE
    # --------------------------------------------------------

    def reconstruct_extrude_feature(self, extrude_data, extrude_uuid, extrude_index, sketch_profiles):
        extrudes = self.reconstruction.features.extrudeFeatures

        # There can be more than one profile, so we create an object collection
        extrude_profiles = adsk.core.ObjectCollection.create()
        for profile in extrude_data["profiles"]:
            profile_uuid = profile["profile"]
            sketch_profile = self.get_sketch_profile_reference(profile_uuid, sketch_profiles)
            extrude_profiles.add(sketch_profile)

        # The operation defines if the extrusion becomes a new body
        # a new component or cuts/joins another body (i.e. boolean operation)
        operation = deserialize.feature_operations(extrude_data["operation"])
        extrude_input = extrudes.createInput(extrude_profiles, operation)

        # Simple extrusion in one direction
        if extrude_data["extent_type"] == "OneSideFeatureExtentType":
            self.set_one_side_extrude_input(extrude_input, extrude_data["extent_one"])
        # Extrusion in two directions with different distances
        elif extrude_data["extent_type"] == "TwoSidesFeatureExtentType":
            self.set_two_side_extrude_input(extrude_input, extrude_data["extent_one"], extrude_data["extent_two"])
        # Symmetrical extrusion by the same distance on each side
        elif extrude_data["extent_type"] == "SymmetricFeatureExtentType":
            self.set_symmetric_extrude_input(extrude_input, extrude_data["extent_one"])

        # The start extent is initialized to be the profile plane
        # but we may need to change it to an offset
        # after all other changes
        self.set_start_extent(extrude_input, extrude_data["start_extent"])
        extrude = extrudes.add(extrude_input)

        if self.reconstruct_cb is not None:
            self.reconstruct_cb({
                "extrude": extrude,
                "extrude_name": extrude_data["name"],
                "extrude_id": extrude_uuid,
                "extrude_index": extrude_index
            })
        return extrude

    def set_start_extent(self, extrude_input, start_extent):
        # Only handle the offset case
        # ProfilePlaneStartDefinition is already setup
        # and other cases we don't handle
        if start_extent["type"] == "OffsetStartDefinition":
            offset_distance = adsk.core.ValueInput.createByReal(start_extent["offset"]["value"])
            offset_start_def = adsk.fusion.OffsetStartDefinition.create(offset_distance)
            extrude_input.startExtent = offset_start_def

    def set_one_side_extrude_input(self, extrude_input, extent_one):
        distance = adsk.core.ValueInput.createByReal(extent_one["distance"]["value"])
        extent_distance = adsk.fusion.DistanceExtentDefinition.create(distance)
        taper_angle = adsk.core.ValueInput.createByReal(0)
        if "taper_angle" in extent_one:
            taper_angle = adsk.core.ValueInput.createByReal(extent_one["taper_angle"]["value"])
        extrude_input.setOneSideExtent(extent_distance, adsk.fusion.ExtentDirections.PositiveExtentDirection, taper_angle)

    def set_two_side_extrude_input(self, extrude_input, extent_one, extent_two):
        distance_one = adsk.core.ValueInput.createByReal(extent_one["distance"]["value"])
        distance_two = adsk.core.ValueInput.createByReal(extent_two["distance"]["value"])
        extent_distance_one = adsk.fusion.DistanceExtentDefinition.create(distance_one)
        extent_distance_two = adsk.fusion.DistanceExtentDefinition.create(distance_two)
        taper_angle_one = adsk.core.ValueInput.createByReal(0)
        taper_angle_two = adsk.core.ValueInput.createByReal(0)
        if "taper_angle" in extent_one:
            taper_angle_one = adsk.core.ValueInput.createByReal(extent_one["taper_angle"]["value"])
        if "taper_angle" in extent_two:
            taper_angle_two = adsk.core.ValueInput.createByReal(extent_two["taper_angle"]["value"])
        extrude_input.setTwoSidesExtent(extent_distance_one, extent_distance_two, taper_angle_one, taper_angle_two)

    def set_symmetric_extrude_input(self, extrude_input, extent_one):
        # SYMMETRIC EXTRUDE
        # Symmetric extent is currently buggy when a taper is applied
        # So instead we use a two sided extent with symmetry
        # Note that the distance is not a DistanceExtentDefinition
        # distance = adsk.core.ValueInput.createByReal(extent_one["distance"]["value"])
        # taper_angle = adsk.core.ValueInput.createByReal(0)
        # if "taper_angle" in extent_one:
        #     taper_angle = adsk.core.ValueInput.createByReal(extent_one["taper_angle"]["value"])
        # is_full_length = extent_one["is_full_length"]
        # extrude_input.setSymmetricExtent(distance, is_full_length, taper_angle)
        #
        # TWO SIDED EXTRUDE WORKAROUND
        distance = extent_one["distance"]["value"]
        if extent_one["is_full_length"]:
            distance = distance * 0.5
        distance_one = adsk.core.ValueInput.createByReal(distance)
        distance_two = adsk.core.ValueInput.createByReal(distance)
        extent_distance_one = adsk.fusion.DistanceExtentDefinition.create(distance_one)
        extent_distance_two = adsk.fusion.DistanceExtentDefinition.create(distance_two)
        taper_angle_one = adsk.core.ValueInput.createByReal(0)
        taper_angle_two = adsk.core.ValueInput.createByReal(0)
        if "taper_angle" in extent_one:
            taper_angle_one = adsk.core.ValueInput.createByReal(extent_one["taper_angle"]["value"])
            taper_angle_two = adsk.core.ValueInput.createByReal(extent_one["taper_angle"]["value"])
        extrude_input.setTwoSidesExtent(extent_distance_one, extent_distance_two, taper_angle_one, taper_angle_two)
