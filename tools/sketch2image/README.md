# Sketch2image
This python utility code creates images from the json sketch data provided with the [Reconstruction Dataset](../../docs/reconstruction.md).  

![Sketch2image](https://i.gyazo.com/082c98ad41df279f20c9e2caab947e1d.png)

## [sketch_plotter.py](sketch_plotter.py)
The SketchPlotter class is a reusable utility for plotting sketch data using matplotlib.  
```
SketchPlotter(sketch, title=None, opts=None)
```
-   `title`:  A title for the image
-   `opts`:
    - `opts.draw_annotation`:   Draw annotation like the sketch points
    - `opts.draw_grid`:  Draw a background grid
    - `opts.linewidth`:  Linewidth for the sketch curves

## [sketch2image.py](sketch2image.py)
A utility to create sketch images for every reconstruction json file in a folder
```
python sketch2image.py --input_folder /path/to/json_files/ --output_folder /path/to/put/images
```