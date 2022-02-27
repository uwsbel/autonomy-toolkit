# Autonomy Research Testbed

The [`autonomy-research-testbed`](https://github.com/uwsbel/autonomy-research-testbed) (ART) platform is purpose built to be an all-in-one test platform for autonomous algorithm development and simulation validation. Provided is documented hardware, a pre-made control stack, an optimized development-to-deployment workflow, and a database system to easily store and interact with ROS-based data files.

On this page, general background of the project is discussed and an overview of design decisions is provided. 

## Purpose

As mentioned before, the ART platform is an all-in-one test platform for autonomous vehicles. Providing this platform aims to leverage the high-fidelity simulation engine [Chrono](https://projectchrono.org) as the test method prior to deploying the code on the real car. Furthermore, the development workflow and data processing pipeline is meant to be generic and scalable to other hardware beyond the ART. Utilizing [ROS 2](https://docs.ros.org/en/galactic/index.html) for the control stack, the sensing support is built on packages from the ROS community and will continue to grow as ROS 2 is further adapted of the first iteration of ROS.

There are also many other existing platforms that provide similar functionality; [DonkeyCar](https://www.donkeycar.com/), [PARV](https://digital.wpi.edu/concern/student_works/st74ct36z?locale=en), [PiCar](https://www.instructables.com/PiCar-an-Autonomous-Car-Platform/), [AutoRally](https://autorally.github.io/), and [MIT RACECAR](https://mit-racecar.github.io/) to name a few. Unlike the aforementioned vehicle platforms, ART is built much larger from a [1:6th scale chassis from Redcat Racing](https://www.redcatracing.com/products/shredder?variant=31050562797658). This allows larger and more sensors to be added to the vehicle chassis. Modular 3D printed part files are provided that can be configured in multiple ways to mount sensor suites for different applications. Voltage rails are also provided to power sensors with varying power usage.

This simulation environment, built on top of Chrono, utilizes multiple modules to create a virtual world for autonomy development. The vehicle module, [Chrono::Vehicle](https://api.projectchrono.org/group__vehicle.html), implements high-fidelity vehicle models, for which a ART model is provided. The Chrono::Vehicle module also has advanced terrain models that can be used to represent hard, concret floors to Soil Contact Model (SCM) based deformable terrain; the latter useful for modeling off-road scenarios. Then [Chrono::Sensor](https://api.projectchrono.org/group__sensor.html) simulates sensors that can be used to replicate the data produced by the physical counterparts.

## Hardware

### Bill of Materials

| Component                 | Qty   | Unit Price | Link                                                                      |
| -----------               | ----- | -----     | ------                                                                    | 
| Shredder RC Car Base      | 1     | $399.99   | [https://tinyurl.com/4mnectre](https://tinyurl.com/4mnectre)              |
| inline fuse (optional)    | 1     | $9.99     | [https://tinyurl.com/dr5ycz9w](https://tinyurl.com/dr5ycz9w)                              |
| Power Wiring              | 1     | $11.99    | [https://tinyurl.com/5erssk6k](https://tinyurl.com/5erssk6k)                              |
| Chassis Wiring            | 1     | $15.99    | [https://tinyurl.com/2wwtfctpw](https://tinyurl.com/2wwtfctp)                              |
| Electronics battery (4S)  | 2     | $45.99    | [https://tinyurl.com/2cu64w2c](https://tinyurl.com/2cu64w2c)                              |
| Buck converter            | 1     | $16.89    | [https://tinyurl.com/2p87mkr3](https://tinyurl.com/2p87mkr3)                              |
| Power distribution blocks | 1     | $13.89    | [https://tinyurl.com/4fdv7emb](https://tinyurl.com/4fdv7emb)                              |
| T plugs                   | 1     | $8.98     | [https://tinyurl.com/396b3h54](https://tinyurl.com/396b3h54)                              |
| Wire shrink wrap          | 1     | $6.99     | [https://tinyurl.com/kfxnmb68](https://tinyurl.com/kfxnmb68)                              |
| Green SPST rocker switch  | 1     | $3.99     | [https://tinyurl.com/yfz2jzh6](https://tinyurl.com/yfz2jzh6)                              |
| Red SPST rocker switch    | 1     | $3.99     | [https://tinyurl.com/24c9rkhe](https://tinyurl.com/24c9rkhe)                              |
| Arduino Nano              | 1     | $19.99    | [https://tinyurl.com/4chrwfsy](https://tinyurl.com/4chrwfsy)                              |
| USB A to B cable (short)  | 1     | $5.89     | [https://tinyurl.com/ycks36zv](https://tinyurl.com/ycks36zv)                              |
| Blade connectors          | 1     | $9.95     | [https://tinyurl.com/4428ksbt](https://tinyurl.com/4428ksbt)                              |
| Tracking markers (optional)   | 1 | $56.00    | [https://tinyurl.com/3kchrv79](https://tinyurl.com/3kchrv79)                              |
| M4 x 12mm screw           | 12    | --        | --                              |
| M4 x 14mm screw           | 10    | --        | --                              |
| M4 x 20mm screw           | 1     | --        | --                              |
| M4 x 30mm screw           | 1     | --        | --                              |
| M4 nuts                   | 24    | --        | --                              |
| M3 x 6mm screw            | 4     | --        | --                              |
| M3 nuts                   | 4     | --        | --                              |
| M3 x 6mm spacer           | 4     | --        | --                              |
| Jetson Xavier NX Developer Kit (optional) | 1 | | |
| ELP USB Camera (optional) |       |           | [https://tinyurl.com/yck4cvyc](https://tinyurl.com/yck4cvyc)|
| VLP-16 Lidar (optional)   |       |           |                   |


### 3D Printed Mountings

#### Component Board
Designed the component board for reconfigurability for different electronic components.

<iframe src="https://uwmadison.app.box.com/embed/s/dphz9r2ofjb5yuf2jp8x45esp5qwga99?sortColumn=date&view=list" width="500" height="400" frameborder="0" allowfullscreen webkitallowfullscreen msallowfullscreen></iframe>

CAD file in STEP format [here](https://uwmadison.box.com/s/hel8mfam6ht7kngnl7753yuezija1zyu)

#### Supports
The supports are spaced to be mounted to the metal base plate of the car and have easy mounting to the board.

Rear support

<iframe src="https://uwmadison.app.box.com/embed/s/n4py1zb5ppavj1j5yerqaclwdypephhi?sortColumn=date&view=list" width="500" height="400" frameborder="0" allowfullscreen webkitallowfullscreen msallowfullscreen></iframe>

CAD file in STEP format [here](https://uwmadison.box.com/s/b9hxrck0ncn5mco3l15uiayv169c3zj6)

Middle support

CAD file in STEP format [here](https://uwmadison.box.com/s/5hj03zxceodsxcsgkzlyu64d07z2myyr)

Front support

CAD file in STEP format [here](https://uwmadison.box.com/s/jhgholq8yvcldbwbxmavu86xjmu8tios)


#### Bumper
The bumper has the option for multiple sensors. Three holes for potential front and side facing sensors.

<iframe src="https://uwmadison.app.box.com/embed/s/pvi6qq0chh5vq6shxqstrhunbonajgem?sortColumn=date&view=list" width="500" height="400" frameborder="0" allowfullscreen webkitallowfullscreen msallowfullscreen></iframe>


CAD file in STEP format  [here](https://uwmadison.box.com/s/e3dq6nslp7yc17sogk5kbllmkcijvp7n)

#### Lidar Mount
The Lidar was to be mounted above the other components so as to have an unobstructed view.

<iframe src="https://uwmadison.app.box.com/embed/s/a1dy7zv4allukmd70448c5ysa7yo0lfg?sortColumn=date&view=list" width="500" height="400" frameborder="0" allowfullscreen webkitallowfullscreen msallowfullscreen></iframe>

CAD file in STEP format  [here](https://uwmadison.box.com/s/rggqguu6zlnf4g1keemyyojtcw8uf9ws)

#### Camera Mounts
These mounts give the ability to change the angle of the cameras vertically and horizontally. The connection point is to a GoPro style connector mount.

<iframe src="https://uwmadison.app.box.com/embed/s/1he47ypzlscdje8cdqirjemwr5qt5pc4?sortColumn=date&view=list" width="500" height="400" frameborder="0" allowfullscreen webkitallowfullscreen msallowfullscreen></iframe>
<iframe src="https://uwmadison.app.box.com/embed/s/nshu4dgfmqex0q05c5mxyqcnw9e2w5h2?sortColumn=date&view=list" width="500" height="400" frameborder="0" allowfullscreen webkitallowfullscreen msallowfullscreen></iframe>

The CAD file for the camera mount can be found [here](https://uwmadison.box.com/s/u6sltxptlcu1y3t8186ccsfsgdck8757)

The frame to hold the camera itself can be found on Thingiverse [here](https://www.thingiverse.com/thing:4755911)


## Autonomy Stack

### Perception

A cone detection algorithm is included as the current perception method. The uses the front facing USB camera which is mounted to the vehicle's bumper. It uses a Faster-RCNN network implemented in PyTorch from [here](https://arxiv.org/abs/1506.01497) based on [this paper](https://arxiv.org/abs/1506.01497). The specific model is built on a [MobileNet](https://arxiv.org/abs/1905.02244) backbone to increase inference speed on the Jetson. The network was trained for 2 non-background classes (green and red cones) using a mix of simulated and real data.

From the 2D bounding boxes and a priori information of the cone height, the 3D cone location is estimated using the geometry of the camera and the mounting position and orientation of the camera on the vehicle. With additional sensors and additional algorithm implementation, the robustness of the 3D cone location estimation can be greatly improved. Below is an example of what is seen from the front facing camera overlaid with perceived object bounding boxes, confidence level, and estimated 3D location in the vehicle's local coordinate frame.

<iframe src="https://uwmadison.app.box.com/embed/s/cfjhohhzitx05g1eupdaeoc65vpqr0si?sortColumn=date&view=list" width="500" height="400" frameborder="0" allowfullscreen webkitallowfullscreen msallowfullscreen></iframe>


### Planning
The perceived 3D cone locations (green and red) are used to estimate a left and right boundary (red on right, green on left). The boundary is estimated using a spline of order 2 less than the number of cones to mitigate issues associate with cone location error. In addition, a phantom cone on left and right are used as a priori path info for the portion of the path that is not within the camera's field of view. When no cone of a color is visible or detected, another phantom cone is placed at the edge of the camera's field of view, representing the closest a cone could be and not be visible.

Once the left and right boundaries are estimated, a center position at distance L in front of the vehicle is found at the midpoint between the left and right paths. This point becomes the target point and is the output of the planning stage. The lookahead distance L can be configured to optimize the algorithm for the vehicle steering and perception abilities. The following shows a visualized example of the planning stage based on the perception example above.

<iframe src="https://uwmadison.app.box.com/embed/s/vzh4fpi0sxf20htz8xrflz7huqw98xxf?sortColumn=date&view=list" width="500" height="400" frameborder="0" allowfullscreen webkitallowfullscreen msallowfullscreen></iframe>


### Control
The control nodes takes the target position and calculates an error between the current heading of the vehicle, and the target position. It then uses a proportional gain to calculate the input steering and produces a vehicle input message with desired throttle [0,1], steering [-1,1], and braking [0,1].

