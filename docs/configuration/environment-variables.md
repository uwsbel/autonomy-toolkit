# Environment Variables

Environment variables may be used by `docker compose` or `atk` to override existing functionality or to configure the service itself. The available environment variables are described here.

## `docker compose` Environment Variables

```{note}
See [the official documentation](https://docs.docker.com/compose/environment-variables/set-environment-variables/) for more detailed information.
```

Because `atk` is simply a wrapper of `docker compose`, all the traditional techniques to use environment variables in `docker compose` still works. It is recommended to put a `.env` file in the same directly as the `atk.yml` file as no additional configuration is needed to read the `.env` file automatically.

## `atk` Environment Variables

```{todo}
There are currently no supported environment variables for `atk` directly.
```
