# CLI Documentation

```{raw} html
---
---

<style>
	h4 {text-transform: lowercase;}
</style>
```

## `atk`

```{autosimple} autonomy_toolkit._atk_base._init

```

```{argparse}
---
module: autonomy_toolkit._atk_base
func: _init
prog: atk
nosubcommands:
nodescription:
---
```

## Sub-commands

Subcommands immediately succeed the `atk` command. They implement additional logic. Having subcommands rather than arguments directly to `atk` increases expandability as it will allow for additional features to be implemented without convoluting the help menu of the base `atk` command.

### `dev`

```{autosimple} autonomy_toolkit.dev._init

```

```{argparse}
---
module: autonomy_toolkit._atk_base
func: _init
prog: atk
path: dev
nosubcommands:
nodescription:
---
```
