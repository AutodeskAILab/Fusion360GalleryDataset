from pathlib import Path
import matplotlib.pyplot as plt

from repl_env import ReplEnv
from random_agent import RandomAgent
from random_search import RandomSearch


def main():
    search_budget = 100

    # Setup the search and the environment that connects to FusionGym
    env = ReplEnv(host="127.0.0.1", port=8080)
    random_search = RandomSearch(env)

    # Setup with the target file we are trying to recreate
    current_dir = Path(__file__).resolve().parent
    testdata_dir = current_dir.parent / "testdata"
    target_file = testdata_dir / "Couch.smt"
    target_graph = random_search.set_target(target_file)

    random_agent = RandomAgent(target_graph)
    best_score_over_time = random_search.search(random_agent, search_budget, screenshot=True)


if __name__ == "__main__":
    main()
