# coding: utf-8
#
# This code is part of asarlib.
#
# Copyright (c) 2022, Dylan Jones

from .asarlib import AsarFile, AsarFileHeaderError

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.0.0"
