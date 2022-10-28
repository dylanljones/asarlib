# Python ASAR

Python Electron Asar archive parser

See [electron/asar](https://github.com/electron/asar) for more information about the ASAR file format

## Installation

````commandline
pip install git+https://github.com/dylanljones/asarlib.git@VERSION
````


## Usage

So far only reading Asar archives is supported. An archive can be opened like
any other file in Python:
````python
from asarlib import AsarFile

asar = AsarFile("path/to/file.asar")
...
asar.close()
````

The file can also be opened using a context manager:
````python
with AsarFile("path/to/file.asar") as asar:
    ...
````



