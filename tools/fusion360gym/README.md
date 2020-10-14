# Fusion 360 Gym
A 'gym' environment for training ML models locally to design using Fusion 360. Consists of a 'server' that runs inside of Fusion 360 and receives design commands from a 'client' running outside.

![Drawing a couch](https://i.gyazo.com/f667c274c2542ddd7ee5aef81af0614a.gif)

## Server
### Running
1. Open Fusion 360
2. Go to Tools tab > Add-ins > Scripts and Add-ins
3. In the popup, select the Add-in panel, click the green '+' icon and select the [`server`](server) directory in this repo
4. Click 'Run' to start the server

### Launching Multiple Servers
Multiple instances of the server can be launched and assigned a range of ports using [`launch.py`](server/launch.py). 
1. Complete steps 1-3 in **Running** section above. Then select 'Run on startup' and close Fusion.
2. From the command line:
    ```
    cd path/to/fusion360gym/server
    python launch.py --instances 2
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
For a simple example of how to interact with the server check out [client/client_example.py](client/client_example.py). You will need to have the `requests` and `psutil` modules installed via pip and the server up and running.
```
cd /path/to/Fusion360Server/client
python client_example.py
```
This script will output various files to the [data](data) directory and you will see the Fusion UI update as it processes requests.

### Interface
See [client/fusion360gym_client.py](client/fusion360gym_client.py) for the implementation of the calls below.

#### Response Format
All calls return a response object that can be accessed like so:

```python
# Create the client class to interact with the server
client = Fusion360GymClient(f"http://{HOST_NAME}:{PORT_NUMBER}")
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
Reconstruct entire designs or parts of them from the json files provided with the reconstruction subset.
- `reconstruct(file)`: Reconstruct a design from the provided json file
- `reconstruct_sketch(sketch_data, sketch_plane, scale, translate, rotate)`: Reconstruct a sketch from the provided sketch data
    - `sketch_data`: is the sketch entity data structure from the json data
    - `sketch_plane` (optional): sketch plane to create the sketch on. Can be either one of:
        - string value representing a construction plane: `XY`, `XZ`, or `YZ`
        - B-Rep planar face id
        - point3d on a planar face of a B-Rep
    - `scale` (optional): scale to apply to the sketch e.g. `{"x": 0.5, "y": 0.5, "z": 0.5}`
    - `translate` (optional): translation to apply to the sketch e.g. `{"x": 1, "y": 1, "z":0}`
    - `rotate` (optional): rotation to apply to the sketch in degrees e.g. `{"x": 0, "y": 0, "z": 90}`
- `reconstruct_profile(sketch_data, sketch_name, profile_id, scale, translate, rotate)`: Reconstruct a single profile from the provided sketch data
    - `sketch_data`: is the sketch entity data structure from the json data
    - `sketch_name`: is the name of the sketch to draw the curve in, typically returned from `add_sketch()`
    - `profile_id`: the uuid of the profile to be drawn
    - `scale` (optional): scale to apply to the sketch e.g. `{"x": 0.5, "y": 0.5, "z": 0.5}`
    - `translate` (optional): translation to apply to the sketch e.g. `{"x": 1, "y": 1, "z":0}`
    - `rotate` (optional): rotation to apply to the sketch in degrees e.g. `{"x": 0, "y": 0, "z": 90}`
- `reconstruct_curve(sketch_data, sketch_name, curve_id, scale, translate, rotate)`: Reconstruct a single curve from the provided sketch data
    - `sketch_data`: is the sketch entity data structure from the json data
    - `sketch_name`: is the name of the sketch to draw the curve in, typically returned from `add_sketch()`
    - `curve_id`: the uuid of the curve to be drawn
    - `scale` (optional): scale to apply to the sketch e.g. `{"x": 0.5, "y": 0.5, "z": 0.5}`
    - `translate` (optional): translation to apply to the sketch e.g. `{"x": 1, "y": 1, "z":0}`
    - `rotate` (optional): rotation to apply to the sketch in degrees e.g. `{"x": 0, "y": 0, "z": 90}`

#### Target Reconstruction
Set the target design to be used with reconstruction.
- `set_target(file)`: Set the target that we want to reconstruct with a .step or .smt file. This call will clear the current design. Returns `graph` as a face adjacency graph representing the B-Rep geometry/topology as described [here](../regraph) and a `bounding_box` of the target that can be used for normalization.
- `revert_to_target()`: Reverts to the target design, removing all reconstruction geometry. Returns the same data as `set_target(file)`.

#### Sketch Extrusion
Incrementally create designs by generating the underlying sketch primitives and extruding them. 
- `add_sketch(sketch_plane)`: Adds a sketch to the design.
    - `sketch_plane`: can be either one of:
        - string value representing a construction plane: `XY`, `XZ`, or `YZ`
        - B-Rep planar face id
        - point3d on a planar face of a B-Rep
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
    - `operation`: a string with the values defining the type of extrude: `JoinFeatureOperation`, `CutFeatureOperation`, `IntersectFeatureOperation`, or `NewBodyFeatureOperation`.
    - Returns BRep vertices of the resulting body, BRep face information

#### Face Extrusion
Use simplified face extrusion actions that reference a target design set with `set_target()`.
- `add_extrude_by_target_face(start_face, end_face, operation)`: Add an extrude between two faces of the target.
    - `start_face`: is the uuid of the start face in the target
    - `end_face`: is the uuid of the end face in the target
    - `operation`: a string with the values defining the type of extrude: `JoinFeatureOperation`, `CutFeatureOperation`, `IntersectFeatureOperation`, or `NewBodyFeatureOperation`.
    - Returns a face adjacency graph representing the B-Rep geometry/topology as described [here](../regraph), and an intersection over union value calculated between the target and the reconstruction.
- `add_extrudes_by_target_face(actions, revert)`: Executes multiple extrude operations, between two faces of the target, in sequence.
    - `actions`: A list of actions in the following format:
    ```json
    [
        {
            "start_face": "7f00f7de-ee2e-11ea-adc1-0242ac120002",
            "end_face": "89b53186-ee2e-11ea-adc1-0242ac120002",
            "operation": "NewBodyFeatureOperation"
        },
        {
            "start_face": "b4982e94-ee2e-11ea-adc1-0242ac120002",
            "end_face": "b98cebe2-ee2e-11ea-adc1-0242ac120002",
            "operation": "JoinFeatureOperation"
        }
    ]
    ```
    - `revert` (optional): Revert to the target design before executing the extrude actions.

#### Export
Export the existing design in a number of formats.
- `mesh(file)`: Retreive a mesh in .obj or .stl format and write it to the local file provided.
- `brep(file)`: Retreive a brep in .step, .smt, or .f3d format and write it to a local file provided.
- `sketches(dir, format)`: Retreive each sketch in a given format.
    - `dir`: the local directory where the output will be saved
    - `format`: a string with the values `.png` or `.dxf`
- `screenshot(file, width, height)`: Retreive a screenshot of the current design as a png image. 
    - `file`: The local file to save the png image to.
    - `width` (optional): The width of the image, default is 512.
    - `height` (optional): The height of the image, default is 512.
    - `fit_camera` (optional): Fit the camera to the geometry in the design, default is True.
- `graph(file, dir, format, sequence)`: Retreive a face adjacency graph for a B-Rep design, or construction sequence.
    - `file` (optional): the base json file name to be used for all graph files when `sequence` is `True`
    - `dir` (optional): the local directory where the output will be saved  when `sequence` is `True`
    - `format` (optional): a string with the values `PerFace` or `PerExtrude` see [here](../regraph) for a description of each format. Default is `PerFace`.
    - `sequence` (optional): a boolean indicating whether to generate graphs for each step in the construction sequence or just the current B-Rep design. Default is `False`.
    - `labels` (optional): a boolean indicating whether to include labels in the graph data returned, default is False.



#### Utility
Various utility calls to interact with Fusion 360.
- `clear()`: Clear (i.e. close) all open designs in Fusion
- `refresh()`: Refresh the active viewport
- `ping()`: Ping for debugging
- `detach()`: Detach the server from Fusion, taking it offline, allowing the Fusion UI to become responsive again 

## Test
See the [test directory](test/) for test coverage and additional usage examples.


