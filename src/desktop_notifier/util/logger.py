# -*- coding: utf-8 -*-
"""
Centralizes logging for desktop-notifier. Configure your own logging with:

.. code-block:: python
    import logging
    from desktop_notifier.util.logger import Logger
    Logger.set_logger("my_logger")

Then:

.. code-block:: python
    from desktop_notifier.util.logger import Logger
    Logger.logger().info("This will be logged using the logger named 'my_logger'")
"""
import logging

from desktop_notifier.util.pkg_metadata_helper import __DESKTOP_NOTIFIER_PACKAGE_NAME__

DEFAULT_LOGGER = logging.getLogger(__DESKTOP_NOTIFIER_PACKAGE_NAME__)


class Logger:
    _logger: logging.Logger | None = None

    @classmethod
    def logger(cls) -> logging.Logger:
        """Returns the currently configured Logger instance."""
        return cls._logger or DEFAULT_LOGGER

    @classmethod
    def set_logger(cls, logger: logging.Logger | str) -> None:
        """Configure Logger instance to use in desktop-notifier logging."""
        if isinstance(logger, str):
            cls._logger = logging.getLogger(logger)
        else:
            cls._logger = logger
