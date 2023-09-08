"""A setuptools based setup module."""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "README.md").read_text(encoding="utf-8")


def parse_requirements():
    with open("requirements.txt") as f:
        required = f.read().splitlines()

    return required


def create_version():
    from setuptools_scm.version import get_local_dirty_tag

    def clean_scheme(version):
        return get_local_dirty_tag(version) if version.dirty else ""

    return {"local_scheme": clean_scheme}


setup(
    name="autonomy-toolkit",  # Required
    use_scm_version=create_version,
    description="Autonomy Toolkit",  # Optional
    long_description=long_description,  # Optional
    long_description_content_type="text/markdown",  # Optional (see note above)
    author="UW Simulation Based Engineering Lab",  # Optional
    license="BSD3",
    packages=find_packages(),  # Required
    include_package_data=True,
    python_requires=">=3.8.2, <4",
    install_requires=parse_requirements(),  # Optional
    url="https://projects.sbel.org/autonomy-toolkit",
    entry_points={  # Optional
        "console_scripts": [
            "atk=autonomy_toolkit._atk_base:_main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Software Development",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    project_urls={  # Optional
        "Homepage": "https://projects.sbel.org/autonomy-toolkit",
        "Bug Reports": "https://github.com/uwsbel/autonomy-toolkit/issues",
        "Source Code": "https://github.com/uwsbel/autonomy-toolkit/",
        "Our Lab!": "https://sbel.wisc.edu",
    },
)
