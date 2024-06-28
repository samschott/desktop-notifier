# -*- coding: utf-8 -*-
"""
Helper methods for parsing data out of the pyproject.toml configuration in a
hopefully future-proof way.
"""
from email import parser, policy
from importlib.metadata import metadata

__DESKTOP_NOTIFIER_PACKAGE_NAME__ = "desktop-notifier"
__desktop_notifier_metadata = metadata(__DESKTOP_NOTIFIER_PACKAGE_NAME__)


def _get_project_url() -> str | None:
    """Parse project URLs from pyproject.toml package metadata."""
    project_urls = __desktop_notifier_metadata.get("Project-URL")

    # 'project_urls' should be a string that looks like this
    #    "Homepage, https://github.com/samschott/desktop-notifier"
    if isinstance(project_urls, str):
        return project_urls.split(",", maxsplit=1)[1].strip()
    else:
        print(f"WARNING: Could not parse project URL from {project_urls}")


# Using the approach in https://stackoverflow.com/questions/75801738/importlib-metadata-doesnt-appear-to-handle-the-authors-field-from-a-pyproject-t
def _get_primary_author_name() -> str:
    """Parse author name from pyproject.toml package metadata."""
    email_parser = parser.Parser(policy=policy.default)
    dummy_email_str = f"To: {__desktop_notifier_metadata.get('Author-email')}"
    dummy_email = email_parser.parsestr(dummy_email_str)

    try:
        return dummy_email["to"].addresses[0].display_name
    except IndexError:
        print(f"WARNING: Could not parse author name from {dummy_email_str}")
        return "Sam Schott"
