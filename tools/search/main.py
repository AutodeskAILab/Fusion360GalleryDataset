import json
import random
import argparse
import traceback
import copy
from pathlib import Path
from requests.exceptions import ConnectionError

from repl_env import ReplEnv
from agent_random import AgentRandom
from agent_supervised import AgentSupervised
from search_random import SearchRandom


parser = argparse.ArgumentParser()
parser.add_argument("--input", type=str, required=True, help="File or folder target smt files to reconstruct")
parser.add_argument("--split", type=str, help="Train/test split file from which to select test files to process")
parser.add_argument("--output", type=str, help="Folder to save the output logs to [default: log]")
parser.add_argument("--screenshot", dest="screenshot", default=False, action="store_true", help="Save screenshots during reconstruction [default: False]")
parser.add_argument("--launch_gym", dest="launch_gym", default=False, action="store_true",
                    help="Launch the Fusion 360 Gym automatically, requires the gym to be set to run on startup [default: False]")
parser.add_argument("--agent", type=str, default="random", help="Agent to use, can be random, supervised [default: random]")
parser.add_argument("--search", type=str, default="random", help="Search to use [default: random]")
parser.add_argument("--budget", type=int, default=100, help="The number of steps to search [default: 100]")
args = parser.parse_args()


def get_files():
    """Process the command line arguments"""
    input = Path(args.input)
    if not input.exists():
        print("Input file/folder does not exist")
        exit()
    test_files = None
    if args.split is not None:
        split_file = Path(args.split)
        if not split_file.exists():
            print("Split file does not exists")
        else:
            with open(split_file, encoding="utf8") as f:
                json_data = json.load(f)
                if "test" not in json_data:
                    print("Split file does not have a test set")
                else:
                    test_files = set()
                    for test_file in json_data["test"]:
                        test_files.add(f"{test_file}.smt")

    files = []
    if input.is_dir():
        smt_files = [f for f in input.glob("**/*.smt")]
        if len(smt_files) == 0:
            print("No .smt files found")
            exit()
        else:
            # We store an index with the file for debug output
            for smt_file in smt_files:
                if test_files is None:
                    # If we don't have a split
                    # use all files
                    files.append(smt_file)
                else:
                    # If we have a split
                    # use only the test files
                    if smt_file.name in test_files:
                        files.append(smt_file)
    else:
        files.append(input)
    return files


def get_output_dir():
    """Get the output directory to save the logs"""
    if args.output is not None:
        output_dir = Path(args.output)
    else:
        output_dir = Path(__file__).resolve().parent / "log"
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
    return output_dir


def get_search(env, output_dir):
    """Get the agent based on user input"""
    if args.search == "random":
        return SearchRandom(env, output_dir)


def get_agent(target_graph):
    """Get the agent based on user input"""
    if args.agent == "random":
        return AgentRandom(target_graph)
    elif args.agent == "supervised":
        return AgentSupervised(target_graph)


def load_results(output_dir):
    """Load the results file"""
    results_file = output_dir / "search_results.json"
    if results_file.exists():
        with open(results_file, encoding="utf8") as f:
            return json.load(f)
    else:
        return {}


def save_results(output_dir, results):
    """Save the results file"""
    results_file = output_dir / "search_results.json"
    with open(results_file, "w", encoding="utf8") as f:
        json.dump(results, f, indent=4)


def main():
    files = get_files()
    output_dir = get_output_dir()
    results = load_results(output_dir)

    # Random sample of a limited set for testing
    # files = random.sample(files, 10)

    # Setup the search and the environment that connects to FusionGym
    env = ReplEnv(host="127.0.0.1", port=8080, launch_gym=args.launch_gym)
    files_to_process = copy.deepcopy(files)
    files_processed = 0
    while len(files_to_process) > 0:
        # Take the file at the end
        file = files_to_process.pop()
        result = {
            "status": "Success"
        }
        # If we already have processed this file, then skip it
        if file.stem in results:
            print(f"[{files_processed}/{len(files)}] Skipping {file.stem}")
            result["status"] = "Skip"
            files_processed += 1
        else:
            print(f"[{files_processed}/{len(files)}] Reconstructing {file.stem}")
            try:
                search = get_search(env, output_dir)
                target_graph = search.set_target(file)
                agent = get_agent(target_graph)
                best_score_over_time = search.search(agent, args.budget, screenshot=args.screenshot)
                print(f"> Result: {best_score_over_time[-1]:.3f} in {len(best_score_over_time)}/{args.budget} steps")
                files_processed += 1
            except ConnectionError as ex:
                # This is thrown when the Fusion 360 Gym is down and we can't connect
                print("ConnectionError communicating with Fusion 360 Gym")
                # Put the file back in the list to reprocess
                files_to_process.append(file)
                env.launch_gym()
                # Continue to the next, which will be a repeat of the current
                continue
            except Exception as ex:
                ex_arg = str(ex.args).split("\\n")[0]
                print(f"\tException! {type(ex).__name__}: {ex_arg}")
                result["status"] = "Fail"
                result["exception"] = type(ex).__name__
                result["exception_args"] = str(ex.args)
                result["trace"] = traceback.format_exc()
                files_processed += 1
        if file.stem not in results:
            results[file.stem] = result
            save_results(output_dir, results)

if __name__ == "__main__":
    main()
