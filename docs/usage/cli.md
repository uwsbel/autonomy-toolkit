# CLI Documentation

```{raw} html
---
---

<style>
	h4 {text-transform: lowercase;}
</style>
```

## `av`

```{autosimple} avtoolbox._av_base._init
```

```{argparse}
---
module: avtoolbox._av_base
func: _init
prog: av
nosubcommands:
nodescription:
---
```

## Sub-commands

Subcommands immediately succeed the `av` command. They implement additional logic. Having subcommands rather than arguments directly to `av` increases expandability as it will allow for additional features to be implemented without convoluting the help menu of the base `av` command.

### `dev`

```{autosimple} avtoolbox.dev._init
```

```{argparse}
---
module: avtoolbox._av_base
func: _init
prog: av
path: dev
nosubcommands:
nodescription:
---
```

#### `dev env`

```{autosimple} avtoolbox.dev._run_env
```

```{argparse}
---
module: avtoolbox._av_base
func: _init
prog: av
path: dev env 
nosubcommands:
nodescription:
---
```

### `db`

```{autosimple} avtoolbox.db._init
```

```{argparse}
---
module: avtoolbox._av_base
func: _init
prog: av
path: db
nosubcommands:
nodescription:
---
```

#### `db combine`

```{autosimple} avtoolbox.db._run_combine
```

```{argparse}
---
module: avtoolbox._av_base
func: _init
prog: av
path: db combine 
nosubcommands:
nodescription:
---
```

#### `db read`

```{autosimple} avtoolbox.db._run_read
```

```{argparse}
---
module: avtoolbox._av_base
func: _init
prog: av
path: db read 
nosubcommands:
nodescription:
---
```
