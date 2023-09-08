# Background

This page provides some helpful background about the Autonomy Toolkit.

## Design Considerations

The _most_ important component we considered when creating the development environment was whether the workflow was usable on multiple platforms/use cases, i.e. it would work as is on Windows, MacOS, Linux, and multi-user systems. This was a nonnegotiable because autonomy could be developed anywhere and wouldn't require any special hardware or "hacking" to work on a specific system (unless the autonomy system requires it, but we don't). Further, the development environment and deployment environment (the system that runs on the actual robot) must also be the same or similar in design. This means that any customization to the dependency lists or sensor configurations that was made locally would carry over to the actual vehicle.

Another important element we considered was using simulation to test the control stack. [Chrono](https://projectchrono.org) was the primary considered simulator (though nothing ties the toolkit directly to Chrono) and it needed to interface with the development _and_ deployment environment natively. The control stack itself should not be limiting hardware-wise (unless the implemented algorithms require a certain type of CPU, for example), but the Chrono simulations may require specific hardware, such as a NVIDIA GPU. Therefore, the solution must be able to communicate over the network considering everyone may not have access to a NVIDIA GPU on their computer, but a remote server/workstation may.

## Development Environment

To begin, Docker is a tool for virtualizing applications from a main operating system. What this means is that you can run full OS containers within a host OS. The primary purpose behind Docker, and similar tools, is to isolate development environments and to consistently deploy applications across computers. Docker is typically used on servers (think AWS or Azure) to isolate users and to deploy websites and web apps. Docker simply provides the ability to run these isolated containers, it is the users job to create the content that goes inside the containers. For more information on Docker, please see their [official website](https://www.docker.com/).

For robotics, containers can be a valuable tool for creating consistent development environments for users with different operating systems or different use cases. For example, a Docker container can be generated that has the entire simulation platform already installed; then, the user can simply run their simulation script in the container without the need to install any dependencies.

To help facilitate complicated scenarios, it is common practice to utilize multiple containers. Think, for instance, with multiple containers, you can have multiple independent systems that can be interchanged easily. Then, each isolated container communicates with the others in some capacity. This is what we will do here, where we have one container for the control stack, another for the simulation, and then other optional containers with other desired features: for example, `vnc` for visualizing gui apps.

The best way to learn the API and the design decisions is to go through a tutorial. Please refer to [this tutorial](tutorial/using-the-development-environment/using-the-development-environment.md).

<!-- There are two `services` (or containers) that will be created: `dev` and `vnc`. `dev` is the ROS 2 development environment we'll use to write the ROS 2 code. `vnc` is the container used to visualize gui apps. Various attributes are included in the `.yml` file, such as build context, ROS version types, and environment variables. As seen in the `volumes` section under the `dev` service, the entire development directory will be mounted inside the container. A [volume](https://docs.docker.com/storage/volumes/) is simply a folder that is shared between the host OS and the container. This means any and all code additions should be made _only_ inside of this folder; if you edit any files outside of `~/<project name>`, then the changes will not be saved when the container is exited. -->
