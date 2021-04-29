# Fusion 360 Gallery Dataset Tools
Here we provide various tools for working with the Fusion 360 Gallery Dataset, including the CAD reconstruction code used in [our paper](https://arxiv.org/abs/2010.02392). Several tools leverage the [Fusion 360 API](http://help.autodesk.com/view/fusion360/ENU/?guid=GUID-7B5A90C8-E94C-48DA-B16B-430729B734DC) to perform geometry operations and require Fusion 360 to be installed. 

## Getting Started
Below are some general instructions for getting started setup with Fusion 360. Please refer to the readme provided along with each tool for specific instructions.

### Install Fusion 360
The first step is to install Fusion 360 and setup up an account. As Fusion 360 stores data in the cloud, an account is required to login and use the application. Fusion 360 is available on Windows and Mac and is free for students and educators. [Follow these instructions](https://www.autodesk.com/products/fusion-360/students-teachers-educators) to create a free educational license.

### Running 
To run a script/add-in in Fusion 360:

1. Open Fusion 360
2. Go to Tools tab > Add-ins > Scripts and Add-ins
3. In the popup, select the Add-in panel, click the green '+' icon and select the appropriate directory in this repo
4. Click 'Run'

![Running Fusion 360 Scripts/Add-ins](https://help.autodesk.com/sfdcarticles/img/0EM3g0000004S86)


### Debugging
To debug any of tools that use Fusion 360 you need to install [Visual Studio Code](https://code.visualstudio.com/), a free open source editor. For a general overview of how to debug scripts in Fusion 360 from Visual Studio Code, check out [this post](https://modthemachine.typepad.com/my_weblog/2019/09/debug-fusion-360-add-ins.html) and refer to the readme provided along with each tool.


## Tools
- [`Fusion 360 Gym`](fusion360gym): A 'gym' environment for training ML models to design using Fusion 360. 
- [`Reconverter`](reconverter): Demonstrates how to batch convert the raw data structure provided with the reconstruction dataset into other representations using Fusion 360.
- [`Regraph`](regraph): Demonstrates how to create a B-Rep graph data structure from data provided with the reconstruction dataset using Fusion 360.
- [`RegraphNet`](regraphnet): A neural network for predicting CAD reconstruction actions. This network takes the output from [`Regraph`](regraph) and is the underlying network used with neurally guided search in [our paper](https://arxiv.org/abs/2010.02392).
- [`Search`](search): A framework for running neurally guided search to recover a construction sequence from B-Rep input. We use this code in [our paper](https://arxiv.org/abs/2010.02392).
- [`sketch2image`](sketch2image): Convert sketches provided in json format to images using matplotlib.

