# Variable Replacement

Another lack luster element of existing container orchestration softwares is that variables can't be utilized in other places throughout the file.

There currently exists two methods for using variables: `${}` (similar to bash variable replacement) and [YAML anchors](https://support.atlassian.com/bitbucket-cloud/docs/yaml-anchors/). However, these cannot be configured at runtime where they are defined in the configuration file itself at runtime, and used later. A use case here is that a `custom_cli_argument` is passed where it's value is to be used elsewhere in the configuration. Neither `${}` or YAML anchors can support this type of functionality.

## How to use it

Similar to _most_ container orchestration systems and bash, `${}` or simply `$` is prefixed to a variable name that is then evaluated at runtime to the variable value. To differentiate between these variables and `atk` variables, `@` is instead used.

For instance, the `project` variable is always populated by the `atk.yml` file (it is required), so if this variable would like to be used elsewhere, one can use `@{project}` anywhere in the `atk.yml` file and it will be availabled to `project`'s value prior to the orchestration program being called.
