# Reconstruction Sequence Search
Framework for running reconstruction of a design sequence with different search benchmarks.

## Running
Runs as a client that interacts with the Fusion 360 Gym.
1. Follow the [instructions here](../fusion360gym) to launch the Fusion 360 Gym.
2. Launch by running [`main.py`](main.py), for example from the `search` directory run:
```
python main.py --input ../testdata Couch.smt --screenshot
```

## Arguments
- `--input`: File or folder target smt files to reconstruct, if this is a folder all .smt files will be run
- `--split` (optional): Train/test split file to filer which test files to process from the input folder 
- `--output`(optional): Folder to save the output logs to [default: log]
- `--screenshot`(optional): Save screenshots during reconstruction [default: False]
- `--agent`(optional): Agent to use [default: random]
- `--search`(optional): Search to use [default: random]
- `--budget`(optional): The number of steps to search [default: 100]