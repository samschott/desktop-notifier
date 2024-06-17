
If you would like to contribute more than a simple bug fix, please open an issue first
to discuss potential changes before implementing them.

### Code

To start, install maestral with the `dev` extra to get all dependencies required for
development:

```shell
pip3 install 'desktop-notifier[dev]'
```

This will install packages to check and enforce the code style, use pre-commit hooks and
bump the current version.

Code is formatted with [black](https://github.com/psf/black).
Coding style is checked with [flake8](http://flake8.pycqa.org).
Type hints, [PEP484](https://www.python.org/dev/peps/pep-0484/), are checked with
[mypy](http://mypy-lang.org/).

### Tests

Tests are currently very limited because it is challenging to verify that a notification
was indeed displayed as intended. Instead, we focus on:

* Testing API contracts around showing and clearing notifications
* Smoke tests to ensure no exceptions or segfaults during usage on supported platforms
