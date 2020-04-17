# text2png

This script takes lines of text in a file, and makes pictures of that text.

It does (almost) exactly what I want it to do, and is meant just for me.

If you find a use for it, feel free to credit me, though you have no obligation to do so.

## Installation

This uses [Python](https://python.org).

Confirm `python` and `pip` are installed:

```sh
python --version
python -m pip --version
```

Install [`pipenv`](https://github.com/pypa/pipenv):

```sh
python -m pip install --user -U pipenv
```

[Download](https://github.com/mawillcockson/text2png/archive/master.zip) this repository, or [install git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) and then [clone this repository](https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository).

The instructions for the latter option are platform specific, and the links contain information specific to macOS, Windows, and Linux. Android can use [Termux](https://termux.com/) to follow along with the Linux instructions.

Have `pipenv` install required packages:

```sh
pipenv install
```

Start a session with a `python` that has access to those packages:

```sh
pipenv shell --fancy
```

The above step is important, as running `pipenv run python` has caused some issues in the past, with files, upon being read, seeming to contain garbled data.

Show the help for this script:

```sh
python text2png.py -h
```

## Copyright

See [`LICENSE.txt`](./LICENSE.txt).
