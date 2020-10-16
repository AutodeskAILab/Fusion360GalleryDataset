# Fusion 360 Gym Tests
Tests use the [Python Unit testing framework](https://docs.python.org/3/library/unittest.html). 


## Visual Studio Code Setup
Tests can be setup and run from [Visual Studio Code](https://code.visualstudio.com/docs/python/testing) by adding the following to the `settings.json` folder at the root of the repo.

```json
{
    "python.testing.unittestArgs": [
        "-v",
        "-s",
        "./tools/fusion360gym/test",
        "-p",
        "test_*.py"
    ],
    "python.testing.pytestEnabled": false,
    "python.testing.nosetestsEnabled": false,
    "python.testing.unittestEnabled": true,
    "python.testing.autoTestDiscoverOnSaveEnabled": false
}
```


## Test Config File
To run all tests reqyures a `test_config.json` file, in the test directory, to store the path to the dataset, required by some tests. The contents of that file are as follows:

```json
{
    "dataset_dir": "/path/to/reconstruction/dataset"
}
```