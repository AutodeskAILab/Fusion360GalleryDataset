import json
import random
import argparse
from pathlib import Path
import matplotlib.pyplot as plt

from repl_env import ReplEnv
from agent_random import AgentRandom
from agent_supervised import AgentSupervised
from search_random import SearchRandom


parser = argparse.ArgumentParser()
parser.add_argument("--input", type=str, required=True, help="File or folder target smt files to reconstruct")
parser.add_argument("--split", type=str, help="Train/test split file from which to select test files to process")
parser.add_argument("--output", type=str, help="Folder to save the output logs to [default: log]")
parser.add_argument("--screenshot", dest="screenshot", default=False, action="store_true", help="Save screenshots during reconstruction [default: False]")
parser.add_argument("--agent", type=str, default="random", help="Agent to use [default: random]")
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
    if args.agent == "random":
        return SearchRandom(env, output_dir)


def get_agent(target_graph):
    """Get the agent based on user input"""
    if args.agent == "random":
        return AgentRandom(target_graph)
    elif args.agent == "supervised":
        return AgentSupervised(target_graph)


def main():
    files = get_files()
    output_dir = get_output_dir()

    # Random sample of a limited set for testing
    # files = random.sample(files, 5)

    # Setup the search and the environment that connects to FusionGym
    env = ReplEnv(host="127.0.0.1", port=8080)
    for file in files:
        print(f"Reconstructing {file.stem}")
        search = get_search(env, output_dir)
        target_graph = search.set_target(file)
        agent = get_agent(target_graph)
        best_score_over_time = search.search(agent, args.budget, screenshot=args.screenshot)
        print(f"> Result: {best_score_over_time[-1]:.3f} in {len(best_score_over_time)}/{args.budget} steps")


if __name__ == "__main__":
    main()
