# This file is part of cachedjdk.
# Copyright 2022, Board of Regents of the University of Wisconsin System
# SPDX-License-Identifier: MIT

import cachedjdk
import re


def test_version():
    # cchedjdk uses SemVer major.minor.patch[-dev]; the possible '-dev' suffix
    # is translated to '.dev0' for PEP 440 format.

    parts = cachedjdk.__version__.split(".")
    assert len(parts) in (3, 4)

    n = r"(([1-9][0-9]*)|0)"
    assert re.fullmatch(n, "0")
    assert re.fullmatch(n, "1")
    assert re.fullmatch(n, "123")
    assert not re.fullmatch(n, "00")
    assert not re.fullmatch(n, "01")

    assert re.fullmatch(n, parts[0])
    assert re.fullmatch(n, parts[1])
    assert re.fullmatch(n, parts[2])
    if len(parts) == 4:
        assert parts[3] == "dev0"
