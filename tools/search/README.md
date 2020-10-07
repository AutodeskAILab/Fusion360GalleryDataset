# Reconstruction with Neurally Guided Search
A framework for running neurally guided search to recover a construction sequence from B-Rep input. 

![Random Reconstruction](https://i.gyazo.com/702ad3f8f443c44be4ad85383f7fa719.gif)

## Publication
For further details on the method, please refer to [our paper](https://arxiv.org/abs/2010.02392).
```
@article{willis2020fusion,
    title={Fusion 360 Gallery: A Dataset and Environment for Programmatic CAD Reconstruction},
    author={Karl D. D. Willis and Yewen Pu and Jieliang Luo and Hang Chu and Tao Du and Joseph G. Lambourne and Armando Solar-Lezama and Wojciech Matusik},
    journal={arXiv preprint arXiv:2010.02392},
    year={2020}
}
```

## Training
We provide pretrained checkpoints, so training is not necessary to run search. For those interested in training the network please refer to the [`regraphnet`](../regraphnet) documentation.

## Setup
1. Fusion 360: Follow the [instructions here](../#install-fusion-360) to install Fusion 360.
2. Fusion 360 Gym: Follow the [instructions here](../fusion360gym#running) to install and run the Fusion 360 Gym, our add-in that runs inside of Fusion 360.
3. Install requirements: 
    - `pytorch` tested with 1.4.0, gpu not required
    - `numpy` tested with 1.18.1
    - `psutil` tested with 5.7.0
    - `requests` tested with 2.23.0


## Running
The code runs as a client that interacts with the Fusion 360 Gym, which must be running inside of Fusion 360 in the background.
1. Launch by running [`main.py`](main.py), for example from the `search` directory run:
```
python main.py --input ../testdata/Couch.smt
```
This will perform random search with the a random agent by default to reconstruct the Couch.smt geometry. You will see the design inside of Fusion 360 update as the agent attempts to reconstruct the original geometry. 

Specifying a type of agent and a search strategy is done as follows:
```
python main.py --input ../testdata/Couch.smt --agent mpn --search best
```

### Arguments
The full list of arguments is as follows:
- `--input`: File or folder of target .smt B-Rep files to reconstruct, if this is a folder all .smt files will be run
- `--split` (optional): Train/test split file, as provided with the reconstruction dataset, to run only test files from the input folder 
- `--output`(optional): Folder to save the output logs to [default: log]
- `--screenshot`(optional): Save screenshots during reconstruction [default: False]
- `--launch_gym` (optional): Launch the Fusion 360 Gym automatically, requires the gym to be set to 'run on startup' within Fusion 360. Enabling this will also handle automatic restarting of Fusion if it crashes [default: False]
- `--agent`(optional): Agent to use, can be rand, mpn, or mlp [default: rand]
- `--search`(optional): Search to use, can be rand, beam or best [default: rand]
- `--budget`(optional): The number of steps to search [default: 100]
- `--augment`: Use an agent trained on augmented data [default: False]


## Results Log
Results are stored by default in the `log` directory as JSON files. Each JSON file contains a list of steps in the following structure:

```js
[
    {
        "rollout_attempt": 5,
        "rollout_step": 0,
        "rollout_length": 7,
        "used_budget": 35,
        "budget": 100,
        "start_face": "7",
        "end_face": "4",
        "operation": "NewBodyFeatureOperation",
        "current_iou": null,
        "max_iou": 0.6121965660153939,
        "time": 1602089959.857739
    },
    ...
]
```
- `rollout_attempt`: The current rollout attempt number  (rand, beam search only)
- `rollout_step`: The current step in the current rollout attempt (rand, beam search only)
- `rollout_length`: The number of steps in a rollout attempt (rand, beam search only)
- `used_budget`: The number of the steps used in the budget so far
- `budget`: The total budget
- `start_face`: The id of the start face, used by the action (rand search only)
- `end_face`: The id of the end face, used by the action (rand search only)
- `operation`: The operation used by the action (rand search only)
- `prefix`: A list containing a sequence of actions with `start_face`, `end_face`, and `operation` (beam, best search only)
- `current_iou`: The IoU at this step, null if an invalid action was specified
- `max_iou`: The maximum IoU value seen so far
- `time`: The epoch unix time stamp


A log of the files that have been processed is stored at `log/search_results.json`. To rerun a given file, delete it from the list (or remove the file) or else it will be skipped during processing.


