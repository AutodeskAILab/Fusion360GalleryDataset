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

## create_sketch_images.py
A utility to create sketch images for every reconstruction json file in a folder
```
python create_sketch_images.py --input_folder /path/to/json_files/ --output_folder /path/to/put/images
```