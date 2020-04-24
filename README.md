# Fusion360Server
A server running inside Fusion 360 as an add-in to communicate with the outside world.

## Server
### Running
1. Open Fusion 360
2. Go to Tools tab > Add-ins > Scripts and Add-ins
3. In the popup, select the Add-in panel, click the green '+' icon and select the [`server`](server) directory in this repo
4. Click 'Run' to start the server
5. Optionally select 'Run on startup' if you want the server to start when Fusion does
### Debugging
To run the server in debug mode you need to install [Visual Studio Code](https://code.visualstudio.com/). For a general overview of how to debug in Fusion 360 from Visual Studio Code, check out [this post](https://modthemachine.typepad.com/my_weblog/2019/09/debug-fusion-360-add-ins.html). Also note there is an [additional step](https://modthemachine.typepad.com/my_weblog/2019/10/problem-debugging-python-code.html) to make sure you are running the correct version of Python compatible with Fusion 360.

 
## Client
### Running
For a simple example of how to interact with the server check out [client/client_example.py](client/client_example.py). You will need to have the `requests` module installed via pip and the server up and running.
```
cd /path/to/Fusion360Server/client
python client_example.py
```
This script will output various files to the [data](data) directory and you will see the Fusion UI update as it processes requests.

### Interface
See [client/fusion_360_client.py](client/fusion_360_client.py) for the implementation of the following calls:
#### Reconstruction
- `reconstruct(file)`: Reconstruct a design from the provided json file
- `clear()`: Clear (i.e. close) all open designs in Fusion
#### Export
- `mesh(file)`: Retreive a mesh in .stl format and write it to a local file
- `brep(file)`: Retreive a brep in a format (step/smt) and write it to a local file
- `sketches(dir, format)`: Retreive each sketch in a given format (e.g. .png, .dxf) and save to a local directory
#### Utility
- `refresh()`: Refresh the active viewport
- `ping()`: Ping for debugging
- `detach()`: Detach the server from Fusion, taking it offline, allowing the Fusion UI to become responsive again 
- `commands(command_list, dir)`: Send a list of commands to run in sequence on the server and output files to `dir`. Commands for `command_list` are formatted as follows:
    ```
    [
        {
            "command": "reconstruct",
            "data": json_data
        },
        {
            "command": "sketches",
            "data": {
                "format": ".png"
            }
        },
        {
            "command": "mesh",
            "data": {
                "file": "test.stl"
            }
        },
        {
            "command": "clear"
        }
    ]
    ```

## Test
See [test/test_fusion_360_server.py](test/test_fusion_360_server.py) for test coverage and additional usage examples.


