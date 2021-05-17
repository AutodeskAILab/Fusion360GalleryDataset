# Reconstruction Neural Network Agent
Message passing neural network to estimate next command probabilities for recovering a construction sequence from B-Rep input.

![Network Architecture](https://i.gyazo.com/7f30e61ce2ecc86d1016da0565badc68.png)

## Publication
For further details on the method, please refer to [our paper](https://arxiv.org/abs/2010.02392).
```
@article{willis2020fusion,
    title={Fusion 360 Gallery: A Dataset and Environment for Programmatic CAD Construction from Human Design Sequences},
    author={Karl D. D. Willis and Yewen Pu and Jieliang Luo and Hang Chu and Tao Du and Joseph G. Lambourne and Armando Solar-Lezama and Wojciech Matusik},
    journal={ACM Transactions on Graphics (TOG)},
    volume={40},
    number={4},
    year={2021},
    publisher={ACM New York, NY, USA}
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
We provide the pre-trained models used in the paper in the [ckpt directory](ckpt). To train a model run [`train.py`](./src/train.py) from the `src` directory as follows:
```
python train.py --dataset /path/to/regraph/data/ --split /path/to/train_test.json
```
This will launch training using the specified dataset and split file. The split file is the `train_test.json` file provided with the reconstruction dataset.

### Training Arguments
The full list of training arguments is as follows:
- `--no_cuda`: Train on CPU [default: `False`]
- `--dataset`: Folder name of the dataset created with [Regraph](../regraph)
- `--split`: Train/test split file, as provided with the reconstruction dataset
- `--mpn`: Message passing network to use, can be `gcn`, `mlp`, `gat`, or `gin` [default: `gcn`]
- `--augment`: Directory for augmentation data
- `--only_augment`: Train using only the augmented data [default: `False`]
- `--exp_name`: Name of the experiment used for the checkpoint and log files.
- `--epochs`, `lr`, `weight_decay`, `hidden`, `dropout`, `seed`: Specify training hyper-parameters.

### Training Results Log
Training results are stored by default in the `log` directory as JSON files. Each JSON file contains a list of steps in the following structure:

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



## Inference
We provide an [inference example](src/inference.py) that can be run as follows from the `src` directory:
```
python inference.py
```
This example loads the example sequence provided in the `data` directory and performs inference.

### Inference Arguments
The full list of inference arguments is as follows:
- `--no_cuda`: Train on CPU [default: `False`]
- `--dataset`: Folder name of the dataset created with [Regraph](../regraph) [default: `data`]
- `--mpn`: Message passing network to use, can be `gcn`, `mlp`, `gat`, or `gin` [default: `gcn`]
- `--augment`: Use the checkpoint trained with augmented data [default: `False`]
- `--only_augment`: Use the checkpoint trained on just the augmented data [default: `False`]
