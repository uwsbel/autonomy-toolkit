# Writing an `.atk.yml` File

In order to use the ATK development environment, a configuration file must be present that describes the project and how to build the necessary images. This file must be named `.atk.yml` and should be located at the top of the repository. This tutorial outlines the optional/required arguments and flags for this file and how to write your own.

## Prerequisites

- You have installed `autonomy-toolkit` ([resources for that](https://projects.sbel.org/autonomy-toolkit/setup.html))

## Setup

Beyond installing the packages outlined in [prerequisites](#prerequisites), there is not much setup that is necessary. The `autonomy-toolkit` package provides tools for easily spinning up containers and attaching to the development environment within Docker.

We'll be using the Autonomy Research Testbed (ART) as an example for certain flags and argumentst. See [autonomy-research-testbed](https://github.com/uwsbel/autonomy-research-testbed) for that code. For information on the platform itself, see [this page](./../../autonomy-research-testbed.md).

## Background

The `.atk.yml` file, as described earlier, is used to configure the `autonomy-toolkit` tool and inform it of how to setup all of the images/containers. It is essentially equivalent to the `docker-compose.yml` file used by the Docker Compose tool with extra configurations specific to `autonomy-toolkit`. The extra configurations are present to aid in generalizing the tool and increasing it's efficacy at being used for autonomy research.

## The `.atk.yml` File

As an example, a simplified configuration file for the `autonomy-research-testbed` platform is shown below: 

```{literalinclude} ./autonomy-research-testbed.atk.yml
:language: yaml
:linenos:
```

### Custom Configuration Attributes

The `.atk.yml` file includes custom configuration attributes and the default docker-compose attributes. When constructing the final `docker-compose.yml` file that is used to create the container system, the custom attributes are combined with defaults and the docker-compose attributes to generate a final configuration.

The currently available custom configuration arguments are listed below:

| **Name** | **Variable Name** | **Type** | **Required?** | **Purpose** |
| --- | --- | --- | --- | --- |
| `project` | `project` | String | Yes | Used as the name of generated containers, images, volumes, etc. |
| `default_services` | `default_services` | List | No | Defines the default services that are assumed to be used when `atk dev` is invoked. Can be overwritten at runtime by passing `--services`. Defaults to `["dev"]`. |
| `overwrite_lists` | `overwrite_lists` | Bool | No | If set to `true`, any list defined later that conflicts with defaults provided through `atk` will be overwritten. The default behavior extends the defaults to include the custom elements. |
| `user` | N/A | Object | No | May be used to define the host/container username and the uid/gid for the user. If not defined, the values will be generated at runtime. |
| `user.container_username` | `username` | String | No | The username of the user created in the container. Defaults to `{project}`. |
| `user.host_username` | `host_username` | String | No | The username of the host. May be used as a filler in the `.atk.yml` file. Defaults to `getpass.getuser()` |
| `user.uid` | `uid` | int | No | The Linux user ID that the container user is set to. This mostly affects Linux users where permission issues are common with volumes. Defaults to `os.getuid()` on Unix systems and `1000` on Windows. |
| `user.gid` | `gid` | int | No | The Linux group ID that the container user is set to. This mostly affects Linux users where permission issues are common with volumes. Defaults to `os.getgid()` on Unix systems and `1000` on Windows. |
| `custom_cli_arguments` | N/A | Object | No | Defines custom command line arguments that are specific to each service. Should follow [argparse](https://docs.python.org/3/library/argparse.html) arguments. |

These are the **only** attributes used by `autonomy-toolkit`. After they are parsed, they are deleted and/or used to read custom command line arguments or evaluate variable replacement in the generated `docker-compose.yml` file.

#### Variable Replacement

[f-strings](https://realpython.com/python-f-strings/) are a very popular tool in Python to replace elements in a string with variables. This can be utilized in `autonomy-toolkit`. As seen in the table above, the name of the variable under the header **Variable Name** can be used anywhere in the `.atk.yml` file to replace it with the dynamic variable at runtime when configuring the `docker-compose.yml` file. Furthermore, in `custom_cli_arguments`, the destination attribute can also be used in an f-string.

Examples of this can be seen on lines 29 and 31 of the above code snippet.

### Docker Compose Attributes

The other attributes available to be used are defined by the Docker Compose specification. Information about it can be found in their [official documentation](https://docs.docker.com/compose/compose-file/compose-file-v3/).

As an example, to generate a custom image/container that is not `vnc` or `dev` (which are the default containers), you can do something like the following:

```yaml
services:
	...
  chrono:
    image: "atk/{project}:chrono"
    hostname: "{project}-chrono"
    container_name: "{project}-chrono"
    build:
      context: ./docker/chrono
      dockerfile: ./chrono.dockerfile
      network: "host"
      args:
        USERNAME: "{project}"
        APT_DEPENDENCIES: "libirrlicht-dev"
        CONDA_CHANNELS: "anaconda conda-forge"
        CONDA_DEPENDENCIES: "python=3.8.12 pip pychrono cudatoolkit anaconda-client conda-build"
        PIP_DEPENDENCIES: ""
    environment:
      NVIDIA_VISIBLE_DEVICES: "all"
      NVIDIA_DRIVER_CAPABILITIES: "all"
    ports:
      - "50000:50000"
    working_dir: "/home/{username}/{project}/sim"
    volumes: 
      - "{root}:/home/{username}/{project}"
    tty: true
```

As it can be seen in the snippet above, an image named `atk/{project}:chrono` (where `{project}` is replaced with the contents of the variable `project`) is created using the custom dockerfile located at `./docker/chrono/chrono.dockerfile`. This is exactly `docker-compose.yml` syntax, so please refer to their documentation if this doesn't make sense.
