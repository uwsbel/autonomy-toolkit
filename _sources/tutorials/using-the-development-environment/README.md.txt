# Using the ATK Development Environment

The ATK development environment has been created to expedite the process from algorithm implementation to testing in simulation to deploying the control stack on the Autonomy Research Testbed (ART) (or any other compatible platform). 

## Prerequisites

- You have installed `autonomy-toolkit` ([resources for that](https://projects.sbel.org/autonomy-toolkit/setup.html))
- You have cloned the [autonomy-research-testbed](https://github.com/uwsbel/autonomy-research-testbed) repository

This tutorial focuses on the Autonomy Research Testbed (ART) for description purposes. You will therefore need to have cloned the [autonomy-research-testbed](https://github.com/uwsbel/autonomy-research-testbed) repository. ATK is not specific to ART, this is simply used to help explain the API.

Furthermore, it is assumed `docker` is available and used.

## Setup

Beyond installing the packages outlined in [prerequisites](#prerequisites), there is not much setup that is necessary. The `autonomy-toolkit` package provides tools for easily spinning up containers and attaching to the development environment within Docker.

## Usage

To use the development environment, very convenient commands are provided through the `autonomy-toolkit` CLI. The documentation for the `dev` command can be found [here](http://projects.sbel.org/autonomy-toolkit/usage/cli.html#dev).

As described in the documentation, the `dev` command has five arguments: `build`, `up`, `down`, `attach`, and `run`. These may sound familiar if you've used `docker compose` before because the `dev` command essentially wraps `docker compose`. Everything that the `atk dev` command does, `docker compose` can also do; the `atk dev` cli command is simply made to expedite the process of entering a container and may also provide an easy mechanism to add additional functionality in the future.

```{note}
For any commands mentioned herein, it will be assumed they are run from within the `autonomy-research-testbed` repository.
```

### Entering the Development Environment

The first time you attempt to use the ART development environment, the docker image will need to be built (the `atk` package will do this for you). This may take upwards of 10 minutes, depending on the number of packages your control stack needs to install. After the initial build, you may never need to build the stack again (unless you need additional packages installed). To build the image the first time around, you can run the following command:

```bash
atk dev
```

This is equivalent to running the following:

```bash
atk dev --up --attach
```

And since the image has never been built, the `--up` argument will also build it. This is only the case if the image cannot be found, i.e. the first time you run `atk dev`.

If you make changes to the workspace and need additional packages to be installed into the container, you can run the same command with the build flag:

```bash
atk dev --build
```

```{note}
This is _not_ equivalient to `atk dev --up --attach --build`. `--up` and `--attach` are only added if no other arguments are provided
```

```{warning}
If the container is already running (i.e. `atk dev --up` has already been called), the new built image will not be loaded automatically. You need to tear down the container by running `atk dev --down` or `atk dev -d` and then spin up the container again with `atk dev --up`. This can be done with one command: `atk dev --down --up --build`.
```

After you run `atk dev`, you should see a shell prompt like the following:

```bash
$ atk dev
WARNING  | logger.set_verbosity :: Verbosity has been set to WARNING
art-dev:~/art/workspace$
```

For more information regarding the `atk` command, please see the [documentation page](https://projects.sbel.org/autonomy-toolkit/usage/cli.html#dev).

### Developing Inside the Container

Once inside the container, if you type `pwd`, you should see `/home/art/art/workspace`. This is a mapped volume from the host. ART's control stack is built on top of [ROS 2](https://docs.ros.org/en/galactic/index.html). The intracricies of ROS 2 and its usage is outside the scope of this tutorial. Please refer to their official documentation to learn more.

The important things to understand when it comes to the ROS 2 stack is that, by default, the `setup.bash` file in `~/art/workspace/install` will automatically be sourced by the shell profile script. If the workspace has not been built yet (i.e. `colcon build` has not been run), you will need to either source it yourself after the first build or exit and enter the container once more to rerun the shell profile script. Furthermore, for the most part, the `<depend>` flag in ROS 2 `package.xml` config files should be used to outline dependencies necessary to run the stack. This has already been done within the ART stack.

```{warning}
It is _imperative_ any changes to files are mode exclusively in `/home/art/art/`. This folder is a mapped Docker [volume](https://docs.docker.com/storage/volumes/) and is shared with the host. If a file is editted outside of this folder, the changes will not persist once the container is torn down.
```

#### Running a Simulation

```{note}
To run the Chrono simulation with synthetic sensor data, a NVIDIA GPU is required.
```

Another container provided by the ART platform is `chrono`. The `chrono` container has been developed to provide a independent and prebuilt interface to the Chrono simulator. ART has been developed to have a Chrono model and various scenarios/examples are provided as a means of testing the `chrono` container.

The ART stack also comes with a variety of launch packages/files, one of which is the `art_simulation.launch.py` file in the `art_simulation_launch` package. In this section, we'll spin up a Chrono simulatiion using the `chrono` container and then use `art_simulation.launch.py` to start up the control stack to control the simulated vehicle autonomously through a track of red and green cones. The interface between Chrono and ROS 2 has been implemented through the [chrono-ros-bridge](https://github.com/uwsbel/chrono-ros-bridge.git). This package is already provided in the ART workspace and the generated node is called upon in `art_simulation.launch.py`. 

You first need to start the simulation. The Chrono simulation will act as a TCP server, so the ART launch file will throw errors if the Chrono sim is not started first. To do this, run the following command in one terminal window:

```bash
atk dev --run --services chrono --custom-cli-args gpus --args python demo_ARCLAB_cone.py
```

The `--services chrono` tells atk to use the `chrono` container for the `--run` command. `--custom-cli-args gpus` is required for the `demo_ARCLAB_cone.py` script because it uses [Chrono::Sensor](https://api.projectchrono.org/group__sensor.html) which requires CUDA. Similar to the `dev` container with the `--up` flag, if the image for the `chrono` container is not already built, `--run` will build it.

Then, in another terminal window, enter the development environment and run the following command to spin up both the `chrono-ros-bridge` node and the autonomy stack:

```bash
$ atk dev --custom-cli-args gpus # NOTE: only use --custom-cli-args gpus if you have a nvidia gpu
WARNING  | logger.set_verbosity :: Verbosity has been set to WARNING
art-dev:~/art/workspace$ ros2 launch art_simulation_launch art_simulation.launch.py hostname:=art-chrono vis:=true
```

The `vis:=true` flag essentially tells the stack nodes to visualize some intermediate steps that are currently implemented. `rviz2` is a better option for visualization purposes, and is automatically installed in the container. `rviz` configurations will be shipped with the repository in the near future. In any case, you may utilize the `vnc` container to then see the display windows. Details on the `vnc` container can be found [here](#visualizing-gui-windows-with-vnc).

The `hostname:=art-chrono` tells the `chrono-ros-bridge` to connect to the server at the hostname `art-chrono`. If the `chrono` instance is being run on a separate computer or is not at the `art-chrono` hostname, you can pass _instead_ `ip:=<ip address>` where `<ip address>` is set to wherever the `chrono` server is actually running.

#### Running with a ROS 2 Bag

To facilitate the recording and replaying of data in a ROS 2 stack, bags can be created. The entrypoint `ros2 bag ...` allows users to easily record/replay topics. For information on this command, please visit the [official ros documentation](https://docs.ros.org/en/galactic/Tutorials/Ros2bag/Recording-And-Playing-Back-Data.html). Using a ros2 bag to test a control stack is a viable option and is helpful to understand if code is working as expected.

The `autonomy-research-testbed` is shipped with a ros2 bag for testing purposes. Multiple ROS 2 bag files were recorded using ART for testing purposes. To get this file, you'll need to download it from the Box folder. This can be done using the [`wget`](https://pypi.org/project/wget/) Python package and a custom entrypoint in `atk` called `db`. `db`, which stands for database, is an evolving tool and has not been fully implemented. Further documentation will be written in the near future.

You first need to pull the bag files. To do this, you may run the following command:

```bash
atk db pull --use-atk-config
```

Under the hood, this is also reading the `atk.yml` file to find the files that need to be pulled.

The folder will be located at `autonomy-research-testbed/demos/bags/ATK-<ID>/`. ROS 2 bags are contained in folders and the `ros2 bag` command will be used to replay the file. After the file is pulled, enter the development environment and start replaying the bag file. We'll have it loop so the stack can be visualized easier.

```bash
$ atk dev --custom-cli-args gpus # NOTE: only use --custom-cli-args gpus if you have a nvidia gpu
WARNING  | logger.set_verbosity :: Verbosity has been set to WARNING
art-dev:~/art/workspace$ ros2 bag play ../demos/bags/ATK-02-25-2022-03-19-00 -l # or ATK-02-25-2022-04-30-30
```

With the bag being played, open another terminal and start up the stack.

```bash
$ atk dev --custom-cli-args gpus # NOTE: only use --custom-cli-args gpus if you have a nvidia gpu
WARNING  | logger.set_verbosity :: Verbosity has been set to WARNING
art-dev:~/art/workspace$ ros2 launch art_launch art_stack.launch.py vis:=true
```

The `vis:=true` flag essentially tells the stack nodes to visualize some intermediate steps that are currently implemented. `rviz2` is a better option for visualization purposes, and is automatically installed in the container. `rviz` configurations will be shipped with the repository in the near future. In any case, you may utilize the `vnc` container to then see the display windows. Details on the `vnc` container can be found [here](#visualizing-gui-windows-with-vnc).

### Visualizing GUI Windows with VNC

Another container provided by `autonomy-toolkit` is `vnc`. It can be used to visualize GUI apps that otherwise would be difficult to do from within Docker. In theory, the `vnc` container supports either [NoVNC](https://novnc.com/info.html) or a traditional VNC viewer, such as from [RealVNC](https://www.realvnc.com/en/connect/download/viewer/). In this section, we'll focus on NoVNC since it doesn't require any additional packages to be installed on the host.

By default, when you run `atk dev`, both the `dev` and `vnc` containers will be spun up. If you'd like to either start the `vnc` container explicitly or ensure it is in fact running, you can run the following command:

```bash
atk dev --up --services vnc
```

You can then navigate to [localhost:8080](http://localhost:8080) to see the visualization windows. It should look something like the pictures below.

```{image} https://raw.githubusercontent.com/uwsbel/autonomy-toolkit/master/docs/tutorials/using-the-development-environment/images/sim-novnc-screenshot.png?raw
:width: 49%
```

```{image} https://raw.githubusercontent.com/uwsbel/autonomy-toolkit/master/docs/tutorials/using-the-development-environment/images/real-novnc-screenshot.png?raw
:width: 49%
```

```{note}
If a port conflict occurs ([as described later](#port-conflicts)), you will need to replace `8080` in [localhost:8080](http://localhost:8080) with whatever you remap the new port to.
```

## Possible Problems

This sections outlines some possible pitfuls or frequently run into errors.

### Port Conflicts

If a docker container attempts to map to a host port that is currently in use or otherwise unavailable, it will throw an error and exit. The `autonomy-toolkit` error for this looks similar to the following:

```bash
CRITICAL | dev._parse_ports :: Host port '<port>' is requested for the '<service>' service, but it is already in use.
```

In this instance, `<port>` is requested to be mapped to the host for the service `<service>`, but it can't happen because it's already in use. The solution here is to use the `--port-mappings` flag. See below for usage:

```bash
$ atk dev -s <service> --port-mappings <old-port1>:<new-port1> <old-port2>:<new-port2> --up
```

The syntax is as it appears above, where the `--port-mappings` argument takes any number of mappings such that it goes `<old host port>:<new host port>`.

Example:

```bash
$ atk dev -s <service> --port-mappings 8080:8081 5900:5901 --up
```


## Support

Contact the [Simulation Based Engineering Laboratory](mailto:negrut@wisc.edu) for any questions or concerns regarding the contents of this repository.

## See Also

Visit our website at [sbel.wisc.edu](https://sbel.wisc.edu)!
