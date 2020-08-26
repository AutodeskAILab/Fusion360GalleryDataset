import sys
import os
from pathlib import Path

from base_search import BaseSearch


class RandomSearch(BaseSearch):

    def __init__(self):
        BaseSearch.__init__(self)

    def run(self):
        pass


def main():
    search = RandomSearch()
    target_file = search.testdata_dir / "Couch.smt"
    search.setup(target_file)
    search.run()

if __name__ == "__main__":
    main()
