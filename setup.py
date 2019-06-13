#! /usr/bin/env python3


import os
from pathlib import Path

from setuptools import find_packages, setup


SKIP_REQUIREMENTS = ["#", "-e"]


def read(given_path):
    """Returns the striped content of a file."""
    given_path = Path(given_path)
    relative_path = Path(__file__).parent / given_path
    used_path = relative_path

    exists = lambda: os.path.isfile(used_path)
    if not exists():
        used_path = given_path
        if not exists:
            raise FileNotFoundError(
                f"could not find any of {relative_path} or {given_path}"
            )

    with open(used_path) as stream:
        return stream.read().strip()


def get_requirements(path="requirements.txt"):
    """Get default or custom requirements specified by `path`."""
    content = read(path)
    lines = []

    for line in content.splitlines():
        line = line.strip()
        if not line or any(map(line.startswith, SKIP_REQUIREMENTS)):
            continue
        if line.startswith("-r"):
            new_path = line[2:].strip()
            lines.extend(get_requirements(path=new_path))
            continue
        lines.append(line)

    return lines


setup(
    name="truestory",
    version="0.7.0",
    description="Be your own journalist.",
    long_description=read("README.md"),
    url="https://github.com/SavvyBit/TrueStory",
    license="MIT",
    author="SavvyBit",
    author_email="hello@truestory.one",
    packages=find_packages(exclude=["tests"]),
    scripts=["bin/truestory"],
    include_package_data=True,
    zip_safe=False,
    install_requires=get_requirements(),
    tests_require=get_requirements("requirements-test.txt"),
    test_suite="tests",
)
