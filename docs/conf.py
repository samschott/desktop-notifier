# -*- coding: utf-8 -*-

import os
import sys
import time

from desktop_notifier import (
    __DESKTOP_NOTIFIER_PACKAGE_NAME__,
    __version__
)

# -- Path setup ------------------------------------------------------------------------

sys.path.insert(0, os.path.abspath("../src"))

# -- Project information ---------------------------------------------------------------

author = "Sam Schott"
version = __version__
release = version
project = __DESKTOP_NOTIFIER_PACKAGE_NAME__
title = "Desktop-Notifier Documentation"
copyright = "{}, {}".format(time.localtime().tm_year, author)

# -- General configuration -------------------------------------------------------------

extensions = [
    "autoapi.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.intersphinx",
    "sphinx_mdinclude",
]
source_suffix = [".rst", ".md"]
master_doc = "index"
language = "en"

# -- Options for HTML output -----------------------------------------------------------

html_theme = "furo"

# -- Extension configuration -----------------------------------------------------------
autodoc_typehints = "description"

autoapi_dirs = ["../src/"]
autoapi_options = [
    "members",
    "show-inheritance",
    "show-module-summary",
    "inherited-members",
]
autoapi_member_order = "groupwise"

# sphinx.ext.todo
todo_include_todos = True

# sphinx.ext.intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
}
