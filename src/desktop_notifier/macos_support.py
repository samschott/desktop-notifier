# -*- coding: utf-8 -*-
import logging
import platform
import ctypes

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
    main_bundle = NSBundle.mainBundle
    logger.debug(f"main_bundle.bundleURL: {main_bundle.bundleURL}")
    return main_bundle.bundleIdentifier is not None


def is_signed_bundle() -> bool:
    """
    Detect if we are in a signed app bundle

    :returns: Whether we are inside a signed app bundle.
    """
    main_bundle = NSBundle.mainBundle

    if main_bundle.bundleIdentifier is None:
        _log_unsigned_warning("bundleIdentifier is None")
        return False

    # Check for valid code signature on bundle.
    static_code = ctypes.c_void_p(0)
    err = sec.SecStaticCodeCreateWithPath(
        main_bundle.bundleURL, kSecCSDefaultFlags, ctypes.byref(static_code)
    )

    if err != 0:
        _log_unsigned_warning(f"SecStaticCodeCreateWithPath() error: {err}")
        return False

    signed_status = sec.SecStaticCodeCheckValidity(
        static_code,
        kSecCSCheckAllArchitectures | kSecCSCheckNestedCode | kSecCSStrictValidate,
        None,
    )

    if cast(int, signed_status) == 0:
        return True
    else:
        _log_unsigned_warning(f"signed_status is {signed_status}")
        return False


def _log_unsigned_warning(msg: str) -> None:
    logger.warning(f"Unsigned bundle ({msg})")
