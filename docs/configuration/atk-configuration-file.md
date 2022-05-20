# ATK Configuration File

The ATK configuration file (`atk.yml`) is used to describe the project and provides configurability to the user when the `atk` command is invoked.

Essentially, the `atk.yml` is a 1:1 replacement for traditional container orchestration tools, such as [docker compose](https://docs.docker.com/compose/). There are some minor adjustments that improve modularity, which are described here.

## Example File

```yaml
project: art
default_containers: 
  - dev
  - vnc
custom_cli_arguments:
  gpus:
    argparse:
      action: 'store_true'
    all:
      runtime: nvidia
  x11:
    argparse:
      action: 'store_true'
    dev:
      volumes:
        - "/tmp/.X11-unix:/tmp/.X11-unix"
      environment:
        DISPLAY: ${DISPLAY}
services:
  dev: &dev_service
    image: "atk/@{project}:dev"
    hostname: "@{project}-dev"
    container_name: "@{project}-dev"
    build: &dev_build
      context: "./"
      dockerfile: "./containers/dev/dev.dockerfile"
      network: "host"
      args: &dev_build_args
        PROJECT: "@{project}"
        USER_UID: "@{uid}"
        USER_GID: "@{gid}"
        APT_DEPENDENCIES: "bash zsh vim git python3-pip"
        PIP_REQUIREMENTS: "pandas matplotlib numpy>=1.19"
        USER_GROUPS: "dialout video"
    environment:
      DISPLAY: vnc:0.0
      NVIDIA_VISIBLE_DEVICES: "all"
      NVIDIA_DRIVER_CAPABILITIES: "all"
    volumes: 
     - "@{project_root}:/home/@{container_username}/@{project}"
    tty: true
    working_dir: "/home/@{container_username}/@{project}/workspace"
  nx:
    <<: *dev_service
    image: "atk/@{project}:nx"
    hostname: "@{project}-nx"
    container_name: "@{project}-nx"
    build:
      <<: *dev_build
      args:
        <<: *dev_build_args
        CONTAINERNAME: "nx"
  vnc:
    image: "atk/@{project}:vnc"
    hostname: "@{project}-vnc"
    container_name: "@{project}-vnc"
    build:
      context: "./containers/vnc"
      dockerfile: "./vnc.dockerfile"
      network: "host"
      args:
        VNC_PASSWORD: "@{project}"
        RUN_XTERM: "yes"
        RUN_FLUXBOX: "yes"
    environment:
      RUN_XTERM: no
      RUN_FLUXBOX: yes
    ports:
      - "8080:8080"
      - "5900:5900"
networks:
  default:
    name: "@{project}"
```

The above example `atk.yml` file showcases many of the usages and features of the `atk.yml` specification.

## `atk.yml` Fields

The `atk.yml` file is populated with various fields at the root level of the yaml.

```{note}
Some fields' values are accessible as variables elsewhere in the `atk.yml` file. See [here](./variable-replacement.md) for more info. The variable destination is also listed below for each field (if applicable).
```

### `project`

This field specifies the name of the project. It is a required field, and can be accessed via the `project` variable.

This field is typically used throughout the `atk.yml` file to aptly name variables other attributes.

### `default_containers`

This field specifies the default containers (see [containers](#containers)) that is used by the `atk dev` command. This field can be overridden by the `ATK_DEFAULT_CONTAINERS` environment variable (see [here](./environment-variables.md) for more info).

For the `atk dev` command, this applies as follows:

```python
atk dev --up --attach

# Provided the default_containers field is as written above
# Evaluates to...

atk dev --up --attach --services dev vnc
```

If `$ATK_DEFAULT_CONTAINERS` is set to something other than nothing, default_containers will be ignored and `$ATK_DEFAULT_CONTAINERS` is used.
```

```python
atk dev --up --attach

# Provided the ATK_DEFAULT_CONTAINERS=nx
# Evaluates to...

atk dev --up --attach --services nx     # Even though default_containers=['dev', 'vnc']
```

### `custom_cli_arguments`

This field is the primary advantage of using `autonomy-toolkit` over other container orchestrations. This field provides users the ability to, at runtime, specify custom configuration variables to be used that are not used by default. 

Use cases here include activating hardware-specific flags for the container orchestration, build flag augmentation, optional container adjustments, etc.

```yaml
custom_cli_arguments:
  gpus:
    argparse:
      action: 'store_true'
    all:
      runtime: nvidia
  x11:
    argparse:
      action: 'store_true'
    dev:
      volumes:
        - "/tmp/.X11-unix:/tmp/.X11-unix"
      environment:
        DISPLAY: ${DISPLAY}
```

In the above example, these custom arguments can be specified as show below.

```python
atk dev --up --attach --services dev --custom-cli-args gpus
```

This will then parse the flag using [`argparse`](https://docs.python.org/3/library/argparse.html) using the accompanied `argparse` field in the passed flag. If `'store_true'` is set as the action, the resulting configuration will simply be used. The second field immediately following the flag name (i.e. `gpus`) is the containers this flag applies to (i.e. `all` in the `gpus` example). This specifies which containers this flag will be activated for; for instance, since `all` is used for `gpus`, all containers will have this flag activate it's configuration; for the `x11` flag, only `dev` is specified, so only `dev` will have `x11`'s configuration activated for.

Say for the above example that `gpus` is passed as a custom arg, the attributes immediately following the container filter (i.e. `all` or `dev`) will be copied to that containers root configuration level.

A simplified `atk.yml` is showed below for description purposes:

```yaml
custom_cli_arguments:
  gpus:
    argparse:
      action: 'store_true'
    all:
      runtime: nvidia
  x11:
    argparse:
      action: 'store_true'
    dev:
      volumes:
        - "/tmp/.X11-unix:/tmp/.X11-unix"
services:
  dev:
    image: "atk/@{project}:dev"
    hostname: "@{project}-dev"
    container_name: "@{project}-dev"
    build:
      context: "./"
      dockerfile: "./containers/dev/dev.dockerfile"
      network: "host"
    environment:
      DISPLAY: ${DISPLAY}
    volumes: 
     - "@{project_root}:/home/@{container_username}/@{project}"
    tty: true
```

If then `atk dev --up --attach --services dev --custom-cli-args gpus x11` is used, the resulting configuration that's used by the selected container orchestration is as follows:

```yaml
custom_cli_arguments:
  gpus:
    argparse:
      action: 'store_true'
    all:
      runtime: nvidia
services:
  dev: &dev_service
    image: "atk/@{project}:dev"
    hostname: "@{project}-dev"
    container_name: "@{project}-dev"
    build:
      context: "./"
      dockerfile: "./containers/dev/dev.dockerfile"
      network: "host"
    environment:
      DISPLAY: ${DISPLAY}
    volumes: 
     - "@{project_root}:/home/@{container_username}/@{project}"
     - "/tmp/.X11-unix:/tmp/.X11-unix" # ======== NEW ========
    tty: true
    runtime: nvidia # ======== NEW ========
  nx:
    <<: *dev_service
    runtime: nvidia # ======== NEW ========
```

## `overwrite_lists`

If set to `true`, any list defined later that conflicts with custom cli arg, or any other merged entry, will be overwritten with the new list. The default behavior extends the existing list with the new entries.

## `user`

This is a nested field with multiple subfields which generate variable names.

Example:

```yaml
user:
  container_username: my_container_name
  host_username: my_host_name
  uid: 1000
  gid: 1000
```

### `user.container_username`

Evaluates to `username` which can be used throughout the `atk.yml` file. Typically used by `atk dev` when building a container to correctly specify the username for permission or naming reasons. By default, if not set explicitly, it will evaluate to whatever `project` is set to.

### `user.host_username`

Evaluates to `host_username`. The username of the host. If not directly set, will evaluate to the output of [`getpass.getuser()`](https://docs.python.org/3/library/getpass.html#getpass.getuser).

### `user.uid`

The Linux user ID. This can be used by the `atk dev` command for permission related reasons.

### `user.gid`

The Linux group ID. This can be used by the `atk dev` command for permission related reasons.

## `external`

The `external` field extends usability to allow the user to specify any configuration, even if it isn't applicable to container orchestration or `atk dev`. For instance, `atk db` may utilize the `external` field to specify files for download.
