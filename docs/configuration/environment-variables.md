# Environment Variables

Environment variables may be used by `atk` to override existing functionality or to configure the service itself. The available environment variables are described here.

## `ATK_DEFAULT_CONTAINERS`

`$ATK_DEFAULT_CONTAINERS` is a comma separated list of container/service/instance names that overrides the `default_containers` field in the `atk.yml` file. When set, it's values will be used when `atk dev` is called without explicitly specifying the `services` to be used.

For example, `default_containers` may be set to `['dev', 'vnc']`. If `ATK_DEFAULT_CONTAINERS=nx` then `atk dev` evaluates to `atk dev --services nx`, not `atk dev --services dev vnc`.

## `ATK_DEFAULT_RUNTIME`

The `atk dev` command provides the option to utilize multiple container orchastration services. By default `docker` is used. At the time of writing, `singularity` is also implemented. To use singularity then, one can set `ATK_DEFAULT_RUNTIME=singularity`.
