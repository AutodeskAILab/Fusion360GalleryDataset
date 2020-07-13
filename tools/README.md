# Fusion 360 Gallery Dataset Tools
Here we provide various tools for working with the Fusion 360 Gallery Dataset. 

## Getting Started
Below are some general instructions for getting started with using the dataset tools that leverage the [Fusion 360 API](http://help.autodesk.com/view/fusion360/ENU/?guid=GUID-7B5A90C8-E94C-48DA-B16B-430729B734DC) to perform geometry operations. Please refer to the readme provided along with each tool for specific instructions.

### Install Fusion 360
The first step is to install Fusion 360 and setup up an account. As Fusion 360 stores data in the cloud, an account is required to login and use the application. Fusion 360 is available on Windows and Mac and is free for students and educators. [Follow these instructions](https://www.autodesk.com/products/fusion-360/students-teachers-educators) to create a free educational license.

### Install Visual Studio Code
To debug any of these tools you need to install [Visual Studio Code](https://code.visualstudio.com/), a free open source editor. Please note that there is currently [an additional step](https://modthemachine.typepad.com/my_weblog/2019/10/problem-debugging-python-code.html) to make sure you are running the correct version of Python compatible with Fusion 360.

### Running 
For a general overview of how to run scripts in Fusion 360 from Visual Studio Code, check out [this post](https://modthemachine.typepad.com/my_weblog/2019/09/debug-fusion-360-add-ins.html) and refer to the readme provided along with each tool.


## Tools
- [`Fusion 360 Gym`](fusion360gym): A 'gym' environment for training ML models to design using Fusion 360. 
- [`Reconverter`](reconverter): Demonstrates how to batch convert the raw data structure provided with the Reconstruction Subset into other representations using Fusion 360.
- [`sketch2image`](sketch2image): Convert sketches provided in json format to images using matplotlib.


