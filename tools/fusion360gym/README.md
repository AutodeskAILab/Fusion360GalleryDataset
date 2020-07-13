# Fusion 360 Gym
A 'gym' environment for training ML models to design using Fusion 360. Consists of a 'server' that runs inside of Fusion 360 and receives design commands from a 'client' running outside.

![Drawing a couch](https://i.gyazo.com/f667c274c2542ddd7ee5aef81af0614a.gif)

## Server
### Running
1. Open Fusion 360
2. Go to Tools tab > Add-ins > Scripts and Add-ins
3. In the popup, select the Add-in panel, click the green '+' icon and select the [`server`](server) directory in this repo
4. Click 'Run' to start the server
5. Optionally select 'Run on startup' if you want the server to start when Fusion does

### Launching Multiple Servers
Multiple instances of the server can be launched and assigned a range of ports using [`launch.py`](server/launch.py). 
1. Complete steps 1-5 in **Running** section above. Especially important is step 5, selecting 'Run on startup'.
2. From the command line:
    ```
    cd path/to/Fusion360Server/server
    python launch.py
    Launching Fusion 360 instance: 127.0.0.1:8080
    Launching Fusion 360 instance: 127.0.0.1:8081
    ```
3. This will launch 2 instances of Fusion 360 at the default endpoints: http://127.0.0.1:8080 and http://127.0.0.1:8081
4. Observe that several instances of Fusion 360 will launch and become unresponsive as the server is running in the UI thread
5. Verify that the servers are connected by running from the command line:
    ```
    python launch.py --ping
    Ping response from http://127.0.0.1:8080: 200
    Ping response from http://127.0.0.1:8081: 200
    ```
6. To detach the servers and make Fusion 360 responsive again:
    ```
    python launch.py --detach
    Detaching http://127.0.0.1:8080...
    Detaching http://127.0.0.1:8081...
    ```

#### Additional Arguments
The following additional arguments can be passed to [`launch.py`](server/launch.py):
- `--host`: Host name as an IP address [default: 127.0.0.1]
- `--start_port`: The starting port for the first Fusion 360 instance [default: 8080]
- `--instances`: The number of Fusion 360 instances to start [default: 2]

Launching multiple servers has been tested on both Windows and Mac. 


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
See [client/fusion_360_client.py](client/fusion_360_client.py) for the implementation of the calls below.

#### Response Format
All calls return a response object that can be accessed like so:

```python
# Create the client class to interact with the server
client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")
# Make a call to the server to clear the design
r = client.clear()
# Example of how we read the response data
response_data = r.json()
print(f"[{r.status_code}] Response: {response_data['message']}")
```
The following keys can be expected inside the `response_data` returned by calling `r.json()`:
- `status`: integer will be either `200` or `500`, see [here for more information](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status). This is a duplicate of the code in `r.status_code`.
- `message`: message with the server response. When the server failed this will contain the error and stack trace to debug.
- `data`: dict with data returned by the specific call.
Note that when returning binary data (e.g. mesh, brep) the above keys will not be present.


#### Reconstruction
- `reconstruct(file)`: Reconstruct a design from the provided json file
- `clear()`: Clear (i.e. close) all open designs in Fusion
#### Incremental Construction
- `add_sketch(sketch_plane)`: Adds a sketch to the design.
    - `sketch_plane`: can be either one of:
        - string value representing a construction plane: `XY`, `XZ`, or `YZ`
        - BRep planar face id
        - point3d on a planar face of a BRep
    - Returns the `sketch_name` and `sketch_id`.
- `add_point(sketch_name, p1, transform)`: Add a point to create a new sequential line in the given sketch
    - `sketch_name`: is the string name of the sketch returned by `add_sketch()`
    - `p1`: a point in sketch space 2D coords in a dict e.g. `{"x": 0, "y": 0}` or 3D coords if `transform="world"` is specified, indicating use of world coords
    - `transform` (optional): the transform for the sketch (necessary if you are replaying json data exported from Fusion) or a string `world` denoting use of world coordinates.
    - Returns the sketch `profiles` or an empty dict if there are no `profiles`. Note that profile uuid returned is only valid while the design does not change.
- `add_line(sketch_name, p1, p2, transform)`: Adds a line to the given sketch. 
    - `sketch_name`: is the string name of the sketch returned by `add_sketch()`
    - `p1` and `p2`: are sketch space 2D coords of the line in a dict e.g. `{"x": 0, "y": 0}` or 3D coords if `transform="world"` is specified, indicating use of world coords
    - `transform` (optional): the transform for the sketch (necessary if you are replaying json data exported from Fusion) or a string `world` denoting use of world coordinates.
    - Returns the sketch profiles or an empty dict if there are no profiles. Note that profile uuid returned is only valid while the design does not change.
- `close_profile(sketch_name)`: Close the current set of lines to create one or more profiles by joining the first point to the last point
    - `sketch_name`: is the string name of the sketch returned by `add_sketch()`
- `add_extrude(sketch_name, profile_id, distance, operation)`: Add an extrude to the design
    - `sketch_name`: is the string name of the sketch returned by `add_sketch()`
    - `profile_id`: is the uuid of the profile returned by `add_line()`
    - `distance`: is the extrude distance perpendicular to the profile plane
    - `operation`: a string with the values: `JoinFeatureOperation`, `CutFeatureOperation`, `IntersectFeatureOperation`, or `NewBodyFeatureOperation`.
    - Returns BRep vertices of the resulting body, BRep face information

#### Export
- `mesh(file)`: Retreive a mesh in .obj or .stl format and write it to the local file provided.
- `brep(file)`: Retreive a brep in .step or .smt format and write it to a local file provided.
- `sketches(dir, format)`: Retreive each sketch in a given format.
    - `dir`: the local directory where the output will be saved
    - `format`: a string with the values `.png` or `.dxf`

#### Utility
- `refresh()`: Refresh the active viewport
- `ping()`: Ping for debugging
- `detach()`: Detach the server from Fusion, taking it offline, allowing the Fusion UI to become responsive again 
- `commands(command_list, dir)`: Send a list of commands to run in sequence on the server. Currently the export and reconstruction commands are supported.
    - `command_list`: a list of commands in the following format:
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
    `dir`: is the (optional) local directory where files will be saved

## Test
See [test/test_fusion_360_server.py](test/test_fusion_360_server.py) for test coverage and additional usage examples.


