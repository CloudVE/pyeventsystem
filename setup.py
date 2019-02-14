import ast
import os
import re

import setuptools

# Cannot use "from pyeventware import get_version" because that would
# try to import the six package which may not be installed yet.
reg = re.compile(r"__version__\s*=\s*(.+)")
with open(os.path.join("pyeventware", "__init__.py")) as f:
    for line in f:
        m = reg.match(line)
        if m:
            version = ast.literal_eval(m.group(1))
            break

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyeventware",
    description="An event driven middleware library for Python",
    version=version,
    author="Galaxy and GVL projects",
    author_email="help@genome.edu.au",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cloudve/pyeventware",
    extras_require={
        'dev': ['tox', 'sphinx', 'flake8', 'flake8-import-order']
    },
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy"
    ],
)
