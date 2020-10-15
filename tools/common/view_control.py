import adsk.core
import adsk.fusion


def disable_grid_display():
    """Disable display of grid - useful to do before exporting a thumbnail"""
    app = adsk.core.Application.get()
    ui = app.userInterface
    cmd_def = ui.commandDefinitions.itemById('ViewLayoutGridCommand')
    list_control_def = adsk.core.ListControlDefinition.cast(
        cmd_def.controlDefinition)
    layout_grid_item = list_control_def.listItems.item(0)
    layout_grid_item.isSelected = False


def orient_camera(offset,
                  up_vector=adsk.core.Vector3D.create(0, 0, 1),
                  target=adsk.core.Point3D.create(0, 0, 0),
                  fit=True):
    """Orient the camera to look at a given target"""
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)

    # Get the existing camera and modify it
    camera = app.activeViewport.camera
    camera.isSmoothTransition = False

    # We will fit to the contents of the screen
    # So we just need to point the camera in the right direction
    camera.target = target
    camera.upVector = up_vector
    camera.eye = adsk.core.Point3D.create(
        target.x + offset.x,
        target.y + offset.y,
        target.z + offset.z
    )

    camera.isFitView = True
    app.activeViewport.camera = camera  # Update the viewport

    if(fit):
        # Set this once to fit to the camera view
        # But fit() needs to also be called below
        # Call fit to the screen after we have changed to top view
        app.activeViewport.fit()


def set_geometry_visible(bodies=True, sketches=True, profiles=True):
    """Toggle the visibility of geometry"""
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)

    for component in design.allComponents:
        for body in component.bRepBodies:
            body.isVisible = bodies
        for sketch in component.sketches:
            sketch.isVisible = sketches
            sketch.areProfilesShown = profiles
    adsk.doEvents()
