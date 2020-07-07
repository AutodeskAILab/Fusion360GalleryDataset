import json
import os
from pathlib import Path
import argparse
from sketch_plotter import SketchPlotter

parser = argparse.ArgumentParser()
parser.add_argument("--input_folder", type=str, help="The input directory containing the json files")
parser.add_argument("--output_folder", type=str, help="The output folder for the images")
parser.add_argument("--linewidth", type=int, default=1,help="The linewidth to draw the geometry")
parser.add_argument("--show_title", type=int, default=1, help="Add a title to the image")
parser.add_argument("--draw_annotation", type=int, default=0, help="Draw additional annotation")
parser.add_argument("--draw_grid", type=int, default=0, help="Draw a grid with the image")
args = parser.parse_args()

if args.input_folder is None:
    print("Please specify input folder with the --input_folder argument")
    exit()

if args.output_folder is None:
    print("Please specify output folder with the --output_folder argument")
    exit()


def read_json(pathname):
    """Read json from a file"""
    with open(pathname) as data_file:
        try:
            json_data = json.load(data_file)
        except:
            print(f"Error reading file {pathname}")
            return None
    return json_data

def check_valid_sketch(sketch_data):
    if sketch_data is None:
        return False
    if not "points" in sketch_data:
        return False
    if not "curves" in sketch_data:
        return False
    return True

def get_short_name(filename):
    name = filename.stem
    # We expect something like 
    # ReconstructionExtractor_Z0HexagonCutJoin_3797e54d_Untitled
    names = name.split("_")
    if len(names) == 4:
        name = names[1] + " " + names[2]
    return name

def image_pathname(file, sketch_name, output_path):
    filename = file.stem + "_"+sketch_name
    return (output_path / filename).with_suffix(".png")

def image_exists(file, sketch_name, output_path):
    return image_pathname(file, sketch_name, output_path).exists()

def create_sketch_image(sketch, file, output_path, opts):
    if check_valid_sketch(sketch):
        sketch_name = sketch["name"]
        if image_exists(file, sketch_name, output_path):
            print(f"Image for {file} already exists.  Skiping")
            return
        if opts.show_title:
            title = get_short_name(file) + " " + sketch_name
        else:
            title = None
        sp = SketchPlotter(sketch, title, opts)
        sp.create_drawing()
        save_path = image_pathname(file, sketch_name, output_path)
        sp.save_image(save_path)
        sp.close_figure()

def create_sketch_images(json_pathname, output_path, opts):
    data = read_json(json_pathname)
    if not "entities" in data:
        return
    for entity in data["entities"].values():
        if not "type" in entity:
            continue
        if entity["type"] == "Sketch":
            create_sketch_image(entity, json_pathname, output_path, opts)


input_path = Path(args.input_folder)
output_path = Path(args.output_folder)
if not output_path.exists():
    output_path.mkdir()

files = [f for f in input_path.glob("**/*.json")]
for file in files:
    try:
        create_sketch_images(file, output_path, args)
    except Exception as ex:
        print(f"Exception processing sketch {file}.")
        print(f"{str(ex)}")

print("")
print("")
print("Completed sketch2image.py")
