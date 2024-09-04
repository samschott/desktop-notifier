# -*- coding: utf-8 -*-
from __future__ import annotations

import ctypes
import logging
import platform
from typing import cast

from packaging.version import Version
from rubicon.objc import ObjCClass
from rubicon.objc.runtime import load_library

logger = logging.getLogger(__name__)
macos_version = Version(platform.mac_ver()[0])


__all__ = [
    "is_bundle",
    "is_signed_bundle",
    "macos_version",
]


sec = load_library("Security")
foundation = load_library("Foundation")

NSBundle = ObjCClass("NSBundle")

# Security/SecRequirement.h

kSecCSDefaultFlags = 0
kSecCSCheckAllArchitectures = 1 << 0
kSecCSDoNotValidateExecutable = 1 << 1
kSecCSDoNotValidateResources = 1 << 2
kSecCSCheckNestedCode = 1 << 3
kSecCSStrictValidate = 1 << 4


def is_bundle() -> bool:
    """
    Detect if we are in an app bundle

    :returns: Whether we are inside an app bundle.
    """
    return NSBundle.mainBundle.bundleIdentifier is not None


def is_signed_bundle() -> bool:
    """
    Detect if we are in a signed app bundle

    :returns: Whether we are inside a signed app bundle.
    """
    if not is_bundle():
        return False

    # Check for valid code signature on bundle.
    static_code = ctypes.c_void_p(0)
    err = sec.SecStaticCodeCreateWithPath(
        NSBundle.mainBundle.bundleURL, kSecCSDefaultFlags, ctypes.byref(static_code)
    )

    if err != 0:
        _codesigning_warning("SecStaticCodeCreateWithPath", err)
        return False

    signed_status = sec.SecStaticCodeCheckValidity(
        static_code,
        kSecCSCheckAllArchitectures | kSecCSCheckNestedCode | kSecCSStrictValidate,
        None,
    )

    signed_status = cast(int, signed_status)

    if signed_status == 0:
        return True
    else:
        _codesigning_warning("SecStaticCodeCheckValidity", signed_status)
        return False


def _codesigning_warning(call: str, os_status: int) -> None:
    """Log a warning about a failed code signing check."""
    logger.warning(
        "Cannot verify signature of bundle %s. %s call failed with OSStatus: %s",
        NSBundle.mainBundle.bundleIdentifier,
        call,
        os_status,
    )
