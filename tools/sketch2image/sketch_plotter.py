import matplotlib.pyplot as plt
import matplotlib.lines as lines
import matplotlib.patches as patches
import math
import sys

class SketchPlotter:
    """
    A class to read plot the geometry from a json sketch file
    """
    def __init__(self, sketch, title = None, opts = None):
        """
        Initialize the object with the dictionary of the sketch data
        """
        self.sketch = sketch
        self.fig, self.ax = plt.subplots()

        # Set some default options
        self.draw_annotation = False
        self.draw_grid = False
        self.linewidth = 1
        if opts is not None:
            if opts.draw_annotation is not None:
                self.draw_annotation = opts.draw_annotation
            if opts.draw_grid:
                self.draw_grid = True
            if self.linewidth is not None:
                self.linewidth = opts.linewidth
        
        # Add a title if one was given
        if title is not None:
            self.fig.suptitle(title, fontsize=16)


    def get_point(self, point_uuid):
        """
        Get a tuple with the x, y coordinates of a point
        """
        point_struct = self.sketch["points"][point_uuid]
        return (point_struct["x"], point_struct["y"])

    def get_vec(self, vec_struct):
        """
        Get a tuple with the x, y coordinates of a vector
        """
        return (vec_struct["x"], vec_struct["y"])

    def angle_from_vector_to_x(self, vec):
        angle = 0.0
        # 2 | 1
        #-------
        # 3 | 4
        if vec[0] >=0:
            if vec[1] >= 0:
                # Qadrant 1
                angle = math.asin(vec[1])
            else:
                # Qadrant 4
                angle = 2.0*math.pi - math.asin(-vec[1])
        else:
            if vec[1] >= 0:
                # Qadrant 2
                angle = math.pi - math.asin(vec[1])
            else:
                # Qadrant 3
                angle = math.pi + math.asin(-vec[1])
        return angle
    
    def rads_to_degs(self, rads):
        """
        Convert an angle from radians to degrees
        """
        return 180*rads/math.pi

    def add_line(self, pt0, pt1, color):
        """
        Add a line to the plot
        """
        xdata = [pt0[0], pt1[0]]
        ydata = [pt0[1], pt1[1]]
        l1 = lines.Line2D(xdata, ydata, lw=self.linewidth, color=color, axes=self.ax)
        self.ax.add_line(l1)


    def draw_line(self, line_uuid):
        """
        Draw a line given its uuid
        """
        line = self.sketch["curves"][line_uuid]
        assert line["type"] == "SketchLine"

        p0 = self.get_point(line["start_point"])
        p1 = self.get_point(line["end_point"])
        self.add_line(p0, p1, 'black')

    def draw_arc(self, arc_uuid):
        """
        Draw an arc given its uuid
        """
        arc = self.sketch["curves"][arc_uuid]
        center = self.get_point(arc["center_point"])
        r = arc["radius"]
        ref_vec = self.get_vec(arc["reference_vector"])
        ref_vec_angle = self.rads_to_degs(self.angle_from_vector_to_x(ref_vec))
        start_angle = self.rads_to_degs(arc["start_angle"])
        end_angle = self.rads_to_degs(arc["end_angle"])
        diameter = 2.0*r
        ap = patches.Arc(
            center, 
            diameter,
            diameter,
            angle=ref_vec_angle, 
            theta1=start_angle, 
            theta2=end_angle,  
            lw=self.linewidth
        )
        self.ax.add_patch(ap)

    def draw_circle(self, circle_uuid):
        """
        Draw a circle given its uuid
        """
        circle = self.sketch["curves"][circle_uuid]
        center = self.get_point(circle["center_point"])
        r = circle["radius"]
        ap = patches.Circle(center, r, lw=self.linewidth, fill=None, color="black")
        self.ax.add_patch(ap)

    def draw_point(self, point_uuid):
        """
        Plot a point given its uuid
        """
        pt = self.get_point(point_uuid)
        if self.draw_annotation:
            self.ax.plot(pt[0], pt[1], 'ok')

                
    def draw_curves(self):
        """
        Draw the curves in the sketch
        """
        for curve_uuid in self.sketch["curves"]:
            curve = self.sketch["curves"][curve_uuid]
            curve_type = curve["type"]
            if curve_type == "SketchLine":
                self.draw_line(curve_uuid)
            elif curve_type == "SketchArc":
                self.draw_arc(curve_uuid)
            elif curve_type == "SketchCircle":
                self.draw_circle(curve_uuid)
            else:
               print(f"Warning! -- Curve type {curve_type} is not supported yet")

    def find_type_from_uuid(self, uuid):
        """
        Find the type of a sketch entity from its uuid
        """
        if uuid in self.sketch["points"]:
            return "Point"
        if uuid in self.sketch["curves"]:
            return "Curve"
        if uuid in self.sketch["constraints"]:
            return "Constraint"
        if uuid in self.sketch["dimensions"]:
            return "Dimension"
        return ""

    def draw_points(self):
        """
        Plot the points in the sketch
        """
        for point_uuid in self.sketch["points"]:
            self.draw_point(point_uuid)

    def create_drawing(self):
        """
        Create the sketch drawing
        """
        self.draw_curves()
        self.draw_points()
        self.ax.axis('equal')
        if self.draw_grid:
            self.ax.grid()
        else:
            plt.axis('off')

    def show(self):
        """
        Show the plot
        """
        plt.show()

    def save_image(self, pathname):
        """
        Save an image of the plot
        """
        plt.savefig(pathname, dpi = 100)

    def close_figure(self):
        """
        Close the figure after plotting or displaying the sketch
        """
        plt.close(self.fig)
