# Accessing visualization through noVNC

This tutorial will use autonomy-toolkit (ATK) with the Autonomy Research Testbed (ART) to visualize the simulation using noVNC

## Prerequisites

- You have cloned the [autonomy-toolkit](https://github.com/uwsbel/autonomy-toolkit) repository
- You have installed Docker ([resource for that](https://docs.docker.com/get-docker/))
- You have installed docker compose v2 ([resource for that](https://docs.docker.com/compose/cli-command/))
- You have installed `autonomy-toolkit` ([resources for that](https://projects.sbel.org/autonomy-toolkit/setup.html))
- You have gone through the Using the ATK Developement Environment tutorial


## Background
`vnc` is the container used to visualize gui apps. We will use noVNC which is a browser based VNC client implemented using HTML5 Canvas and WebSockets. This container is used alog with `dev` and `chrono` containers to visualize the simulations.

## Setup

Beyond installing the packages outlined in [prerequisites](#prerequisites), there is not much setup that is necessary. The `autonomy-toolkit` package provides tools for easily spinning up containers and attaching to the development environment within Docker. Going through the Using the `atk` Developement Environment tutorial will provide some background knowledge to understand this tutorial.

### Entering the Development Environment
```{note}
For any commands mentioned herein, it will be assumed they are run from within the `atk` repository.
```

There are two different ART developement environments you will need to enter. This can be done by first opening two terminal windows.

#### Chrono Developement Window

In the first terminal window we will be running the chrono docker container. The build the container the first time around, you can run the following command:

```bash
atk dev -ua -s chrono --gpus
```

And since the image has never been built, the `--up` argument will also build it. This is only the case if the image cannot be found, i.e. the first time you run `atk dev -ua -s chrono --gpus`.

If you make changes to the workspace and need additional packages to be installed into the container, you can run the same command with the build flag:

```bash
atk dev --build -s chrono
```

Once inside ART chrono continer, go into the atk/sim directory and run:
```bash
python demo_ARCLAB_cone.py
```
This will start the simulation in the chrono container. Next, we need to setup the dev container

#### Dev Developement Window
In the second terminal window we will be running the dev docker container. The build the container the first time around, you can run the following command:

```bash
atk dev -ua -s dev --gpus
```

And since the image has never been built, the `--up` argument will also build it. This is only the case if the image cannot be found, i.e. the first time you run `atk dev -ua -s dev --gpus`.

If you make changes to the workspace and need additional packages to be installed into the container, you can run the same command with the build flag:

```bash
atk dev --build -s dev
```

Once inside ART dev continer, go into the art/workspace directory.

We will then need to run the following:
```bash
colcon build
```
Refer to [Colcon-Tutorial](https://docs.ros.org/en/foxy/Tutorials/Colcon-Tutorial.html) for information on `colcon`

Next run:
```bash
source instal/setup.bash
```

Refer to [Colcon-Tutorial](https://docs.ros.org/en/foxy/Tutorials/Colcon-Tutorial.html) for information on `colcon` and how `source` works

The container is now ready to run the simlution using one of the launch files. The launch files can be found in: `workspace/src/common/launch/art_simulation_launch/launch`

The command to run the launch files follows this format:
```bash
ros2 launch <package> <launch_file>
```
For example to launch the art simluation, you would run:
```bash
ros2 launch art_simulation_launch art_simulation.launch.py hostname:=art-chrono vis:=true
```

```{note}
The `vis` flag is used to tell some of the nodes to visulizes what they are trying to do for debugging purposes. vis is a ROS parameter.
```

```{note}
The `--gpus` argument sets the runtime correctly for the docker container
```


#### rviz
You may also use rviz for visualization and debugging purposes when testing changes. Once inside the rviz console the user can select what nodes they want to visualize. To open rviz run:
```bash
ros run rviz2 rviz2
```
For more information on rviz refer to [rviz-User-Guide](http://wiki.ros.org/rviz/UserGuide)

### Viewing the noVNC visualization of the simulation

Once the commands are run in both command windows, open `localhost:8080` in your browser to view the noVNC window that visualizes the simulation that is running.

## Support

Contact the [Simulation Based Engineering Laboratory](mailto:negrut@wisc.edu) for any questions or concerns regarding the contents of this repository.

## See Also

Visit our website at [sbel.wisc.edu](https://sbel.wisc.edu)!





<!-- --gpus set the runtime correctly for the docker container -- .atk.yml in atk -->