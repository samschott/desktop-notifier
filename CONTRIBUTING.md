
If you would like to contribute more than a simple bug fix, please open an issue first
to discuss potential changes before implementing them.

### Code

To start, install maestral with the `dev` extra to get all dependencies required for
development:

```
pip3 install desktop-notifier[dev]
```

This will install packages to check and enforce the code style, use pre-commit hooks and
bump the current version.

Code is formatted with [black](https://github.com/psf/black).
Coding style is checked with [flake8](http://flake8.pycqa.org).
Type hints, [PEP484](https://www.python.org/dev/peps/pep-0484/), are checked with
[mypy](http://mypy-lang.org/).

You can check the format, coding style, and type hints at the same time by running the
provided pre-commit hook from the git directory:

```bash
pre-commit run -a
```

You can also install the provided pre-commit hook to run checks on every commit. This
will however significantly slow down commits. An introduction to pre-commit commit hooks
is given at [https://pre-commit.com](https://pre-commit.com).

### Tests

There are currently no tests. Contributions are very welcome!
