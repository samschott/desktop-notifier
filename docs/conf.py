# -*- coding: utf-8 -*-

import os
import sys
import time

# -- Path setup ------------------------------------------------------------------------

sys.path.insert(0, os.path.abspath("../src"))

# -- Project information ---------------------------------------------------------------

author = "Sam Schott"
version = "4.0.0"
release = version
project = "dekstop-notifier"
title = "Desktop-Notifier Documentation"
copyright = "{}, {}".format(time.localtime().tm_year, author)

# -- General configuration -------------------------------------------------------------

extensions = [
    "autoapi.extension",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx.ext.intersphinx",
    "sphinx_mdinclude",
]
source_suffix = [".rst", ".md"]
master_doc = "index"
language = "en"
# html4_writer = True

# -- Options for HTML output -----------------------------------------------------------

html_theme = "furo"

# -- Extension configuration -----------------------------------------------------------

# autoapi.extension
autoapi_type = "python"
autoapi_dirs = ["../src/desktop_notifier"]
autoapi_options = [
    "members",
    "show-inheritance",
    "show-module-summary",
    "undoc-members",
    "private-members",
]
autoapi_add_toctree_entry = False

# sphinx.ext.todo
todo_include_todos = True

# sphinx.ext.intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
}
