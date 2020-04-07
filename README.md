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

Have `pipenv` install required packages:

```sh
pipenv install
```

Start a session with a `python` that has access to those packages:

```sh
pipenv shell --fancy
```

Show the help for this script:

```sh
python text2png.py -h
```

## Copyright

See [`LICENSE.txt`](./LICENSE.txt).
