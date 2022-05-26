# Configuration

The Autonomy Toolkit stores it's configuration file at `${REPO\_ROOT}/atk.yml` ([this can be overridden](https://projects.sbel.org/autonomy-toolkit/usage/cli.html#dev)), where `${REPO_ROOT}` is the root of whatever repository contains the desired working code (can simply be a directory, doesn't need to be a git repo).

Because there are multiple commands available in `atk`, with more to be added in the future, the `atk.yml` is made to be configurable for multiple applications.

## Table of Contents 

```{toctree}
:maxdepth: 1

atk-configuration-file.md
variable-replacement.md
environment-variables.md
container-runtimes.md

```
