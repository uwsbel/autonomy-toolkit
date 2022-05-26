# Container Runtimes

ATK supports any container orchestration system; the `atk.yml` file follows Docker Compose standards, which is supported by [podman-compose](https://github.com/containers/podman-compose). Furthermore, some container orchestration projects (e.g. [singularity-compose](https://singularityhub.github.io/singularity-compose/#/) has some minor changes which requires adjustments to the `atk.yml` file to support it. A mechanism for adjusting the `atk.yml` file for specific orchestration types is supported through ATK (see the [ATK docs](https://projects.sbel.org/autonomy-toolkit/usage/api/autonomy_toolkit/containers/index.html) for examples). 

## Supported Runtimes

To change the orchestration backend that is used by ATK, you need to adjust the `ATK_CONTAINER_RUNTIME` environment variable. See [environment variable](./environment-variables.md) docs for more info.

### Docker Compose

[Docker Compose](https://docs.docker.com/compose/) is the industry standard when it comes to container orchestration systems. This is used by default.

### Singularity Compose

[Singularity Compose](https://singularityhub.github.io/singularity-compose/#/) is a tool in beta release that wraps [Singularity](https://sylabs.io/guides/3.5/user-guide/index.html). A singularity implementation is present in ATK because Docker has security issues that makes it not ideal for use on shared systems (see [here](https://logrhythm.com/blog/how-to-mitigate-docker-security-risk/) for more information). Singularity provides a feature that leverages `fakeroot` to let users build and attach to containers on systems where it's not typically possible to run container systems.

The system administrator for your shared computer may need to do the following to ensure singularity-compose works as expected:

- [Add fakeroot support](https://sylabs.io/guides/3.5/user-guide/cli/singularity_config_fakeroot.html)
- Add your user to the network config
	- This is only necessary if you don't want to be root in the container and you'd like to allow port mapping between the container and host. If you don't mind being root in the container, just use fakeroot.
	- i.e. `singularity global config --set "allow net users" <USER>`

## Configuration

There may be some configuration necessary to ensure different container systems function properly. Described here are a few mechanisms to support that.

### `ATK_CONTAINER_RUNTIME`

See [environment variable](./environment-variables.md) docs for more information on how to properly set the container runtime.

### `custom_cli_argments`

Different container orchestration systems (i.e. `docker compose` or `singularity-compose`) may have different configuration standards, so `custom_cli_argments` may need to be used in conjunction with different container systems.

By default, whatever is present in the service's `custom_cli_argments` field will be applied to the service configuration. 

For example, if the following configuration includes this:

```
project: test
default_containers:
	- dev
custom_cli_arguments:
  gpus:
    argparse:
      action: 'store_true'
    all:
      runtime: nvidia
services:
	dev:
		some_configuration_stuff: BLAH
```

And a user calls `atk dev --services dev --custom-cli-args gpus`, the resulting configuration will look like this:

```
project: test
default_containers:
	- dev
custom_cli_arguments:
  gpus:
    argparse:
      action: 'store_true'
    all:
      runtime: nvidia
services:
	dev:
		some_configuration_stuff: BLAH
		runtime: nvidia # NEW!!!
```

However, for singularity, the flag instead should be `nv: true`. To support this, an optional nested field can be used in each service's `custom_cli_arguments` configuration that matches the container runtime.

For instance, if we'd like to support both `nvidia: runtime` for Docker and `nv: true` for singularity, you can do the following:

```
project: test
default_containers:
	- dev
custom_cli_arguments:
  gpus:
    argparse:
      action: 'store_true'
    all:
			docker:
				runtime: nvidia
			singularity:
				nv: true
services:
	dev:
		some_configuration_stuff: BLAH
```

This will then check at runtime if `ATK_CONTAINER_RUNTIME` matches the first level under the service name (i.e. `all` in this case), and only use that config if found.
