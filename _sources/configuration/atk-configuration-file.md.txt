# ATK Configuration File

The ATK configuration file (`atk.yml`) is used to describe the project and provides configurability to the user when the `atk` command is invoked.

Essentially, the `atk.yml` is a 1:1 replacement for traditional container orchestration tools, such as [docker compose](https://docs.docker.com/compose/). There are some minor adjustments that improve modularity, which are described here.

```{note}
See [Environment Variables](environment-variables.md) for more information regarding environment variable substitution in the `atk.yml` file.
```

## Example File

```yaml
name: art
x-optionals:
  devices:
    devices:
      - '/dev/video0'
  gpus:
    runtime: nvidia
  x11:
    volumes:
      - '/tmp/.X11-unix:/tmp/.X11-unix'
    environment:
      DISPLAY: ${DISPLAY}
services:
  dev: &dev_service
    image: 'atk/${ATK_PROJECT}:dev'
    hostname: '${ATK_PROJECT}-dev'
    container_name: '${ATK_PROJECT}-dev'
    build: &dev_build
      context: './'
      network: 'host'
      dockerfile: './containers/dev/dev.dockerfile'
      args: &dev_build_args
        PROJECT: ${ATK_PROJECT}
        ROS_DISTRO: ${ROS_DISTRO}
    volumes:
      - './:/home/${ATK_CONTAINER_USERNAME}/${ATK_PROJECT}'
    environment:
      DISPLAY: vnc:0.0
    working_dir: '/home/${ATK_CONTAINER_USERNAME}/${ATK_PROJECT}/workspace'
    tty: true
  vnc:
    image: 'atk/${ATK_PROJECT}:vnc'
    hostname: '${ATK_PROJECT}-vnc'
    command: ''
    container_name: '${ATK_PROJECT}-vnc'
    entrypoint: ''
    build:
      context: './containers/vnc'
      dockerfile: './vnc.dockerfile'
      network: 'host'
      args:
        VNC_PASSWORD: '${ATK_PROJECT}'
        RUN_XTERM: 'yes'
        RUN_FLUXBOX: 'yes'
    environment:
      RUN_XTERM: no
      RUN_FLUXBOX: yes
    ports:
      - '8080:8080'
      - '5900:5900'
networks:
  default:
    name: '${ATK_PROJECT}'
```

The above example `atk.yml` file showcases many of the usages and features of the `atk.yml` specification.

## `atk.yml` Fields

The `atk.yml` file is populated with various fields at the root level of the yaml. All are prefixed with `x-`, as this is reserved in `docker compose` and will not throw an error when reading.

### `name`

This field specifies the name of the project. It is part of the `docker compse` specification. It is a highly recommended to be included as if not defined explicitly, container and network names are defined with arbitrary names.

### `x-optionals`

```{warning}
Note that [extensions](https://docs.docker.com/compose/compose-file/11-extension/) (the `docker compose` name in the specification for `x-<variable>`) are not carried over with the [`include`](https://docs.docker.com/compose/compose-file/14-include/) keyword.
```

This field is the primary advantage of using `autonomy-toolkit` over other container orchestrations. This field provides users the ability to, at runtime, specify custom configuration variables to be used that are not used by default.

Use cases here include activating hardware-specific flags for the container orchestration, build flag augmentation, optional container adjustments, etc.

```yaml
x-optionals:
  devices:
    devices:
      - '/dev/video0'
  gpus:
    runtime: nvidia
  x11:
    volumes:
      - '/tmp/.X11-unix:/tmp/.X11-unix'
    environment:
      DISPLAY: ${DISPLAY}
```

In the above example, these custom arguments can be specified as show below.

```bash
atk dev --up --attach --services dev --optionals gpus
```

Say for the above example that `gpus` is passed as an optional, the attributes immediately following the optional name (i.e. `gpus`) will be copied to that containers root configuration level.

A simplified `atk.yml` is showed below for description purposes:

```yaml
name: art
x-optionals:
  devices:
    devices:
      - '/dev/video0'
  gpus:
    runtime: nvidia
  x11:
    volumes:
      - '/tmp/.X11-unix:/tmp/.X11-unix'
    environment:
      DISPLAY: ${DISPLAY}
services:
  dev:
    image: 'atk/${ATK_PROJECT}:dev'
    hostname: '${ATK_PROJECT}-dev'
    container_name: '${ATK_PROJECT}-dev'
    build:
      context: './'
      network: 'host'
      dockerfile: './containers/dev/dev.dockerfile'
      args:
        PROJECT: ${ATK_PROJECT}
        ROS_DISTRO: ${ROS_DISTRO}
    volumes:
      - './:/home/${ATK_CONTAINER_USERNAME}/${ATK_PROJECT}'
    environment:
      DISPLAY: vnc:0.0
    working_dir: '/home/${ATK_CONTAINER_USERNAME}/${ATK_PROJECT}/workspace'
    tty: true
```

If then `atk dev --up --attach --services dev --optionals gpus x11` is used, the resulting configuration that's used by the selected container orchestration is as follows:

```yaml
x-optionals:
  devices:
    devices:
      - '/dev/video0'
  gpus:
    runtime: nvidia
  x11:
    volumes:
      - '/tmp/.X11-unix:/tmp/.X11-unix'
    environment:
      DISPLAY: ${DISPLAY}
services:
  dev:
    image: 'atk/${ATK_PROJECT}:dev'
    hostname: '${ATK_PROJECT}-dev'
    container_name: '${ATK_PROJECT}-dev'
    build:
      context: './'
      network: 'host'
      dockerfile: './containers/dev/dev.dockerfile'
      args:
        PROJECT: ${ATK_PROJECT}
        ROS_DISTRO: ${ROS_DISTRO}
    volumes:
      - './:/home/${ATK_CONTAINER_USERNAME}/${ATK_PROJECT}'
      - '/tmp/.X11-unix:/tmp/.X11-unix'
    runtime: nvidia
    environment:
      DISPLAY: vnc:0.0
    working_dir: '/home/${ATK_CONTAINER_USERNAME}/${ATK_PROJECT}/workspace'
    tty: true
```
