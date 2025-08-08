# -*- coding: utf-8 -*-

import os
import sys
import time

# -- Path setup ------------------------------------------------------------------------

sys.path.insert(0, os.path.abspath("../src"))

# -- Project information ---------------------------------------------------------------

author = "Sam Schott"
version = "6.2.0.dev0"
release = version
project = "desktop-notifier"
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
]
autoapi_member_order = "bysource"

# sphinx.ext.todo
todo_include_todos = True

# sphinx.ext.intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
}
