# Setup

`autonomy-toolkit` has two interfaces: the command line interface (CLI) and through the Python API. Both are simply installed through `pip`.

Setup and installation information is provided in this guide.

## Prerequisites

Before you can install the `autonomy-toolkit` package, you will need to install a few other applications. Please see the linked installation instructions before continuing.

- Python >= 3.8.2: [Further details below](#python-environments)
- [Docker](https://docker.com): [Installation instructions](https://docs.docker.com/get-docker/) (additional [post installation instructions](https://docs.docker.com/engine/install/linux-postinstall/) for Linux users)
- [docker compose v2](https://docs.docker.com/compose/): [Installation instructions](https://docs.docker.com/compose/cli-command/)

```{note}
The docker compose version must be greater than 2.21.x. To check, run `docker compose version`.
```

Once the [prerequisites](#prerequisites) have been installed, you may proceed to installing the `autonomy-toolkit` package.

## Python Package

To install the `autonomy-toolkit` Python package, it is fairly simple.

### Python Environments

```{note}
This is merely a recommendation. Virtual and/or Conda environments simply isolate your Python versions and packages from other systems so that you can have different isolated environments on your system. If your main Python version is greater than 3.8.2 and you're not concerned about isolating your Python packages, ignore this section.
```

A common and _recommended_ way of maintaining Python versions, along with their packages, on your system is through [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html) or [Anaconda](https://anaconda.org). Virtual environments isolate your Python versions and packages from other environments. Imagine you are working on a project that requires Python2.7 and another that requires Python3.8. These versions are completely incompatible with one another, so their packages and code will be, too. The solution to this problem would be to create a Python2.7 virtual environment and a Python3.8 virtual environment. The primary difference between `venv` and Anaconda is that Anaconda is not restricted to only Python packages but allows you to install other packages that use other languages. For the `autonomy-toolkit` package, no such non-Python packages are used, so either can be used (though Anaconda is more common). Further, `venv` requires the Python version you intend to use to be installed on your system already, which Anaconda does not.

#### Create a Python Environment with `conda`

```{note}
You will need to install Anaconda for your system before creating the environment. To do that, please refer to their [official documentation](https://docs.anaconda.com/anaconda/install/index.html).
```

To create a `conda` environment, you can do something like the following:

```bash
$ conda create -n atk python=3.8.2
$ conda activate atk
```

#### Create a Python Environment with `venv`

```{warning}
You _must_ have Python >= 3.8.2 installed already for this to work. If you don't already have Python >= 3.8.2, you will need to create an environment via [conda](#create-a-python-environment-with-conda).
```

To create a Python virtual environment using `venv`, you can do something like the following:

```bash
$ python -m venv atk
```

You must then source the virtual environment. This depends on your system. See below for information on how to do that.

| Platform | Shell           | Command to activate virtual environment |
| -------- | --------------- | --------------------------------------- |
| POSIX    | bash/zsh        | `$ source <venv>/bin/activate`          |
|          | fish            | `$ source <venv>/bin/activate.fish`     |
|          | csh/tcsh        | `$ source <venv>/bin/activate.csh`      |
|          | PowerShell Core | `$ <venv>/bin/Activate.ps1`             |
| Windows  | cmd.exe         | `C:\> <venv>\Scripts\activate.bat`      |
|          | PowerShell      | `PS C:\> <venv>\Scripts\Activate.ps1`   |

You may also want to refer to the [`venv` documentation](https://docs.python.org/3/library/venv.html).

### Using `pip`

The `autonomy-toolkit` package is available on [PyPI](https://pypi.org/project/autonomy-toolkit). To install it, run the following command:

```bash
pip install autonomy-toolkit
```

### From Sources

Or, you can install the `autonomy-tookit` package from sources. To do that, clone the `autonomy-toolkit` repo locally:

```bash
git clone git@github.com:uwsbel/autonomy-toolkit.git
cd autonomy-toolkit
```

Then, use `setuptools` to install the `autonomy-toolkit` package:

```bash
pip install .
```

_**Note: If you're planning on developing the package, you may wish to install it as symlinks:**_

```bash
pip install -e .
```