# Using the ROS bag for Testing 

The ROS bag has been made for testing the **Autonomy Stack** using the launch file `art_stack.launch.py` present in the `~/autonomy-research-testbed/workspace/src/common/launch/art_launch/launch` directory.

## Prerequisites 


- You have cloned the [autonomy-toolkit](https://github.com/uwsbel/autonomy-toolkit) repository
- You have installed Docker ([resource for that](https://docs.docker.com/get-docker/))
- You have installed docker compose v2 ([resource for that](https://docs.docker.com/compose/cli-command/))
- You have installed `autonomy-toolkit` ([resources for that](https://projects.sbel.org/autonomy-toolkit/setup.html))
- You have access to [MiniAV](https://uwmadison.app.box.com/folder/0)

## Background

A `bag` is a file format in ROS for storing message data. Within a `bag`, there are a few tools out of which we will be using the `ros2 bag`. `ros2 bag` is an unified console tool for recording, playback, and other operations. 
To know more about what a `bag` is, this is a [resource](http://wiki.ros.org/Bags).

## Setup

 After getting access to [MiniAV](https://uwmadison.app.box.com/folder/0), you can download the rosbag within the cloned repository(autonomy-research-testbed). Though the location where you download it shouldn't matter, it would be recommended to install it within the `~/autonomy-research-testbed/workspace/src/common/launch/art_launch` directory to keep the rosbag and the launch file you want to test within the same directory. 
 
 Apart from the above step, the [prerequisites](#prerequisites) listed above will be all that is necessary to run the `rosbag` along with a launch file for testing purposes. 

## Usage


To start testing the launch file using the `ros2 bag`, you will need to have two windows of a command line system opened. On one of them you will run the `ros2 bag` and on the other one you will run the launch file.

In both the windows, enter the MiniAV development environment using the following command:


```bash
atk dev
```

After entering the environment, navigate to the `art_launch` directory in one of the windows where you will be running your rosbag using the following command:

```bash
cd workspace/src/common/launch/art_launch/launch
```
After navigating to the `art_launch/launch` directory in one of the windows you chose above, run the following command to run the `ros2 bag`:

```bash
ros2 bag play rosbag2_2022_02_25-16_40_30_0.db3 
```
```{note}
The above command assumes you have your `ros2 bag` stored in `~/art/workspace/src/common/launch/art_launch/launch`.
You might have to cd into a different directory depending on where your `ros2 bag` is and then run the above command accordingly. 
</div></div>
```

In the second window, to launch the `autonomy stack`, run the following command:

```bash
ros2 launch art_launch art_stack.launch.py vis:=True
```
After running the above command, you have got the `autonomy stack` running. Navigate to your browser, and enter the  following address:

```bash
http://localhost:8080/
```
You can now visualize the `autonomy stack`!

Below is a representation of what your `autonomy stack` should look like -

![](https://raw.githubusercontent.com/uwsbel/autonomy-toolkit/master/docs/_static/rosbagVisual.png?)

## Support

Contact the [Simulation Based Engineering Laboratory](mailto:negrut@wisc.edu) for any questions or concerns regarding the contents of this repository.

## See Also

Visit our website at [sbel.wisc.edu](https://sbel.wisc.edu)!




