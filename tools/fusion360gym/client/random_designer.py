from pathlib import Path
from requests.exceptions import ConnectionError
import numpy as np
import math
import random
import argparse
from threading import Timer

from random_designer_env import RandomDesignerEnv

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080

RECONSTRUCTION_DATA_PATH = "d7"
GENERATED_DATA_PATH = "generated_design"

TOTAL_EPISODES = 2000

MIN_AREA = 10
MAX_AREA = 2000

EXTRUDE_LIMIT = 10
SCALE_FACTOR = 3
TRANSLATE_NOISE = 0
MAX_NUM_FACES_PER_PROFILE = 15
MAX_STEPS = 4
TWO_MORE_EXTRUDE = True

MACHINE_ID = 2

# Global variable to indicated if we have timed out
halted = False


def main(input_dir, output_dir, split_file, host, port, machine_id=MACHINE_ID):
    global halted

    random_designer = RandomDesignerEnv(
        host=host,
        port=port,
        extrude_limit=EXTRUDE_LIMIT,
        data_dir=input_dir,
        split_file=split_file,
        launch_gym=True
    )

    episode = 0
    skip_regraph = False

    while episode < TOTAL_EPISODES:

        try:
            halt_timer = setup_timer(random_designer)
            current_num_faces = 0

            # setup
            random_designer.client.clear()
            target_face, sketch_plane = random_designer.setup_from_distributions()

            # pick up a random json file
            json_data, json_file_dir = random_designer.select_json(input_dir)

            # retrieve the json in case we need to investigate it
            print("The base sketch is：{}\n".format(json_file_dir))

            # traverse all the sketches from the json data
            sketches = random_designer.traverse_sketches(json_data)
            # skip if the json file doesn't contain sketches
            if len(sketches) == 0:
                halt_timer.cancel()
                continue

            # pick the sketch that has the largest area
            sketch, sketch_name, average_area, sketch_area = random_designer.largest_area(
                sketches)
            if sketch is None:
                halt_timer.cancel()
                continue
            # print("average area: {}".format(average_area))
            # print("max area: {}".format(max_area))

            # filter out designs are too larger
            if sketch_area > MAX_AREA or sketch_area < MIN_AREA:
                print("Invalid area\n")
                halt_timer.cancel()
                continue

            # calculate the centroid of the sketch
            sketch_centroid = random_designer.calculate_sketch_centroid(sketch)
            # print("base sketch centroid: {}".format(sketch_centroid))

            # translate the sketch to the center
            if sketch_plane == "XY":
                translate = {
                    "x": -sketch_centroid["x"], "y": -sketch_centroid["y"], "z": 0}
                rotate = {"x": 0, "y": 0, "z": random.randint(0, 359)}
                scale = {"x": random.uniform(
                    1, SCALE_FACTOR), "y": random.uniform(1, SCALE_FACTOR), "z": 1}
            elif sketch_plane == "XZ":
                translate = {
                    "x": -sketch_centroid["x"], "y": 0, "z": -sketch_centroid["z"]}
                rotate = {"x": 0, "y": random.randint(0, 359), "z": 0}
                scale = {"x": random.uniform(
                    1, SCALE_FACTOR), "y": 1, "z": random.uniform(1, SCALE_FACTOR)}
            elif sketch_plane == "YZ":
                translate = {"x": 0, "y": -
                             sketch_centroid["y"], "z": -sketch_centroid["z"]}
                rotate = {"x": random.randint(0, 359), "y": 0, "z": 0}
                scale = {"x": 1, "y": random.uniform(
                    1, SCALE_FACTOR), "z": random.uniform(1, SCALE_FACTOR)}

            # reconsturct the based sketch
            r = random_designer.client.reconstruct_sketch(
                json_data, sketch_name, sketch_plane=sketch_plane, scale=scale, translate=translate, rotate=rotate)
            response_data = r.json()
            if response_data["status"] == 500:
                print(response_data["message"])
                halt_timer.cancel()
                continue

            base_faces, num_faces = random_designer.extrude_profiles(
                response_data)
            if base_faces is None or num_faces > MAX_NUM_FACES_PER_PROFILE:
                halt_timer.cancel()
                continue

            if not TWO_MORE_EXTRUDE:
                current_num_faces += num_faces

            # start the sub-sketches
            steps = 0
 
            while current_num_faces < target_face and len(base_faces) > 0 and steps < MAX_STEPS:

                try:
                    sketch_plane = random_designer.select_plane(base_faces)
                except ValueError:
                    continue

                # pick up a new random json file
                json_data, json_file_dir = random_designer.select_json(
                    input_dir)
                print("The sub-sketch is：{}\n".format(json_file_dir))

                sketches = random_designer.traverse_sketches(json_data)
                if len(sketches) == 0:
                    continue

                sketch = np.random.choice(sketches, 1)[0]
                sketch_name = sketch["name"]
                sketch_centroid = random_designer.calculate_sketch_centroid(
                    sketch)
                sketch_average_area = random_designer.calculate_average_area(
                    sketch["profiles"])

                scale = {"x": 1, "y": 1, "z": 1}
                if(sketch_average_area > average_area * 2):
                    resize_factor = math.ceil(
                        sketch_average_area / average_area)
                    scale = {"x": 1/resize_factor, "y": 1 /
                             resize_factor, "z": 1/resize_factor}
                translate = {"x": -sketch_centroid["x"] + random.uniform(-TRANSLATE_NOISE, TRANSLATE_NOISE),
                             "y": -sketch_centroid["y"] + random.uniform(-TRANSLATE_NOISE, TRANSLATE_NOISE),
                             "z": 0}

                r = random_designer.client.reconstruct_sketch(
                    json_data, sketch_name, sketch_plane=sketch_plane, scale=scale, translate=translate)
                response_data = r.json()
                if response_data["status"] == 500:
                    print(response_data["message"])

                num_faces = random_designer.extrude_one_profile(response_data)
                current_num_faces += num_faces

                if num_faces > MAX_NUM_FACES_PER_PROFILE or num_faces == 0:
                    skip_regraph = True
                    continue

                steps += 1

            if skip_regraph:
                skip_regraph = False
                halt_timer.cancel()
                continue

            # save graph and f3d
            try:
                success = random_designer.save(output_dir, machine_id)
                if success:
                    episode += 1
            except OSError:
                # random_designer.launch_gym()
                halt_timer.cancel()
                continue

            halt_timer.cancel()

        except ConnectionError as ex:
            print("ConnectionError!")
            if not halted:
                halted = True
                halt_timer.cancel()
                print("Launching the gym again...")
                random_designer.launch_gym()
                continue


def halt(env):
    """Halt generation of the current design"""
    global halted
    print("Halting...")
    halted = True
    env.kill_gym()


def setup_timer(env):
    """Setup the timer to halt execution if needed"""
    global halted
    # We put a hard cap on the time it takes to execute
    halt_delay = 60 * 5
    halted = False
    halt_timer = Timer(halt_delay, halt, [env])
    halt_timer.start()
    return halt_timer


def get_input_dir(args):
    """Get the input directory"""
    if args.input is not None:
        input_dir = Path(args.input)
    if not input_dir.exists():
        print(f"Input directory does not exist: {input_dir}")
        exit()
    return input_dir


def get_output_dir(args):
    """Get the output directory"""
    if args.output is not None:
        output_dir = Path(args.output)
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    return output_dir


def get_split_file(args):
    """Get the train_test split file"""
    if args.split is not None:
        split_file = Path(args.split)
    if not split_file.exists():
        print(f"Split file does not exist: {split_file}")
        exit()
    return split_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default=RECONSTRUCTION_DATA_PATH,
                        help="File or folder containing the dataset [default: d7]")
    parser.add_argument("--split", type=str, default="train_test.json",
                        help="Train/test split file from which to select train sketches only [default: train_test.json]")
    parser.add_argument("--output", type=str, default=GENERATED_DATA_PATH,
                        help="Folder to save the output to [default: generated_design]")
    parser.add_argument("--machine_id", type=int, default=MACHINE_ID, help="Machine id used in file names [default: 2]")
    parser.add_argument("--host", type=str, default=HOST_NAME,
                        help="Host name to launch Fusion Gym on [default: 127.0.0.1]")
    parser.add_argument("--port", type=int, default=PORT_NUMBER, help="Port number to launch Fusion Gym on [default: 8080]")
    args = parser.parse_args()

    input_dir = get_input_dir(args)
    output_dir = get_output_dir(args)
    split_file = get_split_file(args)

    main(input_dir, output_dir, split_file, args.host, args.port, machine_id=args.machine_id)
