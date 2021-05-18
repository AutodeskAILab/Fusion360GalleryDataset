import json
import random
import argparse
import traceback
import copy
import time
from pathlib import Path
from threading import Timer
from requests.exceptions import ConnectionError

from repl_env import ReplEnv
from agent_random import AgentRandom
from agent_supervised import AgentSupervised
from search_random import SearchRandom
from search_beam import SearchBeam
from search_best import SearchBest


parser = argparse.ArgumentParser()
parser.add_argument("--input", type=str, required=True, help="File or folder target smt files to reconstruct")
parser.add_argument("--split", type=str, help="Train/test split file from which to select test files to process")
parser.add_argument("--output", type=str, help="Folder to save the output logs to [default: log]")
parser.add_argument("--screenshot", dest="screenshot", default=False, action="store_true", help="Save screenshots during reconstruction [default: False]")
parser.add_argument("--launch_gym", dest="launch_gym", default=False, action="store_true",
                    help="Launch the Fusion 360 Gym automatically, requires the gym to be set to run on startup [default: False]")
parser.add_argument("--agent", type=str, default="rand", choices=["rand", "gcn", "gat", "gin", "mlp"], help="Agent to use, can be rand, gcn, gat, gin, or mlp [default: rand]")
parser.add_argument("--search", type=str, default="rand", choices=["rand", "beam", "best"], help="Search to use, can be rand, beam or best [default: rand]")
parser.add_argument("--budget", type=int, default=100, help="The number of steps to search [default: 100]")
parser.add_argument("--synthetic_data", type=str, choices=["aug", "semisyn", "syn"], help="Type of synthetic data to use, can be aug, semisyn, or syn")
parser.add_argument("--debug", dest="debug", default=False, action="store_true", help="Debug mode [default: False]")
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
    if args.search == "rand":
        return SearchRandom(env, output_dir)
    elif args.search == "beam":
        return SearchBeam(env, output_dir)
    elif args.search == "best":
        return SearchBest(env, output_dir)


def get_agent():
    """Get the agent based on user input"""
    if args.agent == "rand":
        return AgentRandom()
    else:
        return AgentSupervised(agent=args.agent, syn_data=args.synthetic_data)


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


def add_result(results, file, result, output_dir):
    """Add a result to the list"""
    if file.stem not in results:
        results[file.stem] = result
        save_results(output_dir, results)

# Global variable to indicated if we have timed out
halted = False


def halt(env, file):
    """Halt search of the current file"""
    global halted
    print(f"Halting {file.name}")
    halted = True
    env.kill_gym()


def setup_timer(env, file):
    """Setup the timer to halt execution if needed"""
    global halted
    # We put a hard cap on the time it takes to execute
    halt_delay = 60 * 10
    halted = False
    halt_timer = Timer(halt_delay, halt, [env, file])
    halt_timer.start()
    return halt_timer


def main():
    global halted
    files = get_files()
    output_dir = get_output_dir()
    results = load_results(output_dir)

    # Setup the search and the environment that connects to FusionGym
    env = ReplEnv(host="127.0.0.1", port=8080, launch_gym=args.launch_gym)
    # Initialize these once and reuse them
    search = get_search(env, output_dir)
    if search is None:
        print("Error: Search is None!")
    agent = get_agent()
    if agent is None:
        print("Error: Agent is None!")

    files_to_process = copy.deepcopy(files)
    files_processed = 0
    crash_counts = {}
    while len(files_to_process) > 0:
        # Take the file at the end
        file = files_to_process.pop()
        halt_timer = setup_timer(env, file)

        result = {
            "status": "Success"
        }
        # If we already have processed this file, then skip it
        if not args.debug and file.stem in results:
            print(f"[{files_processed}/{len(files)}] Skipping {file.stem}")
            result["status"] = "Skip"
            files_processed += 1
        else:
            print("-------------------------")
            print(f"[{files_processed + 1}/{len(files)} files] Reconstructing {file.stem}")
            try:
                start_time = time.time()
                target_graph, bounding_box = search.set_target(file)
                agent.set_target(target_graph, bounding_box)
                best_score_over_time = search.search(agent, args.budget, screenshot=args.screenshot)
                time_taken = time.time() - start_time
                print(f"---> Score: {best_score_over_time[-1]:.3f} in {len(best_score_over_time)}/{args.budget} steps ({time_taken:.2f} sec)")
                files_processed += 1
            except ConnectionError as ex:
                # ConnectionError is thrown when the Fusion 360 Gym is down and we can't connect
                # If the timer has stopped, then we have killed Fusion
                # after a time out
                if halted:
                    print("ConnectionError timeout...")
                    # We want to log this file as not completing
                    result["status"] = "Timeout"
                    add_result(results, file, result, output_dir)
                    files_processed += 1
                else:
                    print("ConnectionError due to Fusion crash...")
                    # If the timer is still running Fusion has crashed
                    # and we want to rerun the file again
                    # Cancel the timer as we will restart and try again
                    halt_timer.cancel()
                    if not file.stem in crash_counts:
                        crash_counts[file.stem] = 1
                    else:
                        crash_counts[file.stem] += 1
                    print("Crash count:", crash_counts[file.stem])
                    # We only want to restart 3 times
                    if crash_counts[file.stem] < 3:
                        # Put the file back in the list to reprocess
                        # we don't log this as done
                        files_to_process.append(file)
                    else:
                        # Lets give up and move on
                        result["status"] = "Crash"
                        add_result(results, file, result, output_dir)
                        files_processed += 1

                # Then we relaunch the gym 
                env.launch_gym()
                # Continue to the next
                continue
            except Exception as ex:
                ex_arg = str(ex.args).split("\\n")[0]
                print(f"\tException! {type(ex).__name__}: {ex_arg}")
                result["status"] = "Fail"
                result["exception"] = type(ex).__name__
                result["exception_args"] = str(ex.args)
                result["trace"] = traceback.format_exc()
                files_processed += 1
        halt_timer.cancel()
        add_result(results, file, result, output_dir)

if __name__ == "__main__":
    main()
