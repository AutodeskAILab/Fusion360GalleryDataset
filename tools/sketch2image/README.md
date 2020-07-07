# Sketch2image
This python utility code creates images from the json data of a sketch.  

## sketch_plotter.py
The SketchPlotter class is a reusable utility for plotting sketch data using matplotlib.  
```
SketchPlotter(sketch, title=None, opts=None)
```
-   title:  A title for the image
-   opts:
    - opts.draw_annotation:   Draw annotation like the sketch points
    - opts.draw_grid:  Draw a background grid
    - opts.linewidth:  Linewidth for the sketch curves

## sketch2image.py
A utility to create sketch images for every reconstruction json file in a folder
```
python sketch2image.py --input_folder /path/to/json_files/ --output_folder /path/to/put/images
```