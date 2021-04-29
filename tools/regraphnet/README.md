# Reconstruction Neural Network Agent
Message passing neural network to estimate next command probabilities for recovering a construction sequence from B-Rep input.

![Network Architecture](https://i.gyazo.com/2223b2f54754a0133cdea6c6da458c46.png)

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

## Setup
1. Install requirements:
    - `pytorch` tested with 1.7.0, gpu not required
    - `torch_geometric` tested with 1.6.1
    - `numpy` tested with 1.18.1
    - `scipy` tested with 1.4.1
2. Prepare data using [Regraph](../regraph) or [download the pre-processed data](https://fusion-360-gallery-dataset.s3-us-west-2.amazonaws.com/reconstruction/r1.0.0/regraph_05.zip) used for training in the paper.

## Training
Launch by running [`train.py`](./src/train.py) from the `src` directory run:
```
python train.py
```
This will launch training using the default dataset located in the `data` directory.

Inference using the trained model:
```
python inference.py
```

### Arguments
The full list of arguments is as follows:
- `--no-cuda`: Train on CPU [default: False]
- `--dataset`: Folder name of the supervised dataset created with [Regraph](../regraph)
- `--split` (optional): Train/test split file, as provided with the reconstruction dataset, to run only test files from the input folder
- `--no_gcn`: Use the MLP network instead of MPN [default: False]
- `--only_augment`: Train using only the augmented data [default: False]
- `exp_name`: Name of the experiment used for the checkpoint and log files.
- `epochs`, `lr`, `weight_decay`, `hidden`, `dropout`, `seed`: Specify training hyper-parameters.


## Results Log
Results are stored by default in the `log` directory as JSON files. Each JSON file contains a list of steps in the following structure:

```js
[
    {
        "train/test": 'Train',
        "epoch": 0,
        "loss": x,
        "start_acc": x%,
        "end_acc": x%,
        "operation_acc": x%,
        "overall_acc": x%
    },
    ...
]
```
- `train/test`: Data split for current log entry
- `epoch`, `loss`: Training epoch and loss
- `start_acc`, `end_acc`, `operation_acc`: Current accuracy logs for the three separate outputs
- `overall_acc`: Accuracy for three outputs all being correct
