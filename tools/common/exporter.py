import adsk.core
import adsk.fusion
import json

import view_control


def get_design_product():
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    return design


def export_stl_from_component(file, component):
    """Export a component as an STL"""
    design = get_design_product()
    try:
        stl_export_options = design.exportManager.createSTLExportOptions(
            component, str(file.resolve()))
        stl_export_options.sendToPrintUtility = False
        return design.exportManager.execute(stl_export_options)
    except:
        return False


def export_obj_from_component(file, component):
    """Export a component as an OBJ"""
    breps = component.bRepBodies
    if len(breps) > 0:
        return export_obj_from_bodies(file, breps)
    return False


def export_obj_from_body(file, body):
    """Export a body as an OBJ"""
    return export_obj_from_bodies(file, [body])


def export_obj_from_bodies(file, bodies):
    """Export bodies collection/list as an OBJ"""
    try:
        meshes = []
        for body in bodies:
            mesher = body.meshManager.createMeshCalculator()
            mesher.setQuality(
                adsk.fusion.TriangleMeshQualityOptions.NormalQualityTriangleMesh
            )
            mesh = mesher.calculate()
            meshes.append(mesh)

        triangle_count = 0
        vert_count = 0
        for mesh in meshes:
            triangle_count += mesh.triangleCount
            vert_count += mesh.nodeCount

        # Write the mesh to OBJ
        with open(file, "w") as fh:
            fh.write("# WaveFront *.obj file\n")
            fh.write(f"# Vertices: {vert_count}\n")
            fh.write(f"# Triangles : {triangle_count}\n\n")

            for mesh in meshes:
                verts = mesh.nodeCoordinates
                for pt in verts:
                    fh.write(f"v {pt.x} {pt.y} {pt.z}\n")
            for mesh in meshes:
                for vec in mesh.normalVectors:
                    fh.write(f"vn {vec.x} {vec.y} {vec.z}\n")

            index_offset = 0
            for mesh in meshes:
                mesh_tri_count = mesh.triangleCount
                indices = mesh.nodeIndices
                for t in range(mesh_tri_count):
                    i0 = indices[t * 3] + 1 + index_offset
                    i1 = indices[t * 3 + 1] + 1 + index_offset
                    i2 = indices[t * 3 + 2] + 1 + index_offset
                    fh.write(f"f {i0}//{i0} {i1}//{i1} {i2}//{i2}\n")
                index_offset += mesh.nodeCount

            fh.write(f"\n# End of file")
            return True

    except Exception as ex:
        return False


def get_occurrence_from_body(body):
    """Receives a body and returns an occurrence with the copied body inside of it"""
    transform = adsk.core.Matrix3D.create()
    # Create a new component and occurrence of it at the root of the design
    design = get_design_product()
    temp_occ = design.rootComponent.occurrences.addNewComponent(transform)
    # Copy our body to the component
    body.copyToComponent(temp_occ)
    return temp_occ


def export_smt_from_component(file, component):
    """Export a component as a SMT file"""
    try:
        design = get_design_product()
        design.fusionUnitsManager.distanceDisplayUnits = \
            adsk.fusion.DistanceUnits.CentimeterDistanceUnits
        smt_export_options = design.exportManager.createSMTExportOptions(
            str(file.resolve()), component)
        export_success = design.exportManager.execute(smt_export_options)
        return export_success
    except Exception as ex:
        return False


def export_smt_from_body(file, body):
    """Export a body as a SMT file"""
    temp_brep_manager = adsk.fusion.TemporaryBRepManager.get()
    return temp_brep_manager.exportToFile([body], str(file.resolve()))


def export_smt_from_bodies(file, bodies):
    """Export a list/collection of bodies as an SMT file"""
    temp_brep_manager = adsk.fusion.TemporaryBRepManager.get()
    return temp_brep_manager.exportToFile(bodies, str(file.resolve()))


def export_step_from_component(file, component):
    """Export a component as a STEP file"""
    try:
        design = get_design_product()
        step_export_options = design.exportManager.createSTEPExportOptions(
            str(file.resolve()), component)
        return design.exportManager.execute(step_export_options)
    except Exception as ex:
        return False


def export_step_from_body(file, body):
    """Export a body as a STEP file"""
    result = False
    # Workaround to make a new occurrence, export, then delete it
    occurrence = get_occurrence_from_body(body)
    if occurrence:
        result = export_step_from_component(file, occurrence.component)
        occurrence.deleteMe()
    return result


def export_f3d(file):
    """Export a design as an f3d file"""
    try:
        design = get_design_product()
        fusion_archive_options = design.exportManager.createFusionArchiveExportOptions(str(file.resolve()))
        return design.exportManager.execute(fusion_archive_options)
    except Exception as ex:
        return False


def export_json(file, data):
    """Export a dict to JSON"""
    with open(file, 'w', encoding='utf8') as fp:
        json.dump(data, fp, indent=4, ensure_ascii=False, sort_keys=False)


def export_png_from_sketch(file, sketch, reset_camera=True,
                           width=600, height=600):
    """Export a png of a sketch with a given size"""
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    # Hide everything
    view_control.set_geometry_visible(False, False, False)
    # Show the sketch
    sketch.isVisible = True
    if(reset_camera):
        # Pull out the transform matrix pieces
        (origin, x_axis, y_axis, z_axis) = \
            sketch.transform.getAsCoordinateSystem()
        # We will fit to the contents of the screen
        # So we just need to point the camera in the right direction
        eye_offset = z_axis.asPoint()
        view_control.orient_camera(eye_offset, y_axis, origin, fit=False)
    # Save image
    app.activeViewport.saveAsImageFile(str(file.resolve()), width, height)
    # Show everything again
    view_control.set_geometry_visible(True, True, True)
    adsk.doEvents()
    app.activeViewport.refresh()


def export_png_from_component(file, component, reset_camera=True,
                              width=600, height=600):
    """Export a png of a component with a given size"""
    app = adsk.core.Application.get()
    design = app.activeProduct
    if component == design.rootComponent:
        design.activateRootComponent()
    else:
        occurrences = design.rootComponent.allOccurrencesByComponent(component)
        occurrences[0].activate()
    if reset_camera:
        app.activeViewport.fit()
    # app.activeViewport.visualStyle = adsk.core.VisualStyles.ShadedVisualStyle
    app.activeViewport.saveAsImageFile(str(file.resolve()), width, height)
